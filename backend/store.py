"""Dostęp do bazy: głosujący, propozycje, głosy, blocklista i ustawienia."""
import secrets

from db import cursor

DEFAULT_SETTINGS = {
    "requests_open": True,
    "daily_goal": 3,
    "max_per_day_anon": 3,
    "max_per_day_account": 6,
    "max_per_day_station": 30,
    "max_duration_s": 480,
    "replay_cooldown_days": 7,
    "remove_when_played": True,
    "auto_mark_played": False,
}

SETTING_LIMITS = {
    "daily_goal": (0, 100),
    "max_per_day_anon": (0, 100),
    "max_per_day_account": (0, 100),
    "max_per_day_station": (0, 1000),
    "max_duration_s": (60, 3600),
    "replay_cooldown_days": (0, 365),
}

# Kolumny propozycji widoczne dla wszystkich. submitted_by nigdy nie wychodzi na zewnątrz.
_PUBLIC_COLUMNS = (
    "s.id, s.video_id, s.title, s.artist, s.duration_seconds, s.status, "
    "s.reject_reason, s.created_at, s.decided_at, s.played_at"
)
_VOTES = "(SELECT COUNT(*) FROM votes v WHERE v.suggestion_id = s.id) AS votes"
_VOTED_BY = (
    "EXISTS(SELECT 1 FROM votes v WHERE v.suggestion_id = s.id AND v.voter_id = %s) AS voted_by_me"
)


def _parse_setting(key, raw):
    default = DEFAULT_SETTINGS[key]
    if isinstance(default, bool):
        return raw in ("1", "true", "True")
    return int(raw)


def _bools(rows, *keys):
    for row in rows:
        for key in keys:
            row[key] = bool(row[key])
    return rows


# --- ustawienia ---

def get_settings():
    with cursor() as cur:
        cur.execute("SELECT k, v FROM settings")
        rows = cur.fetchall()
    settings = dict(DEFAULT_SETTINGS)
    for row in rows:
        if row["k"] in settings:
            settings[row["k"]] = _parse_setting(row["k"], row["v"])
    return settings


def update_settings(changes):
    with cursor() as cur:
        for key, value in changes.items():
            raw = ("1" if value else "0") if isinstance(value, bool) else str(value)
            cur.execute(
                "INSERT INTO settings (k, v) VALUES (%s, %s) ON DUPLICATE KEY UPDATE v = VALUES(v)",
                (key, raw),
            )


# --- głosujący ---

def create_voter():
    voter_id = secrets.token_hex(16)
    with cursor() as cur:
        cur.execute("INSERT INTO voters (id) VALUES (%s)", (voter_id,))
    return voter_id


def get_voter(voter_id):
    with cursor() as cur:
        cur.execute(
            "SELECT id, gorka_id, display_name, is_station, banned FROM voters WHERE id = %s",
            (voter_id,),
        )
        row = cur.fetchone()
    if row:
        _bools([row], "is_station", "banned")
    return row


def set_station(voter_id, is_station):
    with cursor() as cur:
        cur.execute("UPDATE voters SET is_station = %s WHERE id = %s", (int(is_station), voter_id))
        return cur.rowcount == 1


def link_gorka(voter, gorka_id, display_name):
    """Zwraca id głosującego przypisanego do konta Górka.

    Jeśli ta przeglądarka była anonimowa (i nie jest stanowiskiem w pokoju),
    jej głosy i propozycje przechodzą na konto, żeby jedna osoba nie głosowała dwa razy.
    """
    with cursor() as cur:
        cur.execute("SELECT id FROM voters WHERE gorka_id = %s FOR UPDATE", (gorka_id,))
        row = cur.fetchone()
        if row:
            account_id = row["id"]
            cur.execute("UPDATE voters SET display_name = %s WHERE id = %s", (display_name, account_id))
        else:
            account_id = secrets.token_hex(16)
            cur.execute(
                "INSERT INTO voters (id, gorka_id, display_name) VALUES (%s, %s, %s)",
                (account_id, gorka_id, display_name),
            )

        anonymous = voter["gorka_id"] is None and not voter["is_station"]
        if anonymous and voter["id"] != account_id:
            cur.execute(
                "INSERT IGNORE INTO votes (suggestion_id, voter_id, created_at) "
                "SELECT suggestion_id, %s, created_at FROM votes WHERE voter_id = %s",
                (account_id, voter["id"]),
            )
            cur.execute("DELETE FROM votes WHERE voter_id = %s", (voter["id"],))
            cur.execute(
                "UPDATE suggestions SET submitted_by = %s WHERE submitted_by = %s",
                (account_id, voter["id"]),
            )
    return account_id


