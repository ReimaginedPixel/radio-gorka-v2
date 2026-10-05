import logging
import os
import re
import secrets
import threading
import time
from contextlib import asynccontextmanager
from typing import Literal

from dotenv import load_dotenv
from fastapi import BackgroundTasks, Depends, FastAPI, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from ytmusicapi import YTMusic

import auth
import db

load_dotenv()
logging.basicConfig(level=logging.INFO)
log = logging.getLogger("radio-gorka")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
AUTH_FILE = os.getenv("YTMUSIC_AUTH_FILE", os.path.join(BASE_DIR, "browser.json"))
PLAYLIST_ID = os.getenv("PLAYLIST_ID", "PLJhSTAItRjxJl8f9mcHenCKVotPkSDFVB")

# Po tylu sekundach bez sygnału z panelu admina uznajemy, że radio nie gra.
PLAYER_STALE_SECONDS = 25

if os.path.exists(AUTH_FILE):
    yt = YTMusic(AUTH_FILE)
    yt_authed = True
else:
    # Wyszukiwanie działa bez logowania, ale playlista YT nie będzie synchronizowana.
    yt = YTMusic()
    yt_authed = False
    log.warning("Brak %s, playlista YouTube Music nie będzie aktualizowana", AUTH_FILE)


@asynccontextmanager
async def lifespan(app):
    try:
        db.init_db()
    except Exception:
        log.exception("Nie udało się przygotować bazy danych")
    yield


