import os

from ytmusicapi import YTMusic

_client = None


def client():
    """YTMusic tworzony przy pierwszym użyciu, żeby backend startował bez browser.json."""
    global _client
    if _client is None:
        _client = YTMusic(os.getenv("yt_auth_file", "browser.json"))
    return _client


def remove_from_playlist(playlist_id, video_id):
    """Usuwa wszystkie wystąpienia utworu z playlisty. Zwraca False, jeśli go tam nie było."""
    playlist = client().get_playlist(playlist_id, limit=None)
    tracks = [
        {"videoId": t["videoId"], "setVideoId": t["setVideoId"]}
        for t in playlist.get("tracks", [])
        if t.get("videoId") == video_id and t.get("setVideoId")
    ]
    if not tracks:
        return False
    client().remove_playlist_items(playlist_id, tracks)
    return True