def ban_voter(voter_id, banned_by):
    """Blokuje autora i odrzuca jego oczekujące propozycje. Zwraca liczbę odrzuconych."""
    with cursor() as cur:
        cur.execute("UPDATE voters SET banned = 1 WHERE id = %s", (voter_id,))
        cur.execute(
            "UPDATE suggestions SET status = 'rejected', reject_reason = 'Autor zablokowany', "
            "decided_at = NOW(), decided_by = %s "
            "WHERE submitted_by = %s AND status = 'pending'",
            (banned_by, voter_id),
        )
        return cur.rowcount


def count_submitted_today(voter_id):
    with cursor() as cur:
        cur.execute(
            "SELECT COUNT(*) AS c FROM suggestions WHERE submitted_by = %s AND created_at >= CURDATE()",
            (voter_id,),
        )
        return cur.fetchone()["c"]


# --- propozycje ---

def video_states(video_ids, voter_id, cooldown_days):
    """Dla każdego video_id: otwarta propozycja, czy grane niedawno, czy odrzucone wczoraj/dziś, czy zablokowane."""
    states = {
        vid: {"open": None, "played_recently": False, "rejected_recently": False, "blocked": False}
        for vid in video_ids
    }
    if not video_ids:
        return states
    placeholders = ", ".join(["%s"] * len(video_ids))
    with cursor() as cur:
        cur.execute(
            f"SELECT s.id, s.video_id, s.status, {_VOTES}, {_VOTED_BY} "
            f"FROM suggestions s WHERE s.video_id IN ({placeholders}) AND ("
            "  s.status IN ('pending', 'approved')"
            "  OR (s.status = 'played' AND s.played_at >= NOW() - INTERVAL %s DAY)"
            "  OR (s.status = 'rejected' AND s.decided_at >= NOW() - INTERVAL 1 DAY))",
            (voter_id, *video_ids, cooldown_days),
        )
        for row in cur.fetchall():
            state = states[row["video_id"]]
            if row["status"] in ("pending", "approved"):
                row["voted_by_me"] = bool(row["voted_by_me"])
                state["open"] = row
            elif row["status"] == "played":
                state["played_recently"] = True
            else:
                state["rejected_recently"] = True
        cur.execute(
            f"SELECT value FROM blocklist WHERE kind = 'video' AND value IN ({placeholders})",
            tuple(video_ids),
        )
        for row in cur.fetchall():
            states[row["value"]]["blocked"] = True
    return states


def blocked_artists():
    with cursor() as cur:
        cur.execute("SELECT value FROM blocklist WHERE kind = 'artist'")
        return {row["value"].strip().lower() for row in cur.fetchall()}


def insert_suggestion(video_id, title, artist, duration_seconds, voter_id):
    """Dodaje propozycję i od razu głos autora. Rzuca IntegrityError, gdy utwór jest już w kolejce."""
    with cursor() as cur:
        cur.execute(
            "INSERT INTO suggestions (video_id, title, artist, duration_seconds, submitted_by) "
            "VALUES (%s, %s, %s, %s, %s)",
            (video_id, title[:255], artist[:255] if artist else None, duration_seconds, voter_id),
        )
        suggestion_id = cur.lastrowid
        cur.execute(
            "INSERT INTO votes (suggestion_id, voter_id) VALUES (%s, %s)", (suggestion_id, voter_id)
        )
    return suggestion_id


