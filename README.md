# Radio Górka

System próśb muzycznych dla szkolnego radia. Uczniowie proponują utwory z YouTube Music i głosują na kolejkę, a DJ-e w panelu widzą prośby posortowane według głosów i sami decydują, co zagrać.

![Vue 3 + FastAPI](https://img.shields.io/badge/stack-Vue3%20%2B%20FastAPI-blue)
![License](https://img.shields.io/badge/license-MIT-green)

## Demo

**Strona główna:** [radiogorka.pl](https://radiogorka.pl)

**API docs:** [frog02-20689.wykr.es/docs](https://frog02-20689.wykr.es/docs)

## Jak to działa

1. **Uczeń** (telefon albo komputer w pokoju radia) wyszukuje utwór i klika **Zaproponuj**. Jeśli ktoś już go zaproponował, kliknięcie dodaje głos zamiast duplikatu.
2. Wszyscy widzą **Kolejkę** posortowaną według głosów i mogą głosować (jeden głos na utwór na przeglądarkę albo konto).
3. W zakładce **Moje prośby** uczeń widzi status: Czeka na DJ-a, Zatwierdzone, Zagrane albo Odrzucone (z powodem).
4. **DJ** w panelu ma **Inbox** posortowany według głosów: Zatwierdź (utwór trafia na playlistę YouTube, z której gra radio), Odrzuć (szybkie powody), a potem **Zagrane**.
5. **Ekran w pokoju** (`/ekran`) pokazuje kod QR do strony, top prośby, co dziś zagrano na prośbę i licznik dziennego celu.

DJ-e mają pełną kontrolę: nic nie trafia na playlistę bez ich zgody. Dzienny cel („Dziś zagrane prośby: 2 / 3”) jest widoczny dla wszystkich, więc łatwo zobaczyć, że prośby naprawdę lecą.

## Funkcje

- Wyszukiwanie utworów na YouTube Music
- Kolejka próśb z głosowaniem i blokadą duplikatów
- Statusy próśb widoczne dla ucznia (z powodem odrzucenia)
- Dzienne limity propozycji: bez konta, z kontem Górka i dla komputera w pokoju
- Blokada ponownej prośby o utwór grany w ostatnich dniach
- Panel DJ-a: Inbox, Do zagrania, Historia, Statystyki, Ustawienia
- Blocklista utworów i wykonawców, blokowanie spamerów
- Ekran kioskowy z kodem QR dla komputera w pokoju radia
- Opcjonalne logowanie uczniów przez Górka API
- Opcjonalne automatyczne oznaczanie zagranych na podstawie historii YouTube
- Responsywny neonowy interfejs

## Technologie

| Warstwa | Technologie |
|---------|-------------|
| Frontend | Vue 3, Vite, Tailwind CSS, qrcode |
| Backend | FastAPI, ytmusicapi |
| Baza danych | MySQL / MariaDB |
| Autoryzacja | JWT, bcrypt |

## Wymagania

- Node.js 18+
- Python 3.10+
- MySQL 5.7+ albo MariaDB 10.2+

---

## Backend

```
backend/
├── main.py            # Aplikacja FastAPI i wszystkie endpointy
├── store.py           # Zapytania do bazy: prośby, głosy, ustawienia, blocklista
├── db.py              # Połączenie z MySQL i tworzenie tabel przy starcie
├── schema.sql         # Schemat bazy (CREATE TABLE IF NOT EXISTS)
├── auth.py            # Logowanie adminów i tokeny JWT (admin i przeglądarka ucznia)
├── ytm.py             # Klient YouTube Music (ytmusicapi)
├── gorka.py           # Opcjonalne logowanie uczniów przez Górka API
├── create_admin.py    # Dodawanie konta administratora
├── tests/             # Testy pytest (wymagają testowej bazy)
├── browser.json       # Poświadczenia YouTube Music (nie w repo)
└── requirements.txt
```

**Tożsamość ucznia.** Przy pierwszej wizycie przeglądarka dostaje anonimowy token (`POST /api/session`), wysyłany potem w nagłówku `X-Voter-Token`. Jedna przeglądarka to jeden głos na utwór. Token ucznia nigdy nie działa jako token admina.

**Komputer w pokoju.** W panelu, w zakładce Ustawienia, oznacz przeglądarkę na komputerze w pokoju jako **stanowisko**. Dostaje wyższy limit, bo korzysta z niej wiele osób, a uczeń zalogowany tam przez Górkę jest automatycznie wylogowywany po 3 minutach bezczynności.

**Logowanie przez Górkę.** Wyłączone, dopóki nie ustawisz `gorka_api_url`. Konto daje wyższy dzienny limit i te same głosy na każdym urządzeniu. Adapter w `gorka.py` zakłada `POST {gorka_api_url}/login` z `username` i `password`. Sprawdź go z [dokumentacją Górka API](https://gorkaapi.pl/docs) i popraw `_request_login` / `_parse_user`, jeśli API wygląda inaczej.

### browser.json

Plik poświadczeń do logowania w YouTube Music API (ytmusicapi). Pozyskuje się go z DevTools przeglądarki (nagłówki zapytania do music.youtube.com).

---

## Frontend

```
frontend/src/
├── main.js              # Entry point aplikacji Vue
├── App.vue              # Tylko RouterView
├── router.js            # Trasy: /, /admin-panel, /ekran, 404
├── api.js               # Axios + sesja przeglądarki ucznia
├── format.js            # Formatowanie czasu, odmiana „głos/głosy/głosów”, odświeżanie
├── style.css            # Tailwind + neonowe efekty
├── components/          # SongRow, VoteButton, StatusChip, GoalMeter
└── page/
    ├── Home.vue         # Wyszukiwarka, kolejka, moje prośby, zagrane dziś
    ├── AdminPanel.vue   # Logowanie i panel DJ-a
    ├── admin/           # Zakładki panelu: Inbox, Do zagrania, Historia, Statystyki, Ustawienia
    ├── Screen.vue       # Ekran kioskowy dla pokoju radia
    ├── 404.vue
    └── GitHubButton.vue
```

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

# Wymagane: długi losowy sekret do podpisywania JWT (aplikacja nie wystartuje bez niego)
jwt_secret=zmien_na_dlugi_losowy_ciag
# Opcjonalne:
jwt_ttl_hours=12
voter_token_ttl_days=180
# Lista dozwolonych originów CORS (oddzielone przecinkami)
allowed_origins=http://localhost:5173,https://radiogorka.pl
# Playlista YouTube, na którą trafiają zatwierdzone prośby
playlist_id=PLJhSTAItRjxJl8f9mcHenCKVotPkSDFVB
# Adres strony pokazywany jako kod QR na /ekran
site_url=https://radiogorka.pl
# Limity zapytań na minutę: na przeglądarkę, na IP (cała szkoła ma zwykle jedno IP), nowe sesje na IP
rate_limit=30
rate_limit_ip=300
session_rate_limit=120
# Co ile sekund sprawdzać historię YouTube (gdy włączone w panelu)
history_sync_interval=60
# Logowanie uczniów przez Górka API (puste = wyłączone)
gorka_api_url=
gorka_api_key=
gorka_login_path=/login
```

Tabele tworzą się same przy starcie. Pierwsze konto administratora:
```bash
python create_admin.py dj
```

Uruchomienie:
```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

**Przejście ze starej wersji:** wcześniej propozycje trafiały od razu na playlistę YouTube. Teraz playlista zawiera tylko zatwierdzone utwory, a prośby są w bazie. Po aktualizacji możesz wyczyścić playlistę w Ustawienia, Strefa niebezpieczna.

### Testy

Testy potrzebują pustej bazy MySQL/MariaDB (YouTube jest zastąpione atrapą):
```bash
pip install pytest
TEST_DB_NAME=radio_gorka_test TEST_DB_USER=user TEST_DB_PASSWORD=haslo pytest tests
```
Bez `TEST_DB_NAME` testy są pomijane.

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

`.env` (opcjonalne):
```env
VITE_API_URL=https://frog02-20689.wykr.es/api
```

### Ekran w pokoju radia

Na komputerze albo telewizorze w pokoju otwórz `https://radiogorka.pl/ekran` i włącz pełny ekran (F11). Strona odświeża się sama co 10 sekund. Na tym samym komputerze zaloguj się raz do panelu i oznacz przeglądarkę jako stanowisko.

---

## API

Endpointy `/api/admin/*` i `/api/clear-playlist` wymagają nagłówka `Authorization: Bearer {jwt}`.
Endpointy ucznia wymagają nagłówka `X-Voter-Token: {token z /api/session}`.

| Metoda | Endpoint | Opis |
|--------|----------|------|
| POST | `/api/session` | Nowa anonimowa sesja przeglądarki |
| GET | `/api/me` | Moje prośby, pozostały limit, konto |
| GET | `/api/search?query={fraza}` | Wyszukaj utwory (ze stanem: nowy, w kolejce, grany niedawno...) |
| POST | `/api/suggestions` | Zaproponuj utwór `{videoId}` (albo zagłosuj, jeśli już jest w kolejce) |
| POST / DELETE | `/api/suggestions/{id}/vote` | Zagłosuj / cofnij głos |
| GET | `/api/queue` | Kolejka posortowana według głosów |
| GET | `/api/board` | Dane dla ekranu w pokoju |
| POST | `/api/gorka/login` | Logowanie przez Górka API |
| POST | `/api/login` | Logowanie admina |
| GET | `/api/admin/summary` | Liczniki i cel dnia |
| GET | `/api/admin/suggestions?status=` | Prośby: pending, approved, played, rejected |
| POST | `/api/admin/suggestions/{id}/approve` | Zatwierdź (dodaje do playlisty YouTube) |
| POST | `/api/admin/suggestions/{id}/reject` | Odrzuć `{reason, block}` |
| POST | `/api/admin/suggestions/{id}/played` | Oznacz jako zagrane |
| POST | `/api/admin/suggestions/{id}/requeue` | Przywróć do kolejki |
| POST | `/api/admin/suggestions/{id}/ban-submitter` | Zablokuj autora |
| GET / PUT | `/api/admin/settings` | Ustawienia (limity, cel dnia, prośby otwarte...) |
| GET / POST / DELETE | `/api/admin/blocklist` | Blocklista utworów i wykonawców |
| POST | `/api/admin/station` | Oznacz przeglądarkę jako stanowisko w pokoju |
| GET | `/api/admin/stats` | Statystyki |
| POST | `/api/admin/sync-history` | Oznacz zagrane na podstawie historii YouTube |
| DELETE | `/api/clear-playlist` | Wyczyść playlistę YouTube |

Dokumentacja interaktywna: **https://frog02-20689.wykr.es/docs**

---

## Przyszłe rozbudowy

- Osobna playlista eventowa (dyskoteki)
- Powiadomienia (Discord/Telegram bot)

---

MIT License, Radio Górka 2026