app = FastAPI(title="Radio Górka", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------- modele ----------

VIDEO_ID = r"^[A-Za-z0-9_-]{6,20}$"
TICKET = r"^[0-9a-f]{32}$"


class LoginData(BaseModel):
    username: str
    password: str


class RequestIn(BaseModel):
    videoId: str = Field(pattern=VIDEO_ID)


class TicketRef(BaseModel):
    id: int
    ticket: str = Field(pattern=TICKET)


class LookupIn(BaseModel):
    items: list[TicketRef] = Field(default_factory=list, max_length=50)


class IdsIn(BaseModel):
    ids: list[int] = Field(min_length=1, max_length=500)


class PlayerIn(BaseModel):
    state: Literal["playing", "paused", "stopped"]
    submissionId: int | None = None
    position: float = Field(default=0, ge=0)
    duration: float = Field(default=0, ge=0)


# ---------- pomocnicze ----------

FIELDS = "id, video_id, title, artist, thumbnail, duration_seconds, status, position, created_at"
_SIZE_RE = re.compile(r"=w\d+-h\d+")


def best_thumbnail(thumbnails, video_id):
    if thumbnails:
        best = max(thumbnails, key=lambda t: t.get("width") or 0)
        url = best.get("url") or ""
        # Okładki z YT Music można pobrać w większym rozmiarze zmieniając sufiks adresu.
        if "googleusercontent.com" in url or "ggpht.com" in url:
            url = _SIZE_RE.sub("=w544-h544", url)
        if url:
            return url
    return f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg"


def clean_artist(name):
    name = re.sub(r"\s*-\s*Topic$", "", name or "")
    return re.sub(r"VEVO$", "", name).strip()


def iso(dt):
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ") if dt else None


def track_info(row):
    return {
        "videoId": row["video_id"],
        "title": row["title"],
        "artist": row["artist"],
        "thumbnail": row["thumbnail"],
        "durationSeconds": row["duration_seconds"],
    }


def serialize(row):
    return {
        "id": row["id"],
        **track_info(row),
        "status": row["status"],
        "createdAt": iso(row["created_at"]),
    }


def placeholders(values):
    return ",".join(["%s"] * len(values))


def fetch_queue():
    return db.query(
        f"SELECT {FIELDS} FROM submissions WHERE status = 'accepted' ORDER BY position, id"
    )


def require_admin(authorization: str | None = Header(default=None)):
    token = ""
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization[7:].strip()
    user = auth.auth(token) if token else False
    if not user:
        raise HTTPException(status_code=401, detail="Sesja wygasła, zaloguj się ponownie")
    return user


# ---------- synchronizacja z playlistą YouTube Music ----------

_mirror_lock = threading.Lock()


def _mirror_enabled():
    return yt_authed and bool(PLAYLIST_ID)


def mirror_add(video_ids):
    if not _mirror_enabled():
        return
    with _mirror_lock:
        for video_id in video_ids:
            try:
                yt.add_playlist_items(PLAYLIST_ID, [video_id])
            except Exception:
                log.warning("Nie udało się dodać %s do playlisty YT", video_id, exc_info=True)


def mirror_remove(video_id):
    if not _mirror_enabled():
        return
    with _mirror_lock:
        try:
            tracks = yt.get_playlist(PLAYLIST_ID, limit=None).get("tracks", [])
            track = next(
                (t for t in tracks if t.get("videoId") == video_id and t.get("setVideoId")),
                None,
            )
            if track:
                yt.remove_playlist_items(PLAYLIST_ID, [track])
        except Exception:
            log.warning("Nie udało się usunąć %s z playlisty YT", video_id, exc_info=True)


def mirror_clear():
    if not _mirror_enabled():
        return
    with _mirror_lock:
        try:
            tracks = yt.get_playlist(PLAYLIST_ID, limit=None).get("tracks", [])
            if tracks:
                yt.remove_playlist_items(PLAYLIST_ID, tracks)
        except Exception:
            log.warning("Nie udało się wyczyścić playlisty YT", exc_info=True)


# ---------- stan odtwarzacza (raportowany przez panel admina) ----------

_player_lock = threading.Lock()
_player = {
    "state": "stopped",
    "submissionId": None,
    "track": None,
    "position": 0.0,
    "duration": 0.0,
    "updatedAt": 0.0,
}


def player_snapshot():
    with _player_lock:
        p = dict(_player)
    now = time.time()
    state = p["state"]
    if state in ("playing", "paused") and now - p["updatedAt"] > PLAYER_STALE_SECONDS:
        state = "offline"
    if state not in ("playing", "paused") or not p["track"]:
        return {
            "state": state if state == "offline" else "stopped",
            "submissionId": None,
            "track": None,
            "position": 0,
            "duration": 0,
        }
    position = p["position"]
    if state == "playing":
        position += now - p["updatedAt"]
    if p["duration"]:
        position = min(position, p["duration"])
    return {
        "state": state,
        "submissionId": p["submissionId"],
        "track": p["track"],
        "position": round(position, 2),
        "duration": p["duration"],
    }


# ---------- publiczne API ----------

@app.get("/api/health")
def health():
    return {"ok": True, "playlistSync": _mirror_enabled()}


@app.get("/api/search")
def search(query: str = Query(..., min_length=1, max_length=150)):
    try:
        raw = yt.search(query.strip(), limit=20)
    except Exception:
        log.exception("Wyszukiwanie nie powiodło się")
        raise HTTPException(status_code=502, detail="YouTube Music nie odpowiada, spróbuj ponownie")

    results, seen = [], set()
    for r in raw:
        video_id = r.get("videoId")
        if not video_id or video_id in seen or r.get("resultType") not in ("song", "video"):
            continue
        seen.add(video_id)
        results.append({
            "videoId": video_id,
            "title": r.get("title") or "",
            "artist": ", ".join(a["name"] for a in (r.get("artists") or []) if a.get("name")),
            "thumbnail": best_thumbnail(r.get("thumbnails"), video_id),
            "durationSeconds": r.get("duration_seconds"),
            "type": r["resultType"],
        })
    return {"results": results}


@app.post("/api/requests", status_code=201)
def create_request(data: RequestIn):
    existing = db.query_one(
        "SELECT status FROM submissions WHERE video_id = %s AND status IN ('pending', 'accepted') LIMIT 1",
        (data.videoId,),
    )
    if existing:
        detail = (
            "Ten utwór już czeka na akceptację"
            if existing["status"] == "pending"
            else "Ten utwór już jest w kolejce"
        )
        raise HTTPException(status_code=409, detail=detail)

    try:
        song = yt.get_song(data.videoId)
    except Exception:
        log.exception("get_song nie powiodło się")
        raise HTTPException(status_code=502, detail="Nie udało się pobrać informacji o utworze")
    details = (song or {}).get("videoDetails")
    if not details:
        raise HTTPException(status_code=404, detail="Nie znaleziono utworu o podanym ID")

    length = str(details.get("lengthSeconds") or "")
    ticket = secrets.token_hex(16)
    _, new_id = db.execute(
        "INSERT INTO submissions (video_id, title, artist, thumbnail, duration_seconds, status, ticket, created_at, updated_at) "
        "VALUES (%s, %s, %s, %s, %s, 'pending', %s, UTC_TIMESTAMP(), UTC_TIMESTAMP())",
        (
            data.videoId,
            (details.get("title") or "Bez tytułu")[:255],
            clean_artist(details.get("author"))[:255],
            best_thumbnail((details.get("thumbnail") or {}).get("thumbnails"), data.videoId)[:1024],
            int(length) if length.isdigit() else None,
            ticket,
        ),
    )
    row = db.query_one(f"SELECT {FIELDS} FROM submissions WHERE id = %s", (new_id,))
    return {**serialize(row), "ticket": ticket}


@app.post("/api/requests/lookup")
def lookup_requests(data: LookupIn):
    if not data.items:
        return {"requests": []}
    tickets = {item.id: item.ticket for item in data.items}
    ids = list(tickets)
    rows = db.query(
        f"SELECT {FIELDS}, ticket FROM submissions WHERE id IN ({placeholders(ids)})", ids
    )
    now_playing = player_snapshot()
    playing_id = now_playing["submissionId"]
    queue_ids = [r["id"] for r in fetch_queue() if r["id"] != playing_id]

    result = []
    for r in rows:
        if not secrets.compare_digest(r["ticket"], tickets[r["id"]]):
            continue
        item = serialize(r)
        item["nowPlaying"] = r["id"] == playing_id
        item["queuePosition"] = queue_ids.index(r["id"]) + 1 if r["id"] in queue_ids else None
        result.append(item)
    return {"requests": result}


@app.delete("/api/requests/{request_id}")
def cancel_request(request_id: int, ticket: str = Query(..., pattern=TICKET)):
    row = db.query_one("SELECT status, ticket FROM submissions WHERE id = %s", (request_id,))
    if not row or not secrets.compare_digest(row["ticket"], ticket):
        raise HTTPException(status_code=404, detail="Nie znaleziono zgłoszenia")
    if row["status"] != "pending":
        raise HTTPException(status_code=409, detail="Zgłoszenie zostało już rozpatrzone")
    db.execute(
        "UPDATE submissions SET status = 'cancelled', updated_at = UTC_TIMESTAMP() WHERE id = %s AND status = 'pending'",
        (request_id,),
    )
    return {"success": True}


@app.get("/api/live")
def live():
    now_playing = player_snapshot()
    playing_id = now_playing["submissionId"]
    queue = [serialize(r) for r in fetch_queue() if r["id"] != playing_id]
    pending = db.query_one("SELECT COUNT(*) AS n FROM submissions WHERE status = 'pending'")
    return {"nowPlaying": now_playing, "queue": queue, "pendingCount": pending["n"]}


@app.post("/api/login")
def login(data: LoginData):
    token = auth.login(data.username, data.password)
    if not token:
        raise HTTPException(status_code=401, detail="Błędny login lub hasło")
    return {"token": token}


# ---------- panel admina ----------

@app.get("/api/admin/me")
def me(user=Depends(require_admin)):
    return {"username": user}


@app.get("/api/admin/submissions")
def list_submissions(
    status: str = Query("pending", pattern="^(pending|accepted|rejected|played|removed|cancelled)$"),
    limit: int = Query(200, ge=1, le=500),
    user=Depends(require_admin),
):
    order = "created_at, id" if status == "pending" else "updated_at DESC, id DESC"
    rows = db.query(
        f"SELECT {FIELDS} FROM submissions WHERE status = %s ORDER BY {order} LIMIT %s",
        (status, limit),
    )
    return {"submissions": [serialize(r) for r in rows]}


@app.post("/api/admin/submissions/accept")
def accept_submissions(data: IdsIn, background: BackgroundTasks, user=Depends(require_admin)):
    def run(cur):
        cur.execute(
            f"SELECT id, video_id FROM submissions WHERE status = 'pending' AND id IN ({placeholders(data.ids)}) "
            "ORDER BY created_at, id FOR UPDATE",
            data.ids,
        )
        rows = cur.fetchall()
        cur.execute("SELECT COALESCE(MAX(position), 0) AS p FROM submissions WHERE status = 'accepted'")
        position = cur.fetchone()["p"]
        for r in rows:
            position += 1
            cur.execute(
                "UPDATE submissions SET status = 'accepted', position = %s, updated_at = UTC_TIMESTAMP() WHERE id = %s",
                (position, r["id"]),
            )
        return rows

    rows = db.transaction(run)
    if rows:
        background.add_task(mirror_add, [r["video_id"] for r in rows])
    return {"updated": [r["id"] for r in rows]}


@app.post("/api/admin/submissions/reject")
def reject_submissions(data: IdsIn, user=Depends(require_admin)):
    count, _ = db.execute(
        f"UPDATE submissions SET status = 'rejected', updated_at = UTC_TIMESTAMP() "
        f"WHERE status = 'pending' AND id IN ({placeholders(data.ids)})",
        data.ids,
    )
    return {"updated": count}


@app.get("/api/admin/queue")
def admin_queue(user=Depends(require_admin)):
    return {"queue": [serialize(r) for r in fetch_queue()]}


@app.post("/api/admin/queue/order")
def reorder_queue(data: IdsIn, user=Depends(require_admin)):
    def run(cur):
        cur.execute("SELECT id FROM submissions WHERE status = 'accepted' ORDER BY position, id FOR UPDATE")
        current = [r["id"] for r in cur.fetchall()]
        known = set(current)
        wanted = [i for i in dict.fromkeys(data.ids) if i in known]
        rest = [i for i in current if i not in set(wanted)]
        for position, submission_id in enumerate(wanted + rest, start=1):
            cur.execute("UPDATE submissions SET position = %s WHERE id = %s", (position, submission_id))

    db.transaction(run)
    return {"queue": [serialize(r) for r in fetch_queue()]}


def _finish(submission_id, status, background):
    row = db.query_one(
        "SELECT video_id FROM submissions WHERE id = %s AND status = 'accepted'", (submission_id,)
    )
    if not row:
        return {"success": False}
    db.execute(
        "UPDATE submissions SET status = %s, updated_at = UTC_TIMESTAMP() WHERE id = %s AND status = 'accepted'",
        (status, submission_id),
    )
    background.add_task(mirror_remove, row["video_id"])
    return {"success": True}


@app.post("/api/admin/queue/{submission_id}/played")
def mark_played(submission_id: int, background: BackgroundTasks, user=Depends(require_admin)):
    return _finish(submission_id, "played", background)


@app.delete("/api/admin/queue/{submission_id}")
def remove_from_queue(submission_id: int, background: BackgroundTasks, user=Depends(require_admin)):
    return _finish(submission_id, "removed", background)


@app.delete("/api/admin/queue")
def clear_queue(background: BackgroundTasks, user=Depends(require_admin)):
    count, _ = db.execute(
        "UPDATE submissions SET status = 'removed', updated_at = UTC_TIMESTAMP() WHERE status = 'accepted'"
    )
    background.add_task(mirror_clear)
    return {"removed": count}


@app.post("/api/admin/player")
def update_player(data: PlayerIn, user=Depends(require_admin)):
    track = None
    if data.submissionId is not None and data.state != "stopped":
        with _player_lock:
            if _player["submissionId"] == data.submissionId:
                track = _player["track"]
        if track is None:
            row = db.query_one(f"SELECT {FIELDS} FROM submissions WHERE id = %s", (data.submissionId,))
            if row:
                track = track_info(row)

    with _player_lock:
        _player.update(
            state=data.state if track else "stopped",
            submissionId=data.submissionId if track else None,
            track=track,
            position=data.position,
            duration=data.duration or (track or {}).get("durationSeconds") or 0,
            updatedAt=time.time(),
        )
    return player_snapshot()
