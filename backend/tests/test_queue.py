import gorka

SONG = "dQw4w9WgXcQ"
SONG_2 = "kJQP7kiw5Fk"
SONG_3 = "9bZkp7q19f0"


def suggest(client, headers, video_id=SONG):
    return client.post("/api/suggestions", json={"videoId": video_id}, headers=headers)


def admin_list(client, admin, status="pending"):
    return client.get("/api/admin/suggestions", params={"status": status}, headers=admin).json()["suggestions"]


def test_duplicate_suggestion_becomes_vote(client, yt, new_voter):
    yt.add_song(SONG, "Piosenka")
    alice, bob = new_voter(), new_voter()

    first = suggest(client, alice).json()
    assert first["action"] == "created"
    assert first["suggestion"]["votes"] == 1
    assert first["suggestion"]["mine"] is True

    second = suggest(client, bob).json()
    assert second["action"] == "voted"
    assert second["suggestion"]["id"] == first["suggestion"]["id"]
    assert second["suggestion"]["votes"] == 2
    assert second["suggestion"]["mine"] is False

    again = suggest(client, alice).json()
    assert again["suggestion"]["votes"] == 2


def test_one_vote_per_voter_and_unvote(client, yt, new_voter):
    yt.add_song(SONG, "Piosenka")
    alice, bob = new_voter(), new_voter()
    suggestion_id = suggest(client, alice).json()["suggestion"]["id"]

    for _ in range(3):
        res = client.post(f"/api/suggestions/{suggestion_id}/vote", headers=bob)
    assert res.json()["suggestion"]["votes"] == 2
    assert res.json()["suggestion"]["voted_by_me"] is True

    res = client.delete(f"/api/suggestions/{suggestion_id}/vote", headers=bob)
    assert res.json()["suggestion"]["votes"] == 1
    assert res.json()["suggestion"]["voted_by_me"] is False


def test_queue_sorted_by_votes(client, yt, new_voter, admin):
    yt.add_song(SONG, "Mało głosów")
    yt.add_song(SONG_2, "Dużo głosów")
    alice, bob, carol = new_voter(), new_voter(), new_voter()
    suggest(client, alice, SONG)
    suggest(client, alice, SONG_2)
    suggest(client, bob, SONG_2)
    suggest(client, carol, SONG_2)

    queue = client.get("/api/queue", headers=alice).json()["queue"]
    assert [q["video_id"] for q in queue] == [SONG_2, SONG]
    assert queue[0]["votes"] == 3
    assert "submitted_by" not in queue[0]

    assert [s["video_id"] for s in admin_list(client, admin)] == [SONG_2, SONG]


def test_daily_limit_blocks_new_songs_but_not_votes(client, yt, new_voter, admin):
    client.put("/api/admin/settings", json={"max_per_day_anon": 2}, headers=admin)
    for vid in (SONG, SONG_2, SONG_3):
        yt.add_song(vid, vid)
    alice, bob = new_voter(), new_voter()
    assert suggest(client, alice, SONG).status_code == 200
    assert suggest(client, alice, SONG_2).status_code == 200
    assert suggest(client, alice, SONG_3).status_code == 429

    suggest(client, bob, SONG_3)
    assert suggest(client, alice, SONG_3).json()["action"] == "voted"
    assert client.get("/api/me", headers=alice).json()["remaining_today"] == 0


def test_station_gets_higher_limit(client, yt, new_voter, admin):
    client.put("/api/admin/settings", json={"max_per_day_anon": 1}, headers=admin)
    station = new_voter()
    res = client.post(
        "/api/admin/station", json={"voter_token": station["X-Voter-Token"], "is_station": True}, headers=admin
    )
    assert res.status_code == 200
    me = client.get("/api/me", headers=station).json()
    assert me["is_station"] is True
    assert me["daily_limit"] == 30


def test_played_song_has_cooldown(client, yt, new_voter, admin):
    yt.add_song(SONG, "Piosenka")
    alice, bob = new_voter(), new_voter()
    suggestion_id = suggest(client, alice).json()["suggestion"]["id"]
    client.post(f"/api/admin/suggestions/{suggestion_id}/approve", headers=admin)
    client.post(f"/api/admin/suggestions/{suggestion_id}/played", headers=admin)

    assert suggest(client, bob).status_code == 409
    result = client.get("/api/search", params={"query": "x"}, headers=bob).json()["results"][0]
    assert result["state"] == "played_recently"


