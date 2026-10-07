"""Opcjonalne logowanie uczniów przez szkolne Górka API (https://gorkaapi.pl/docs).

Wyłączone, dopóki nie ustawisz gorka_api_url w .env.

UWAGA: kształt zapytania i odpowiedzi poniżej to założenie (POST login + hasło,
w odpowiedzi dane użytkownika). Sprawdź z dokumentacją Górka API i popraw
_request_login / _parse_user, jeśli API wygląda inaczej. Reszta aplikacji
korzysta tylko z verify() i enabled().
"""
import os
from dataclasses import dataclass

import httpx
from dotenv import load_dotenv

load_dotenv()

GORKA_API_URL = os.getenv("gorka_api_url", "").rstrip("/")
GORKA_API_KEY = os.getenv("gorka_api_key", "")
GORKA_LOGIN_PATH = os.getenv("gorka_login_path", "/login")
TIMEOUT_S = 10


@dataclass
class GorkaUser:
    id: str
    name: str
    school_class: str | None = None


class GorkaUnavailable(Exception):
    pass


def enabled():
    return bool(GORKA_API_URL)


def _request_login(username, password):
    headers = {"Authorization": f"Bearer {GORKA_API_KEY}"} if GORKA_API_KEY else {}
    return httpx.post(
        f"{GORKA_API_URL}{GORKA_LOGIN_PATH}",
        json={"username": username, "password": password},
        headers=headers,
        timeout=TIMEOUT_S,
    )


def _parse_user(data, username):
    user = data.get("user") if isinstance(data.get("user"), dict) else data
    user_id = user.get("id") or user.get("user_id") or user.get("login") or username
    name = (
        user.get("name")
        or " ".join(p for p in (user.get("first_name"), user.get("last_name")) if p)
        or username
    )
    school_class = user.get("class") or user.get("school_class") or user.get("klasa")
    return GorkaUser(id=str(user_id), name=str(name)[:80], school_class=school_class)


def verify(username, password):
    """Zwraca GorkaUser przy poprawnym loginie, None przy złym. Rzuca GorkaUnavailable, gdy API nie działa."""
    if not enabled():
        raise GorkaUnavailable("Logowanie przez Górkę jest wyłączone")
    try:
        response = _request_login(username, password)
    except httpx.HTTPError as e:
        raise GorkaUnavailable("Górka API nie odpowiada") from e
    if response.status_code in (400, 401, 403):
        return None
    if response.status_code >= 300:
        raise GorkaUnavailable(f"Górka API zwróciło {response.status_code}")
    try:
        return _parse_user(response.json(), username)
    except ValueError as e:
        raise GorkaUnavailable("Nieczytelna odpowiedź Górka API") from e
