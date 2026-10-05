# Radio Górka

System do zgłaszania utworów na imprezy. Użytkownicy wyszukują piosenki na YouTube Music i zgłaszają je do kolejki. DJ w panelu administratora akceptuje albo odrzuca zgłoszenia i odtwarza kolejkę prosto w przeglądarce (odtwarzacz YouTube), a strona główna na żywo pokazuje, co teraz gra.

![Vue 3 + FastAPI](https://img.shields.io/badge/stack-Vue3%20%2B%20FastAPI-blue)
![License](https://img.shields.io/badge/license-MIT-green)

## Demo

**Strona główna:** [radiogorka.pl](https://radiogorka.pl)

**API docs:** [frog02-20689.wykr.es/docs](https://frog02-20689.wykr.es/docs)

## Funkcje

- Wyszukiwanie utworów na YouTube Music, wyniki jako wachlarz okładek
- Zgłoszenie jednym stuknięciem w okładkę (okładka "przelatuje" do kolejki)
- Podgląd własnych zgłoszeń: czeka na DJ-a, w kolejce, odrzucone, możliwość wycofania
- Na żywo: co teraz gra, postęp utworu, kolejka i liczba zgłoszeń czekających na DJ-a
- Panel administratora:
  - akceptowanie i odrzucanie zgłoszeń (przyciski, zaznaczanie wielu naraz, gest przesunięcia w prawo / w lewo)
  - odtwarzacz YouTube: play, pauza, stop, następny, od początku, przewijanie, głośność, wyciszenie
  - automatyczne przejście do następnego utworu, pomijanie filmów, których nie da się odtworzyć
  - kolejka: zagraj teraz, zagraj jako następny, usuń, wyczyść wszystko
  - mini odtwarzacz przy przewijaniu, skróty klawiszowe (spacja: play/pauza, N: następny)
- Ciemny i jasny motyw, układ od telefonu po desktop, animacje z poszanowaniem `prefers-reduced-motion`
- Logowanie przez JWT

## Technologie

| Warstwa | Technologie |
|---------|-------------|
| Frontend | Vue 3, Vite, YouTube IFrame Player API |
| Backend | FastAPI, ytmusicapi |
| Baza danych | MySQL / MariaDB |
| Autoryzacja | JWT, bcrypt |

## Wymagania

- Node.js 18+
- Python 3.10+
- MySQL lub MariaDB

---

## Jak to działa

1. Użytkownik wyszukuje utwór i stuka okładkę. Zgłoszenie trafia do bazy ze statusem `pending`.
2. DJ widzi je w panelu i akceptuje (`accepted`, trafia na koniec kolejki) albo odrzuca (`rejected`).
3. Panel odtwarza kolejkę po kolei. Zagrany albo pominięty utwór dostaje status `played` i znika z kolejki.
4. Panel co kilka sekund wysyła stan odtwarzacza do serwera, a strona główna pokazuje go jako "teraz gra". Gdy panel zostanie zamknięty, po około 25 sekundach radio jest pokazywane jako wyłączone.

Zaakceptowane utwory są dodatkowo dopisywane do playlisty YouTube Music (jeśli jest `browser.json`), a zagrane i usunięte są z niej zdejmowane. Dzięki temu playlistę nadal można puścić z aplikacji YouTube Music.

---

## Backend

```
backend/
├── main.py          # Aplikacja FastAPI i wszystkie endpointy
├── db.py            # Połączenie z bazą i tabela zgłoszeń
├── auth.py          # Logowanie i weryfikacja tokenów JWT
├── browser.json     # Poświadczenia YouTube Music (niecommitowane)
└── requirements.txt # Zależności Python
```

### main.py

Endpointy publiczne, panel administratora, stan odtwarzacza i synchronizacja z playlistą YouTube Music. Tabela `submissions` tworzy się sama przy starcie serwera.

### db.py

Połączenie z MySQL (PyMySQL) i schemat tabeli `submissions`. Statusy zgłoszeń: `pending`, `accepted`, `rejected`, `played`, `removed`, `cancelled`.

### auth.py

- `login(username, password)`: sprawdza użytkownika w tabeli `users` (hasła bcrypt) i zwraca token JWT ważny 24 godziny (zmienisz to przez `TOKEN_TTL_HOURS`)
- `auth(token)`: sprawdza podpis i ważność tokena, zwraca nazwę użytkownika

Token zawiera tylko nazwę użytkownika i datę wygaśnięcia (bez hasła). Jest podpisany sekretem z `JWT_SECRET`.

### browser.json

Poświadczenia do ytmusicapi, pozyskiwane z DevTools przeglądarki. Bez tego pliku wyszukiwanie dalej działa, ale playlista YouTube Music nie jest aktualizowana.

---

## Frontend

```
frontend/src/
├── main.js / App.vue / router.js
├── style.css              # Tokeny kolorów, typografia, wspólne elementy, animacje
├── assets/                # Logo, rendery (mikrofon, głośnik, słuchawki), font Simpleton
├── lib/                   # api.js (klient API), format.js, motion.js (animacja lotu okładki), session.js
├── composables/           # odtwarzacz YouTube, moje zgłoszenia, motyw, toasty, odpytywanie serwera
├── components/            # nagłówek, "teraz gra", wachlarz okładek, deck odtwarzacza, wiersze zgłoszeń itd.
└── page/
    ├── Home.vue           # Wyszukiwanie, teraz gra, kolejka
    ├── AdminPanel.vue     # Logowanie i panel DJ-a
    └── 404.vue            # Cisza w eterze
```

Trasy: `/` (strona główna), `/admin-panel` (panel), wszystko inne to 404.

Font wyświetlaczy to Simpleton (Brian Kent, freeware), licencja w `src/assets/fonts/simpleton.txt`. Font interfejsu to Schibsted Grotesk z Google Fonts.

---

## Konfiguracja

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Linux/Mac
# lub: venv\Scripts\Activate  # Windows
pip install -r requirements.txt
```

Plik `.env` w `backend/`:
```env
domain=localhost
username=twoj_user
password=twoje_haslo
database=radio_gorka
port=3306

# Długi losowy ciąg, np. wynik: python -c "import secrets; print(secrets.token_hex(32))"
JWT_SECRET=zmien_mnie
# Opcjonalnie
PLAYLIST_ID=PLJhSTAItRjxJl8f9mcHenCKVotPkSDFVB
TOKEN_TTL_HOURS=24
```

Bez `JWT_SECRET` serwer wygeneruje tymczasowy sekret i po każdym restarcie trzeba się logować od nowa.

Tabela użytkowników (jeśli jeszcze jej nie ma):
```sql
CREATE TABLE users (
  id INT AUTO_INCREMENT PRIMARY KEY,
  username VARCHAR(64) UNIQUE NOT NULL,
  password VARCHAR(255) NOT NULL  -- hash bcrypt
);
```

Uruchomienie (jeden worker, bo stan odtwarzacza trzymany jest w pamięci):
```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Build produkcyjny:
```bash
npm run build
```

### .env (opcjonalne)

```env
VITE_API_URL=https://frog02-20689.wykr.es/api
```

Lokalnie: `VITE_API_URL=http://localhost:8000/api`.

---

## API

Publiczne:

| Metoda | Endpoint | Opis |
|--------|----------|------|
| GET | `/api/search?query={fraza}` | Wyszukaj utwory (piosenki i teledyski) |
| POST | `/api/requests` | Zgłoś utwór `{ "videoId": "..." }`, zwraca `id` i `ticket` |
| POST | `/api/requests/lookup` | Statusy własnych zgłoszeń `{ "items": [{ "id", "ticket" }] }` |
| DELETE | `/api/requests/{id}?ticket=...` | Wycofaj własne zgłoszenie (tylko `pending`) |
| GET | `/api/live` | Teraz gra, kolejka, liczba zgłoszeń czekających |
| POST | `/api/login` | Zaloguj, zwraca token |
| GET | `/api/health` | Stan serwera |

Panel administratora (nagłówek `Authorization: Bearer <token>`):

| Metoda | Endpoint | Opis |
|--------|----------|------|
| GET | `/api/admin/me` | Sprawdź sesję |
| GET | `/api/admin/submissions?status=pending` | Lista zgłoszeń o danym statusie |
| POST | `/api/admin/submissions/accept` | Akceptuj `{ "ids": [...] }` |
| POST | `/api/admin/submissions/reject` | Odrzuć `{ "ids": [...] }` |
| GET | `/api/admin/queue` | Kolejka do odtworzenia |
| POST | `/api/admin/queue/order` | Ustaw kolejność `{ "ids": [...] }` |
| POST | `/api/admin/queue/{id}/played` | Oznacz jako zagrane |
| DELETE | `/api/admin/queue/{id}` | Usuń z kolejki |
| DELETE | `/api/admin/queue` | Wyczyść kolejkę (i playlistę YT) |
| POST | `/api/admin/player` | Stan odtwarzacza `{ "state", "submissionId", "position", "duration" }` |

Dokumentacja interaktywna: **https://frog02-20689.wykr.es/docs**

---

## Przyszłe rozbudowy

- Osobna playlista eventowa (dyskoteki)
- Historia odtworzeń w panelu (dane już są w bazie, status `played`)
- Statystyki (top utwory, top użytkownicy)
- Powiadomienia (Discord/Telegram bot)

---

MIT License, Radio Górka 2026