def test_blocklist_video_and_artist(client, yt, new_voter, admin):
    yt.add_song(SONG, "Zablokowana")
    yt.add_song(SONG_2, "Inna", author="Zły Artysta & Kolega")
    alice = new_voter()
    client.post("/api/admin/blocklist", json={"kind": "video", "value": SONG}, headers=admin)
    client.post("/api/admin/blocklist", json={"kind": "artist", "value": "zły artysta"}, headers=admin)

    assert suggest(client, alice, SONG).status_code == 403
    assert suggest(client, alice, SONG_2).status_code == 403
    states = {r["videoId"]: r["state"] for r in client.get("/api/search", params={"query": "x"}).json()["results"]}
    assert states == {SONG: "blocked", SONG_2: "blocked"}


def test_search_states(client, yt, new_voter, admin):
    yt.add_song(SONG, "Nowa")
    yt.add_song(SONG_2, "W kolejce")
    yt.add_song(SONG_3, "Za długa", length=900)
    alice = new_voter()
    suggest(client, alice, SONG_2)

    results = {r["videoId"]: r for r in client.get("/api/search", params={"query": "x"}, headers=alice).json()["results"]}
    assert len(results) == 3
    assert results[SONG]["state"] == "new"
    assert results[SONG_2]["state"] == "queued"
    assert results[SONG_2]["voted_by_me"] is True
    assert results[SONG_3]["state"] == "too_long"
    assert suggest(client, alice, SONG_3).status_code == 400


def test_requests_closed(client, yt, new_voter, admin):
    yt.add_song(SONG, "Piosenka")
    client.put("/api/admin/settings", json={"requests_open": False}, headers=admin)
    assert suggest(client, new_voter()).status_code == 403
    assert client.get("/api/board").json()["requests_open"] is False


def test_approve_adds_to_playlist(client, yt, new_voter, admin):
    yt.add_song(SONG, "Piosenka")
    suggestion_id = suggest(client, new_voter()).json()["suggestion"]["id"]

    assert client.post(f"/api/admin/suggestions/{suggestion_id}/approve", headers=admin).status_code == 200
    assert [t["videoId"] for t in yt.playlist] == [SONG]
    assert admin_list(client, admin, "approved")[0]["decided_by"] == "dj"
    assert client.get("/api/admin/summary", headers=admin).json()["counts"] == {"pending": 0, "approved": 1}


def test_approve_failure_keeps_pending(client, yt, new_voter, admin):
    yt.add_song(SONG, "Piosenka")
    suggestion_id = suggest(client, new_voter()).json()["suggestion"]["id"]
    yt.fail_add = True

    assert client.post(f"/api/admin/suggestions/{suggestion_id}/approve", headers=admin).status_code == 502
    assert admin_list(client, admin)[0]["status"] == "pending"


def test_played_removes_from_playlist_and_counts_for_goal(client, yt, new_voter, admin):
    yt.add_song(SONG, "Piosenka")
    suggestion_id = suggest(client, new_voter()).json()["suggestion"]["id"]
    client.post(f"/api/admin/suggestions/{suggestion_id}/approve", headers=admin)

    res = client.post(f"/api/admin/suggestions/{suggestion_id}/played", headers=admin).json()
    assert res["warning"] is None
    assert yt.playlist == []
    board = client.get("/api/board").json()
    assert board["goal"]["played_today"] == 1
    assert board["played"][0]["video_id"] == SONG
    assert board["queue"] == []


def test_reject_reason_visible_to_student_and_requeue(client, yt, new_voter, admin):
    yt.add_song(SONG, "Piosenka")
    alice = new_voter()
    suggestion_id = suggest(client, alice).json()["suggestion"]["id"]

    client.post(f"/api/admin/suggestions/{suggestion_id}/reject", json={"reason": "Wulgarne"}, headers=admin)
    mine = client.get("/api/me", headers=alice).json()["suggestions"][0]
    assert mine["status"] == "rejected"
    assert mine["reject_reason"] == "Wulgarne"

    assert client.post(f"/api/admin/suggestions/{suggestion_id}/requeue", headers=admin).status_code == 200
    mine = client.get("/api/me", headers=alice).json()["suggestions"][0]
    assert mine["status"] == "pending"
    assert mine["reject_reason"] is None


