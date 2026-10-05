import os

import pymysql
import pymysql.cursors
from dotenv import load_dotenv

load_dotenv()


def get_connection():
    return pymysql.connect(
        host=os.getenv("domain"),
        user=os.getenv("username"),
        password=os.getenv("password"),
        database=os.getenv("database"),
        port=int(os.getenv("port", 3306)),
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=True,
    )


def query(sql, params=None):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(sql, params)
            return cursor.fetchall()
    finally:
        conn.close()


def query_one(sql, params=None):
    rows = query(sql, params)
    return rows[0] if rows else None


def execute(sql, params=None):
    """Runs a write and returns (rowcount, lastrowid)."""
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(sql, params)
            return cursor.rowcount, cursor.lastrowid
    finally:
        conn.close()


def transaction(fn):
    """Runs fn(cursor) inside one transaction and returns its result."""
    conn = get_connection()
    try:
        conn.begin()
        with conn.cursor() as cursor:
            result = fn(cursor)
        conn.commit()
        return result
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# Statusy zgłoszeń:
#   pending   : czeka na decyzję admina
#   accepted  : w kolejce do odtworzenia
#   rejected  : odrzucone przez admina
#   played    : zagrane (albo pominięte) w panelu admina
#   removed   : usunięte z kolejki przez admina
#   cancelled : wycofane przez osobę, która je zgłosiła
SCHEMA = """
CREATE TABLE IF NOT EXISTS submissions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    video_id VARCHAR(32) NOT NULL,
    title VARCHAR(255) NOT NULL,
    artist VARCHAR(255) NOT NULL DEFAULT '',
    thumbnail VARCHAR(1024) NOT NULL DEFAULT '',
    duration_seconds INT NULL,
    status VARCHAR(16) NOT NULL DEFAULT 'pending',
    position DOUBLE NULL,
    ticket CHAR(32) NOT NULL,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL,
    KEY idx_status (status),
    KEY idx_video (video_id)
) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci
"""


def init_db():
    execute(SCHEMA)
