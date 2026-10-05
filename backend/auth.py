import logging
import os
import secrets
import time

import bcrypt
import jwt
from dotenv import load_dotenv

import db

load_dotenv()

log = logging.getLogger("radio-gorka")

JWT_SECRET = os.getenv("JWT_SECRET")
if not JWT_SECRET:
    # Bez stałego sekretu tokeny tracą ważność po restarcie serwera.
    JWT_SECRET = secrets.token_hex(32)
    log.warning("Brak JWT_SECRET w .env, wygenerowano tymczasowy sekret")

TOKEN_TTL_SECONDS = int(os.getenv("TOKEN_TTL_HOURS", 24)) * 3600


def login(username, password):
    user = db.query_one("SELECT password FROM users WHERE username = %s", (username,))
    if user is None:
        return False
    hashed = user["password"]
    hashed = hashed.encode("utf-8") if isinstance(hashed, str) else hashed
    if not bcrypt.checkpw(password.encode("utf-8"), hashed):
        return False
    now = int(time.time())
    return jwt.encode(
        {"sub": username, "iat": now, "exp": now + TOKEN_TTL_SECONDS},
        JWT_SECRET,
        algorithm="HS256",
    )


def auth(key):
    """Zwraca nazwę użytkownika dla poprawnego tokena, w przeciwnym razie False."""
    try:
        data = jwt.decode(key, JWT_SECRET, algorithms=["HS256"])
    except Exception:
        return False
    username = data.get("sub")
    if not username:
        return False
    user = db.query_one("SELECT username FROM users WHERE username = %s", (username,))
    return username if user else False