def test_reject_with_block(client, yt, new_voter, admin):
    yt.add_song(SONG, "Piosenka", author="Ktoś")
    suggestion_id = suggest(client, new_voter()).json()["suggestion"]["id"]
    client.post(f"/api/admin/suggestions/{suggestion_id}/reject", json={"block": True}, headers=admin)

    items = client.get("/api/admin/blocklist", headers=admin).json()["items"]
    assert items[0]["value"] == SONG
    assert items[0]["label"] == "Ktoś - Piosenka"


def test_ban_submitter(client, yt, new_voter, admin):
    yt.add_song(SONG, "Spam")
    spammer = new_voter()
    suggestion_id = suggest(client, spammer).json()["suggestion"]["id"]

    assert client.post(f"/api/admin/suggestions/{suggestion_id}/ban-submitter", headers=admin).json()["rejected"] == 1
    assert client.get("/api/me", headers=spammer).status_code == 403


def test_tokens_cannot_cross_roles(client, new_voter, admin):
    voter = new_voter()
    as_admin = {"Authorization": f"Bearer {voter['X-Voter-Token']}"}
    assert client.get("/api/admin/suggestions", headers=as_admin).status_code == 401

    admin_token = admin["Authorization"].split(" ", 1)[1]
    assert client.get("/api/me", headers={"X-Voter-Token": admin_token}).status_code == 401
    assert client.get("/api/me").status_code == 401


def test_sync_history_marks_played(client, yt, new_voter, admin):
    yt.add_song(SONG, "Piosenka")
    suggestion_id = suggest(client, new_voter()).json()["suggestion"]["id"]
    client.post(f"/api/admin/suggestions/{suggestion_id}/approve", headers=admin)
    yt.history = [{"videoId": SONG, "played": "Today"}]

    assert client.post("/api/admin/sync-history", headers=admin).json() == {"marked": 1}
    assert admin_list(client, admin, "played")[0]["decided_by"] == "dj"


def test_gorka_login_merges_browser_votes(client, yt, new_voter, monkeypatch):
    monkeypatch.setattr(gorka, "enabled", lambda: True)
    monkeypatch.setattr(gorka, "verify", lambda u, p: gorka.GorkaUser(id="42", name="Jan K.", school_class="3B"))
    yt.add_song(SONG, "Piosenka")
    yt.add_song(SONG_2, "Druga")
    phone, laptop, author = new_voter(), new_voter(), new_voter()
    suggestion_id = suggest(client, author, SONG).json()["suggestion"]["id"]
    suggest(client, author, SONG_2)
    client.post(f"/api/suggestions/{suggestion_id}/vote", headers=phone)
    client.post(f"/api/suggestions/{suggestion_id}/vote", headers=laptop)

    def login(headers):
        res = client.post("/api/gorka/login", json={"username": "jan", "password": "x"}, headers=headers)
        assert res.status_code == 200
        return {"X-Voter-Token": res.json()["token"]}

    account = login(phone)
    assert client.get("/api/me", headers=account).json()["account"] == {"name": "Jan K. (3B)"}
    account_again = login(laptop)

    queue = {q["video_id"]: q for q in client.get("/api/queue", headers=account_again).json()["queue"]}
    assert queue[SONG]["votes"] == 2
    assert queue[SONG]["voted_by_me"] is True


def test_gorka_login_from_station_does_not_take_station_votes(client, yt, new_voter, admin, monkeypatch):
    monkeypatch.setattr(gorka, "enabled", lambda: True)
    monkeypatch.setattr(gorka, "verify", lambda u, p: gorka.GorkaUser(id="7", name="Ola"))
    yt.add_song(SONG, "Piosenka")
    station = new_voter()
    client.post("/api/admin/station", json={"voter_token": station["X-Voter-Token"], "is_station": True}, headers=admin)
    suggest(client, station)

    res = client.post("/api/gorka/login", json={"username": "ola", "password": "x"}, headers=station)
    account = {"X-Voter-Token": res.json()["token"]}
    assert client.get("/api/me", headers=account).json()["suggestions"] == []
    assert len(client.get("/api/me", headers=station).json()["suggestions"]) == 1


def test_gorka_wrong_password_is_not_401(client, new_voter, monkeypatch):
    monkeypatch.setattr(gorka, "enabled", lambda: True)
    monkeypatch.setattr(gorka, "verify", lambda u, p: None)
    res = client.post("/api/gorka/login", json={"username": "jan", "password": "zle"}, headers=new_voter())
    assert res.status_code == 400
