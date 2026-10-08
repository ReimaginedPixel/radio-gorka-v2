import asyncio
import logging
import os
import re
import time
from collections import defaultdict
from contextlib import asynccontextmanager
from typing import Literal

import pymysql
from fastapi import FastAPI, HTTPException, Depends, Header, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from dotenv import load_dotenv

import auth
import db
import gorka
import store
import ytm

load_dotenv()
logger = logging.getLogger("radio_gorka")

PLAYLIST_ID = os.getenv("playlist_id", "PLJhSTAItRjxJl8f9mcHenCKVotPkSDFVB")
SITE_URL = os.getenv("site_url", "https://radiogorka.pl")
HISTORY_SYNC_INTERVAL_S = int(os.getenv("history_sync_interval", 60))

_allowed = os.getenv("allowed_origins", "")
ALLOWED_ORIGINS = [o.strip() for o in _allowed.split(",") if o.strip()] or [
    "http://localhost:5173",
]


@asynccontextmanager
async def lifespan(app):
    db.init_db()
    task = asyncio.create_task(_history_sync_loop())
    try:
        yield
    finally:
        task.cancel()


app = FastAPI(lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

VIDEO_ID_PATTERN = r"^[A-Za-z0-9_-]{5,32}$"
Status = Literal["pending", "approved", "played", "rejected"]


class LoginData(BaseModel):
    username: str
    password: str


class SuggestionIn(BaseModel):
    videoId: str = Field(pattern=VIDEO_ID_PATTERN)


class RejectIn(BaseModel):
    reason: str | None = Field(default=None, max_length=120)
    block: bool = False


class SettingsIn(BaseModel):
    requests_open: bool | None = None
    daily_goal: int | None = None
    max_per_day_anon: int | None = None
    max_per_day_account: int | None = None
    max_per_day_station: int | None = None
    max_duration_s: int | None = None
    replay_cooldown_days: int | None = None
    remove_when_played: bool | None = None
    auto_mark_played: bool | None = None


class BlockIn(BaseModel):
    kind: Literal["video", "artist"]
    value: str = Field(min_length=1, max_length=255)
    label: str | None = Field(default=None, max_length=255)


class StationIn(BaseModel):
    voter_token: str
    is_station: bool


class GorkaLoginIn(BaseModel):
    username: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=1, max_length=200)


# --- autoryzacja ---