def get_suggestion(suggestion_id, voter_id=None):
    with cursor() as cur:
        cur.execute(
            f"SELECT {_PUBLIC_COLUMNS}, s.submitted_by, {_VOTES}, {_VOTED_BY} "
            "FROM suggestions s WHERE s.id = %s",
            (voter_id, suggestion_id),
        )
        row = cur.fetchone()
    if row:
        _bools([row], "voted_by_me")
    return row


def add_vote(suggestion_id, voter_id):
    """Głos tylko na otwartą propozycję. Zwraca False, jeśli propozycja nie jest otwarta."""
    with cursor() as cur:
        cur.execute(
            "SELECT 1 FROM suggestions WHERE id = %s AND status IN ('pending', 'approved')",
            (suggestion_id,),
        )
        if cur.fetchone() is None:
            return False
        cur.execute(
            "INSERT IGNORE INTO votes (suggestion_id, voter_id) VALUES (%s, %s)",
            (suggestion_id, voter_id),
        )
    return True


def remove_vote(suggestion_id, voter_id):
    with cursor() as cur:
        cur.execute(
            "DELETE FROM votes WHERE suggestion_id = %s AND voter_id = %s", (suggestion_id, voter_id)
        )


def list_queue(voter_id, limit=100):
    with cursor() as cur:
        cur.execute(
            f"SELECT {_PUBLIC_COLUMNS}, {_VOTES}, {_VOTED_BY}, (s.submitted_by = %s) AS mine "
            "FROM suggestions s WHERE s.status IN ('pending', 'approved') "
            "ORDER BY votes DESC, s.created_at ASC LIMIT %s",
            (voter_id, voter_id, limit),
        )
        return _bools(cur.fetchall(), "voted_by_me", "mine")


def list_mine(voter_id, limit=30):
    with cursor() as cur:
        cur.execute(
            f"SELECT {_PUBLIC_COLUMNS}, {_VOTES} FROM suggestions s "
            "WHERE s.submitted_by = %s ORDER BY s.created_at DESC LIMIT %s",
            (voter_id, limit),
        )
        return cur.fetchall()


_ADMIN_ORDER = {
    "pending": "votes DESC, s.created_at ASC",
    "approved": "votes DESC, s.decided_at ASC",
    "played": "s.played_at DESC",
    "rejected": "s.decided_at DESC",
}


def list_by_status(status, limit=200):
    with cursor() as cur:
        cur.execute(
            f"SELECT {_PUBLIC_COLUMNS}, s.decided_by, {_VOTES}, "
            "vo.display_name AS submitter_name, vo.is_station AS submitter_is_station "
            "FROM suggestions s JOIN voters vo ON vo.id = s.submitted_by "
            f"WHERE s.status = %s ORDER BY {_ADMIN_ORDER[status]} LIMIT %s",
            (status, limit),
        )
        return _bools(cur.fetchall(), "submitter_is_station")


def transition(suggestion_id, from_statuses, to_status, user=None, reason=None):
    """Zmienia status tylko z dozwolonych stanów. Zwraca True, jeśli coś się zmieniło.

    Powrót do kolejki może rzucić IntegrityError, gdy ten sam utwór jest już otwarty.
    """
    sets = ["status = %s"]
    params = [to_status]
    if to_status in ("approved", "rejected"):
        sets += ["decided_at = NOW()", "decided_by = %s"]
        params.append(user)
    if to_status == "rejected":
        sets.append("reject_reason = %s")
        params.append(reason)
    if to_status == "played":
        sets += [
            "played_at = NOW()",
            "decided_at = COALESCE(decided_at, NOW())",
            "decided_by = COALESCE(decided_by, %s)",
        ]
        params.append(user)
    if to_status == "pending":
        sets += ["reject_reason = NULL", "decided_at = NULL", "decided_by = NULL", "played_at = NULL"]

    placeholders = ", ".join(["%s"] * len(from_statuses))
    with cursor() as cur:
        cur.execute(
            f"UPDATE suggestions SET {', '.join(sets)} WHERE id = %s AND status IN ({placeholders})",
            (*params, suggestion_id, *from_statuses),
        )
        return cur.rowcount == 1


