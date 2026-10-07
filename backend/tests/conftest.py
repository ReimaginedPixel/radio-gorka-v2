"""Testy wymagają pustej bazy MySQL/MariaDB. Uruchomienie:

    TEST_DB_NAME=radio_gorka_test TEST_DB_USER=... TEST_DB_PASSWORD=... pytest

Bez TEST_DB_NAME wszystkie testy są pomijane. YouTube Music jest zastąpione atrapą.
"""
import os
import sys

import pytest

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BACKEND_DIR)

TEST_DB_NAME = os.getenv("TEST_DB_NAME")

# Ustawione przed importem modułów aplikacji, więc load_dotenv() nie nadpisze ich wartościami z .env.
os.environ.update({
    "domain": os.getenv("TEST_DB_HOST", "localhost"),
    "username": os.getenv("TEST_DB_USER", "radio"),
    "password": os.getenv("TEST_DB_PASSWORD", "radio"),
    "database": TEST_DB_NAME or "",
    "port": os.getenv("TEST_DB_PORT", "3306"),
    "jwt_secret": "test-secret-not-for-production-0123456789abcdef",
    "gorka_api_url": "",
})

TABLES = ("votes", "suggestions", "voters", "blocklist", "settings", "users")


class FakeYT:
    def __init__(self):
        self.songs = {}
        self.playlist = []
        self.history = []
        self.fail_add = False
        self._set_id = 0

    def add_song(self, video_id, title, author="Artysta", length=200):
        self.songs[video_id] = {"title": title, "author": author, "length": length}

    def get_song(self, video_id):
        song = self.songs.get(video_id)
        if not song:
            return {"playabilityStatus": {"status": "ERROR"}}
        return {"videoDetails": {
            "videoId": video_id,
            "title": song["title"],
            "author": song["author"],
            "lengthSeconds": str(song["length"]),
        }}

    def search(self, query):
        return [
            {
                "videoId": vid,
                "title": s["title"],
                "artists": [{"name": s["author"]}],
                "duration_seconds": s["length"],
            }
            for vid, s in self.songs.items()
        ] + [{"browseId": "artist-without-video", "resultType": "artist"}]

    def add_playlist_items(self, playlist_id, video_ids):
        if self.fail_add:
            raise RuntimeError("YT down")
        for vid in video_ids:
            self._set_id += 1
            self.playlist.append({"videoId": vid, "setVideoId": f"set{self._set_id}"})
        return {"status": "STATUS_SUCCEEDED"}

    def get_playlist(self, playlist_id, limit=None):
        return {"tracks": list(self.playlist)}

    def remove_playlist_items(self, playlist_id, videos):
        remove = {v["setVideoId"] for v in videos}
        self.playlist = [t for t in self.playlist if t["setVideoId"] not in remove]

    def get_history(self):
        return self.history


@pytest.fixture(scope="session")
def main_module():
    if not TEST_DB_NAME:
        pytest.skip("TEST_DB_NAME nie ustawione, pomijam testy bazy")
    import db
    import main
    db.init_db()
    return main


@pytest.fixture
def yt(main_module):
    import db
    import ytm
    with db.cursor() as cur:
        cur.execute("SET FOREIGN_KEY_CHECKS = 0")
        for table in TABLES:
            cur.execute(f"TRUNCATE TABLE {table}")
        cur.execute("SET FOREIGN_KEY_CHECKS = 1")
    main_module._rate_state.clear()
    fake = FakeYT()
    ytm._client = fake
    yield fake
    ytm._client = None


@pytest.fixture
def client(main_module, yt):
    from fastapi.testclient import TestClient
    return TestClient(main_module.app)


@pytest.fixture
def new_voter(client):
    def make():
        token = client.post("/api/session").json()["token"]
        return {"X-Voter-Token": token}
    return make


@pytest.fixture
def admin(client):
    import bcrypt
    import db
    hashed = bcrypt.hashpw(b"haslo123", bcrypt.gensalt()).decode()
    with db.cursor() as cur:
        cur.execute("INSERT INTO users (username, password) VALUES ('dj', %s)", (hashed,))
    token = client.post("/api/login", json={"username": "dj", "password": "haslo123"}).json()["token"]
    return {"Authorization": f"Bearer {token}"}
