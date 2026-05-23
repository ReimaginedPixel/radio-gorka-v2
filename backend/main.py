import time
from collections import defaultdict

from fastapi import FastAPI, HTTPException, Depends, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from ytmusicapi import YTMusic
import auth
from pydantic import BaseModel
from dotenv import load_dotenv
import os

load_dotenv()

PLAYLIST_ID = os.getenv("playlist_id", "PLJhSTAItRjxJl8f9mcHenCKVotPkSDFVB")

_allowed = os.getenv("allowed_origins", "")
ALLOWED_ORIGINS = [o.strip() for o in _allowed.split(",") if o.strip()] or [
    "http://localhost:5173",
]

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

yt = YTMusic('browser.json')


class LoginData(BaseModel):
    username: str
    password: str


def require_auth(authorization: str = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Brak tokenu autoryzacji")
    token = authorization.split(" ", 1)[1]
    user = auth.auth(token)
    if not user:
        raise HTTPException(status_code=401, detail="Klucz JWT niepoprawny")
    return user


_RATE_LIMIT = int(os.getenv("rate_limit", 30))
_RATE_WINDOW = 60
# Best-effort in-memory limiter; not shared across workers/restarts.
_rate_state = defaultdict(list)


def rate_limit(request: Request, bucket: str):
    ip = request.client.host if request.client else "unknown"
    now = time.time()
    hits = _rate_state[(bucket, ip)]
    cutoff = now - _RATE_WINDOW
    while hits and hits[0] < cutoff:
        hits.pop(0)
    if len(hits) >= _RATE_LIMIT:
        raise HTTPException(status_code=429, detail="Zbyt wiele żądań, spróbuj ponownie później")
    hits.append(now)


@app.get("/api/search")
async def search(query: str, request: Request):
    rate_limit(request, "search")
    try:
        search_results = yt.search(query)
    except Exception:
        raise HTTPException(status_code=502, detail="Błąd wyszukiwania w YouTube Music")
    filtered = [
        {
            "videoId": r.get("videoId"),
            "title": r.get("title") or r.get("artist"),
            "artist": r["artists"][0]["name"] if r.get("artists") else None,
            "thumbnail": next((t["url"] for t in r.get("thumbnails", []) if t["width"] == 60), None),
        }
        for r in search_results
    ]
    return {"results": filtered}


@app.get("/api/add")
async def add(videoID: str, request: Request):
    rate_limit(request, "add")
    try:
        song = yt.get_song(videoID)
    except Exception:
        raise HTTPException(status_code=400, detail="Nieprawidłowe ID utworu")

    if not song or not song.get("videoDetails"):
        raise HTTPException(status_code=404, detail="Nie znaleziono piosenki o podanym ID")

    try:
        yt.add_playlist_items(PLAYLIST_ID, [videoID])
    except Exception:
        raise HTTPException(status_code=502, detail="Nie udało się dodać utworu do playlisty")

    return {"success": True, "videoID": videoID}


@app.post("/api/login")
async def login(data: LoginData):
    token = auth.login(data.username, data.password)
    if token is False:
        raise HTTPException(status_code=401, detail="Błędny login lub hasło")
    return {"token": token}


@app.get("/api/list")
async def list_tracks(user: str = Depends(require_auth)):
    try:
        playlist = yt.get_playlist(PLAYLIST_ID, limit=None)
        playlist_tracks = playlist.get("tracks", [])
    except Exception:
        raise HTTPException(status_code=502, detail="Błąd pobierania playlisty")

    result = []
    for track in playlist_tracks:
        videoID = track.get("videoId")
        thumbnails = track.get("thumbnails") or []
        result.append({
            "videoID": videoID,
            "title": track.get("title"),
            "author": ", ".join(
                a["name"] for a in (track.get("artists") or [])
            ),
            "lengthSeconds": track.get("duration_seconds"),
            "thumbnail": thumbnails[-1].get("url") if thumbnails else None,
            "url": f"https://music.youtube.com/watch?v={videoID}"
        })

    return result


@app.delete("/api/delete")
async def decline(videoID: str, user: str = Depends(require_auth)):
    try:
        playlist = yt.get_playlist(PLAYLIST_ID, limit=None)
        playlist_tracks = playlist.get("tracks", [])
    except Exception:
        raise HTTPException(status_code=502, detail="Błąd pobierania playlisty")

    track = next(
        (t for t in playlist_tracks if t.get("videoId") == videoID),
        None
    )

    if not track:
        raise HTTPException(status_code=404, detail="Nie znaleziono utworu w playliście")

    set_video_id = track.get("setVideoId")
    if not set_video_id:
        raise HTTPException(status_code=500, detail="Brak setVideoId — nie można usunąć utworu")

    try:
        yt.remove_playlist_items(PLAYLIST_ID, [{"videoId": videoID, "setVideoId": set_video_id}])
    except Exception:
        raise HTTPException(status_code=502, detail="Błąd usuwania z playlisty")

    return {"success": True, "videoID": videoID}


@app.delete("/api/clear-playlist")
async def clear_playlist(user: str = Depends(require_auth)):
    try:
        playlist = yt.get_playlist(PLAYLIST_ID, limit=None)
        tracks = playlist.get("tracks", [])

        if not tracks:
            return {"message": "Playlista jest już pusta.", "removed": 0}

        yt.remove_playlist_items(PLAYLIST_ID, tracks)

        return {
            "message": "Playlista została wyczyszczona.",
            "removed": len(tracks)
        }
    except Exception:
        raise HTTPException(status_code=502, detail="Błąd czyszczenia playlisty")
