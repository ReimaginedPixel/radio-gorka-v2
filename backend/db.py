import os
from contextlib import contextmanager

import pymysql
import pymysql.cursors
from dotenv import load_dotenv

load_dotenv()

SCHEMA_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "schema.sql")


def get_connection():
    return pymysql.connect(
        host=os.getenv("domain"),
        user=os.getenv("username"),
        password=os.getenv("password"),
        database=os.getenv("database"),
        port=int(os.getenv("port", 3306)),
        charset="utf8mb4",
    )


@contextmanager
def cursor():
    """Dict cursor inside one transaction: commit on success, rollback on error."""
    conn = get_connection()
    try:
        with conn.cursor(pymysql.cursors.DictCursor) as cur:
            yield cur
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _schema_statements():
    with open(SCHEMA_PATH, encoding="utf-8") as f:
        lines = [line for line in f if not line.strip().startswith("--")]
    return [s.strip() for s in "".join(lines).split(";") if s.strip()]


def init_db():
    with cursor() as cur:
        for statement in _schema_statements():
            cur.execute(statement)
