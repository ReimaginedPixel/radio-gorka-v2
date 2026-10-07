import jwt
import bcrypt
import os
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv

from db import get_connection

load_dotenv()

JWT_SECRET = os.getenv("jwt_secret")
if not JWT_SECRET:
    raise RuntimeError(
        "Missing 'jwt_secret' environment variable. Set a long random value in backend/.env"
    )

JWT_ALGORITHM = "HS256"
TOKEN_TTL_HOURS = int(os.getenv("jwt_ttl_hours", 12))
VOTER_TOKEN_TTL_DAYS = int(os.getenv("voter_token_ttl_days", 180))


def login(username, password):
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT password FROM users WHERE username = %s", (username,))
        user = cursor.fetchone()
        if user is None:
            return False
        hashed = user[0].encode("utf-8") if isinstance(user[0], str) else user[0]
        if bcrypt.checkpw(password.encode("utf-8"), hashed):
            return jwt.encode(
                {
                    "sub": username,
                    "typ": "admin",
                    "exp": datetime.now(timezone.utc) + timedelta(hours=TOKEN_TTL_HOURS),
                },
                JWT_SECRET,
                algorithm=JWT_ALGORITHM,
            )
        return False
    finally:
        conn.close()


def auth(token):
    try:
        data = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except Exception:
        return None

    # Tokeny głosujących są podpisane tym samym sekretem, więc nigdy nie mogą przejść jako admin.
    if data.get("typ") == "voter":
        return None

    username = data.get("sub")
    if not username:
        return None

    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM users WHERE username = %s", (username,))
        if cursor.fetchone() is None:
            return None
        return username
    finally:
        conn.close()


def create_voter_token(voter_id):
    return jwt.encode(
        {
            "sub": voter_id,
            "typ": "voter",
            "exp": datetime.now(timezone.utc) + timedelta(days=VOTER_TOKEN_TTL_DAYS),
        },
        JWT_SECRET,
        algorithm=JWT_ALGORITHM,
    )


def decode_voter_token(token):
    try:
        data = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except Exception:
        return None
    if data.get("typ") != "voter":
        return None
    return data.get("sub")