def require_auth(authorization: str = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Brak tokenu autoryzacji")
    token = authorization.split(" ", 1)[1]
    user = auth.auth(token)
    if not user:
        raise HTTPException(status_code=401, detail="Klucz JWT niepoprawny")
    return user


def _voter_from_token(token):
    voter_id = auth.decode_voter_token(token) if token else None
    return store.get_voter(voter_id) if voter_id else None


def optional_voter(x_voter_token: str = Header(None)):
    voter = _voter_from_token(x_voter_token)
    return voter if voter and not voter["banned"] else None


def require_voter(x_voter_token: str = Header(None)):
    voter = _voter_from_token(x_voter_token)
    if not voter:
        raise HTTPException(status_code=401, detail="Brak sesji, odśwież stronę")
    if voter["banned"]:
        raise HTTPException(status_code=403, detail="Ta przeglądarka została zablokowana przez administratorów")
    return voter


# --- limity zapytań ---

_RATE_LIMIT = int(os.getenv("rate_limit", 30))
# Cała szkoła wychodzi zwykle z jednego IP, więc limit per IP jest dużo wyższy niż per przeglądarka.
_RATE_LIMIT_IP = int(os.getenv("rate_limit_ip", 300))
_RATE_WINDOW = 60
# Best-effort in-memory limiter; not shared across workers/restarts.
_rate_state = defaultdict(list)


def rate_limit(request: Request, bucket: str, voter=None, limit=None):
    if voter:
        key = f"voter:{voter['id']}"
        limit = limit or _RATE_LIMIT
    else:
        key = f"ip:{request.client.host if request.client else 'unknown'}"
        limit = limit or _RATE_LIMIT_IP
    now = time.time()
    hits = _rate_state[(bucket, key)]
    cutoff = now - _RATE_WINDOW
    while hits and hits[0] < cutoff:
        hits.pop(0)
    if len(hits) >= limit:
        raise HTTPException(status_code=429, detail="Zbyt wiele żądań, spróbuj ponownie później")
    hits.append(now)


# --- reguły propozycji ---

_ARTIST_SPLIT = re.compile(r"\s*(?:,|&|\bfeat\.?|\bft\.?)\s*", re.IGNORECASE)


def _artist_blocked(artist, blocked):
    if not artist or not blocked:
        return False
    names = {part.strip().lower() for part in _ARTIST_SPLIT.split(artist) if part.strip()}
    return bool(names & blocked) or artist.strip().lower() in blocked


def _describe(state, artist, duration, settings, blocked_artists):
    """Co uczeń może zrobić z danym utworem w wynikach wyszukiwania."""
    if state["blocked"] or _artist_blocked(artist, blocked_artists):
        return {"state": "blocked"}
    if state["open"]:
        o = state["open"]
        return {
            "state": "queued",
            "suggestion_id": o["id"],
            "status": o["status"],
            "votes": o["votes"],
            "voted_by_me": o["voted_by_me"],
        }
    if state["played_recently"]:
        return {"state": "played_recently"}
    if state["rejected_recently"]:
        return {"state": "rejected_recently"}
    if duration and duration > settings["max_duration_s"]:
        return {"state": "too_long"}
    return {"state": "new"}


def _daily_limit(voter, settings):
    if voter["is_station"]:
        return settings["max_per_day_station"]
    if voter["gorka_id"]:
        return settings["max_per_day_account"]
    return settings["max_per_day_anon"]


def _public(suggestion, voter):
    suggestion = dict(suggestion)
    suggestion["mine"] = suggestion.pop("submitted_by") == voter["id"]
    return suggestion


def _vote_on(suggestion_id, voter):
    if not store.add_vote(suggestion_id, voter["id"]):
        raise HTTPException(status_code=404, detail="Tej propozycji nie ma już w kolejce")
    return {"action": "voted", "suggestion": _public(store.get_suggestion(suggestion_id, voter["id"]), voter)}


def _fetch_song(video_id):
    try:
        song = ytm.client().get_song(video_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Nieprawidłowe ID utworu")
    details = (song or {}).get("videoDetails")
    if not details:
        raise HTTPException(status_code=404, detail="Nie znaleziono piosenki o podanym ID")
    artist = details.get("author")
    if artist and artist.endswith(" - Topic"):
        artist = artist[: -len(" - Topic")]
    try:
        duration = int(details.get("lengthSeconds"))
    except (TypeError, ValueError):
        duration = None
    return details.get("title") or video_id, artist, duration


def _try_remove_from_playlist(video_id):
    try:
        ytm.remove_from_playlist(PLAYLIST_ID, video_id)
        return True
    except Exception:
        logger.exception("Nie udało się usunąć %s z playlisty", video_id)
        return False


# --- uczniowie ---

@app.post("/api/session")
def create_session(request: Request):
    rate_limit(request, "session", limit=int(os.getenv("session_rate_limit", 120)))
    voter_id = store.create_voter()
    return {"token": auth.create_voter_token(voter_id)}


@app.get("/api/me")
def me(voter=Depends(require_voter)):
    settings = store.get_settings()
    limit = _daily_limit(voter, settings)
    used = store.count_submitted_today(voter["id"])
    return {
        "account": {"name": voter["display_name"]} if voter["gorka_id"] else None,
        "is_station": voter["is_station"],
        "gorka_enabled": gorka.enabled(),
        "requests_open": settings["requests_open"],
        "daily_limit": limit,
        "remaining_today": max(0, limit - used),
        "suggestions": store.list_mine(voter["id"]),
    }


@app.get("/api/search")
def search(query: str, request: Request, voter=Depends(optional_voter)):
    rate_limit(request, "search", voter)
    query = query.strip()
    if not query:
        return {"results": []}
    if len(query) > 200:
        raise HTTPException(status_code=400, detail="Za długie zapytanie")
    try:
        search_results = ytm.client().search(query)
    except Exception:
        raise HTTPException(status_code=502, detail="Błąd wyszukiwania w YouTube Music")

    results, seen = [], set()
    for r in search_results:
        video_id = r.get("videoId")
        if not video_id or video_id in seen:
            continue
        seen.add(video_id)
        results.append({
            "videoId": video_id,
            "title": r.get("title") or r.get("artist"),
            "artist": r["artists"][0]["name"] if r.get("artists") else None,
            "duration_seconds": r.get("duration_seconds"),
        })

    settings = store.get_settings()
    states = store.video_states(
        [r["videoId"] for r in results], voter["id"] if voter else None, settings["replay_cooldown_days"]
    )
    blocked = store.blocked_artists()
    for r in results:
        r.update(_describe(states[r["videoId"]], r["artist"], r["duration_seconds"], settings, blocked))
    return {"results": results}


@app.post("/api/suggestions")
def suggest(data: SuggestionIn, request: Request, voter=Depends(require_voter)):
    rate_limit(request, "suggest", voter)
    settings = store.get_settings()
    if not settings["requests_open"]:
        raise HTTPException(status_code=403, detail="Propozycje są teraz zamknięte")

    video_id = data.videoId
    state = store.video_states([video_id], voter["id"], settings["replay_cooldown_days"])[video_id]
    if state["blocked"]:
        raise HTTPException(status_code=403, detail="Ten utwór jest zablokowany przez administratorów")
    if state["open"]:
        return _vote_on(state["open"]["id"], voter)
    if state["played_recently"]:
        raise HTTPException(
            status_code=409,
            detail=f"Ten utwór był grany w ciągu ostatnich {settings['replay_cooldown_days']} dni",
        )
    if state["rejected_recently"]:
        raise HTTPException(status_code=409, detail="Ten utwór został niedawno odrzucony")

    limit = _daily_limit(voter, settings)
    if store.count_submitted_today(voter["id"]) >= limit:
        raise HTTPException(
            status_code=429,
            detail=f"Wykorzystano dzienny limit propozycji ({limit}). Nadal możesz głosować na kolejkę.",
        )

    title, artist, duration = _fetch_song(video_id)
    if duration and duration > settings["max_duration_s"]:
        raise HTTPException(
            status_code=400, detail=f"Utwór jest za długi (max {settings['max_duration_s'] // 60} min)"
        )
    if _artist_blocked(artist, store.blocked_artists()):
        raise HTTPException(status_code=403, detail="Ten wykonawca jest zablokowany przez administratorów")

    try:
        suggestion_id = store.insert_suggestion(video_id, title, artist, duration, voter["id"])
    except pymysql.IntegrityError:
        # Ktoś dodał ten sam utwór w tej samej chwili, więc liczymy to jako głos.
        state = store.video_states([video_id], voter["id"], settings["replay_cooldown_days"])[video_id]
        if state["open"]:
            return _vote_on(state["open"]["id"], voter)
        raise HTTPException(status_code=409, detail="Spróbuj ponownie")
    return {"action": "created", "suggestion": _public(store.get_suggestion(suggestion_id, voter["id"]), voter)}


@app.post("/api/suggestions/{suggestion_id}/vote")
def vote(suggestion_id: int, request: Request, voter=Depends(require_voter)):
    rate_limit(request, "vote", voter)
    return _vote_on(suggestion_id, voter)


@app.delete("/api/suggestions/{suggestion_id}/vote")
def unvote(suggestion_id: int, request: Request, voter=Depends(require_voter)):
    rate_limit(request, "vote", voter)
    store.remove_vote(suggestion_id, voter["id"])
    suggestion = store.get_suggestion(suggestion_id, voter["id"])
    if not suggestion:
        raise HTTPException(status_code=404, detail="Nie znaleziono propozycji")
    return {"suggestion": _public(suggestion, voter)}


@app.get("/api/queue")
def queue(voter=Depends(optional_voter)):
    return {"queue": store.list_queue(voter["id"] if voter else None)}


@app.get("/api/board")
def board():
    settings = store.get_settings()
    played_count, played = store.played_today()
    return {
        "requests_open": settings["requests_open"],
        "site_url": SITE_URL,
        "goal": {"played_today": played_count, "daily_goal": settings["daily_goal"]},
        "queue": store.list_queue(None, limit=8),
        "played": played,
    }


@app.post("/api/gorka/login")
def gorka_login(data: GorkaLoginIn, request: Request, voter=Depends(require_voter)):
    rate_limit(request, "gorka", voter, limit=10)
    if not gorka.enabled():
        raise HTTPException(status_code=404, detail="Logowanie przez Górkę jest wyłączone")
    try:
        user = gorka.verify(data.username, data.password)
    except gorka.GorkaUnavailable as e:
        raise HTTPException(status_code=502, detail=str(e))
    if user is None:
        # 400 a nie 401: 401 frontend traktuje jako wygasłą sesję przeglądarki.
        raise HTTPException(status_code=400, detail="Błędny login lub hasło Górki")
    name = f"{user.name} ({user.school_class})" if user.school_class else user.name
    account_id = store.link_gorka(voter, user.id, name[:100])
    return {"token": auth.create_voter_token(account_id), "account": {"name": name}}


# --- administratorzy ---

@app.post("/api/login")
def login(data: LoginData, request: Request):
    rate_limit(request, "login", limit=20)
    token = auth.login(data.username, data.password)
    if token is False:
        raise HTTPException(status_code=401, detail="Błędny login lub hasło")
    return {"token": token}


def _get_or_404(suggestion_id):
    suggestion = store.get_suggestion(suggestion_id)
    if not suggestion:
        raise HTTPException(status_code=404, detail="Nie znaleziono propozycji")
    return suggestion


@app.get("/api/admin/summary")
def admin_summary(user: str = Depends(require_auth)):
    settings = store.get_settings()
    played_count, _ = store.played_today(limit=0)
    return {
        "counts": store.status_counts(),
        "played_today": played_count,
        "daily_goal": settings["daily_goal"],
        "requests_open": settings["requests_open"],
    }


@app.get("/api/admin/suggestions")
def admin_suggestions(status: Status = "pending", user: str = Depends(require_auth)):
    return {"suggestions": store.list_by_status(status)}


@app.post("/api/admin/suggestions/{suggestion_id}/approve")
def approve(suggestion_id: int, user: str = Depends(require_auth)):
    suggestion = _get_or_404(suggestion_id)
    if suggestion["status"] != "pending":
        raise HTTPException(status_code=409, detail="Ta propozycja nie czeka już na decyzję")
    try:
        ytm.client().add_playlist_items(PLAYLIST_ID, [suggestion["video_id"]])
    except Exception:
        logger.exception("Nie udało się dodać %s do playlisty", suggestion["video_id"])
        raise HTTPException(status_code=502, detail="Nie udało się dodać utworu do playlisty YouTube")
    if not store.transition(suggestion_id, ("pending",), "approved", user=user):
        raise HTTPException(status_code=409, detail="Ta propozycja nie czeka już na decyzję")
    return {"success": True}


@app.post("/api/admin/suggestions/{suggestion_id}/reject")
def reject(suggestion_id: int, data: RejectIn, user: str = Depends(require_auth)):
    suggestion = _get_or_404(suggestion_id)
    reason = (data.reason or "").strip() or None
    if not store.transition(suggestion_id, ("pending", "approved"), "rejected", user=user, reason=reason):
        raise HTTPException(status_code=409, detail="Tej propozycji nie można już odrzucić")
    if suggestion["status"] == "approved":
        _try_remove_from_playlist(suggestion["video_id"])
    if data.block:
        label = " - ".join(p for p in (suggestion["artist"], suggestion["title"]) if p)
        store.add_block("video", suggestion["video_id"], label, user)
    return {"success": True}


@app.post("/api/admin/suggestions/{suggestion_id}/played")
def mark_played(suggestion_id: int, user: str = Depends(require_auth)):
    suggestion = _get_or_404(suggestion_id)
    if not store.transition(suggestion_id, ("pending", "approved"), "played", user=user):
        raise HTTPException(status_code=409, detail="Tej propozycji nie można oznaczyć jako zagranej")
    warning = None
    if suggestion["status"] == "approved" and store.get_settings()["remove_when_played"]:
        if not _try_remove_from_playlist(suggestion["video_id"]):
            warning = "Oznaczono jako zagrane, ale nie udało się usunąć utworu z playlisty YouTube"
    return {"success": True, "warning": warning}


@app.post("/api/admin/suggestions/{suggestion_id}/requeue")
def requeue(suggestion_id: int, user: str = Depends(require_auth)):
    _get_or_404(suggestion_id)
    try:
        changed = store.transition(suggestion_id, ("rejected", "played"), "pending")
    except pymysql.IntegrityError:
        raise HTTPException(status_code=409, detail="Ten utwór już jest w kolejce")
    if not changed:
        raise HTTPException(status_code=409, detail="Tę propozycję można przywrócić tylko z historii")
    return {"success": True}


@app.post("/api/admin/suggestions/{suggestion_id}/ban-submitter")
def ban_submitter(suggestion_id: int, user: str = Depends(require_auth)):
    suggestion = _get_or_404(suggestion_id)
    voter = store.get_voter(suggestion["submitted_by"])
    if voter["is_station"]:
        raise HTTPException(status_code=400, detail="Nie można zablokować stanowiska w pokoju radia")
    rejected = store.ban_voter(voter["id"], user)
    return {"success": True, "rejected": rejected}


@app.get("/api/admin/settings")
def admin_get_settings(user: str = Depends(require_auth)):
    return store.get_settings()


@app.put("/api/admin/settings")
def admin_put_settings(data: SettingsIn, user: str = Depends(require_auth)):
    changes = data.model_dump(exclude_none=True)
    for key, value in changes.items():
        if key in store.SETTING_LIMITS:
            low, high = store.SETTING_LIMITS[key]
            if not low <= value <= high:
                raise HTTPException(status_code=400, detail=f"{key}: dozwolony zakres {low} do {high}")
    store.update_settings(changes)
    return store.get_settings()


@app.get("/api/admin/blocklist")
def admin_blocklist(user: str = Depends(require_auth)):
    return {"items": store.list_blocklist()}


@app.post("/api/admin/blocklist")
def admin_add_block(data: BlockIn, user: str = Depends(require_auth)):
    value = data.value.strip()
    if data.kind == "video" and not re.match(VIDEO_ID_PATTERN, value):
        raise HTTPException(status_code=400, detail="Nieprawidłowe ID utworu")
    store.add_block(data.kind, value, data.label, user)
    return {"items": store.list_blocklist()}


@app.delete("/api/admin/blocklist/{block_id}")
def admin_remove_block(block_id: int, user: str = Depends(require_auth)):
    if not store.remove_block(block_id):
        raise HTTPException(status_code=404, detail="Nie znaleziono wpisu")
    return {"items": store.list_blocklist()}


@app.post("/api/admin/station")
def admin_set_station(data: StationIn, user: str = Depends(require_auth)):
    voter = _voter_from_token(data.voter_token)
    if not voter:
        raise HTTPException(status_code=400, detail="Nieprawidłowa sesja przeglądarki")
    store.set_station(voter["id"], data.is_station)
    return {"is_station": data.is_station}


@app.get("/api/admin/stats")
def admin_stats(user: str = Depends(require_auth)):
    return {**store.stats(), "daily_goal": store.get_settings()["daily_goal"]}


def sync_history():
    """Oznacza zatwierdzone utwory jako zagrane, jeśli są w dzisiejszej historii konta YT z browser.json."""
    approved = store.approved_video_ids()
    if not approved:
        return 0
    history = ytm.client().get_history()
    played_today = {h.get("videoId") for h in history if h.get("played") == "Today"}
    remove = store.get_settings()["remove_when_played"]
    marked = 0
    for row in approved:
        if row["video_id"] in played_today and store.transition(row["id"], ("approved",), "played", user="auto"):
            marked += 1
            if remove:
                _try_remove_from_playlist(row["video_id"])
    return marked


async def _history_sync_loop():
    while True:
        await asyncio.sleep(HISTORY_SYNC_INTERVAL_S)
        try:
            settings = await run_in_threadpool(store.get_settings)
            if settings["auto_mark_played"]:
                await run_in_threadpool(sync_history)
        except Exception:
            logger.exception("Synchronizacja historii YouTube nie powiodła się")


@app.post("/api/admin/sync-history")
def sync_history_now(user: str = Depends(require_auth)):
    try:
        marked = sync_history()
    except Exception:
        logger.exception("Synchronizacja historii YouTube nie powiodła się")
        raise HTTPException(status_code=502, detail="Nie udało się pobrać historii YouTube")
    return {"marked": marked}


@app.delete("/api/clear-playlist")
def clear_playlist(user: str = Depends(require_auth)):
    try:
        playlist = ytm.client().get_playlist(PLAYLIST_ID, limit=None)
        tracks = playlist.get("tracks", [])

        if not tracks:
            return {"message": "Playlista jest już pusta.", "removed": 0}

        ytm.client().remove_playlist_items(PLAYLIST_ID, tracks)

        return {
            "message": "Playlista została wyczyszczona.",
            "removed": len(tracks)
        }
    except Exception:
        raise HTTPException(status_code=502, detail="Błąd czyszczenia playlisty")
