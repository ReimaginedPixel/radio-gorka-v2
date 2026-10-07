"""Dodaje konto administratora (albo zmienia mu hasło).

Użycie: python create_admin.py <login>
"""
import getpass
import sys

import bcrypt

import db


def main():
    username = sys.argv[1] if len(sys.argv) > 1 else input("Login: ").strip()
    password = getpass.getpass("Hasło: ")
    if not username or not password:
        sys.exit("Login i hasło nie mogą być puste")
    db.init_db()
    hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    with db.cursor() as cur:
        cur.execute(
            "INSERT INTO users (username, password) VALUES (%s, %s) "
            "ON DUPLICATE KEY UPDATE password = VALUES(password)",
            (username, hashed),
        )
    print(f"Zapisano administratora: {username}")


if __name__ == "__main__":
    main()
