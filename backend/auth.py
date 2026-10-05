import pymysql
import jwt
import bcrypt
import os
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv

load_dotenv()

JWT_SECRET = os.getenv("jwt_secret")
if not JWT_SECRET:
    raise RuntimeError(
        "Missing 'jwt_secret' environment variable. Set a long random value in backend/.env"
    )

JWT_ALGORITHM = "HS256"
TOKEN_TTL_HOURS = int(os.getenv("jwt_ttl_hours", 12))


def get_connection():
    return pymysql.connect(
        host=os.getenv("domain"),
        user=os.getenv("username"),
        password=os.getenv("password"),
        database=os.getenv("database"),
        port=int(os.getenv("port", 3306))
    )


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