def approved_video_ids():
    with cursor() as cur:
        cur.execute("SELECT id, video_id FROM suggestions WHERE status = 'approved'")
        return cur.fetchall()


# --- tablica i statystyki ---

def played_today(limit=10):
    with cursor() as cur:
        cur.execute(
            f"SELECT {_PUBLIC_COLUMNS}, {_VOTES} FROM suggestions s "
            "WHERE s.status = 'played' AND s.played_at >= CURDATE() "
            "ORDER BY s.played_at DESC LIMIT %s",
            (limit,),
        )
        rows = cur.fetchall()
        cur.execute(
            "SELECT COUNT(*) AS c FROM suggestions WHERE status = 'played' AND played_at >= CURDATE()"
        )
        return cur.fetchone()["c"], rows


def status_counts():
    with cursor() as cur:
        cur.execute(
            "SELECT status, COUNT(*) AS c FROM suggestions "
            "WHERE status IN ('pending', 'approved') GROUP BY status"
        )
        counts = {"pending": 0, "approved": 0}
        counts.update({row["status"]: row["c"] for row in cur.fetchall()})
        return counts


def stats():
    with cursor() as cur:
        cur.execute(
            "SELECT "
            " SUM(status = 'played' AND played_at >= CURDATE()) AS played_today, "
            " SUM(status = 'played' AND played_at >= NOW() - INTERVAL 7 DAY) AS played_week, "
            " SUM(created_at >= NOW() - INTERVAL 7 DAY) AS submitted_week, "
            " SUM(status IN ('approved', 'played') AND decided_at >= NOW() - INTERVAL 30 DAY) AS accepted_month, "
            " SUM(status = 'rejected' AND decided_at >= NOW() - INTERVAL 30 DAY) AS rejected_month "
            "FROM suggestions"
        )
        totals = {k: int(v or 0) for k, v in cur.fetchone().items()}
        cur.execute(
            "SELECT COUNT(DISTINCT voter_id) AS c FROM votes WHERE created_at >= NOW() - INTERVAL 7 DAY"
        )
        totals["active_voters_week"] = cur.fetchone()["c"]
        cur.execute(
            "SELECT s.video_id, MAX(s.title) AS title, MAX(s.artist) AS artist, COUNT(*) AS votes "
            "FROM suggestions s JOIN votes v ON v.suggestion_id = s.id "
            "WHERE s.created_at >= NOW() - INTERVAL 30 DAY "
            "GROUP BY s.video_id ORDER BY votes DESC LIMIT 10"
        )
        top_songs = cur.fetchall()
        cur.execute(
            "SELECT artist, COUNT(*) AS suggestions FROM suggestions "
            "WHERE created_at >= NOW() - INTERVAL 30 DAY AND artist IS NOT NULL "
            "GROUP BY artist ORDER BY suggestions DESC LIMIT 10"
        )
        top_artists = cur.fetchall()
    decided = totals["accepted_month"] + totals["rejected_month"]
    totals["approval_rate"] = round(totals["accepted_month"] / decided, 2) if decided else None
    return {**totals, "top_songs": top_songs, "top_artists": top_artists}


# --- blocklista ---

def list_blocklist():
    with cursor() as cur:
        cur.execute(
            "SELECT id, kind, value, label, created_by, created_at FROM blocklist ORDER BY created_at DESC"
        )
        return cur.fetchall()


def add_block(kind, value, label, user):
    with cursor() as cur:
        cur.execute(
            "INSERT INTO blocklist (kind, value, label, created_by) VALUES (%s, %s, %s, %s) "
            "ON DUPLICATE KEY UPDATE label = VALUES(label)",
            (kind, value, label, user),
        )


def remove_block(block_id):
    with cursor() as cur:
        cur.execute("DELETE FROM blocklist WHERE id = %s", (block_id,))
        return cur.rowcount == 1
