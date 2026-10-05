# Radio Górka

System do zgłaszania utworów do playlisty YouTube Music. Użytkownicy wyszukują piosenki na YouTube i dodają je do wspólnej playlisty, którą odtwarza Radio Górka podczas imprez.

![Vue 3 + FastAPI](https://img.shields.io/badge/stack-Vue3%20%2B%20FastAPI-blue)
![License](https://img.shields.io/badge/license-MIT-green)

## Demo

**Strona główna:** [radiogorka.pl](https://radiogorka.pl)


**API docs:** [frog02-20689.wykr.es/docs](https://frog02-20689.wykr.es/docs)

## Funkcje

- Wyszukiwanie utworów na YouTube Music
- Dodawanie zgłoszeń do playlisty
- Panel administratora (zarządzanie zgłoszeniami)
- Logowanie przez JWT
- Responsywny neonowy interfejs

## Technologie

| Warstwa | Technologie |
|---------|-------------|
| Frontend | Vue 3, Vite, Tailwind CSS |
| Backend | FastAPI, ytmusicapi |
| Baza danych | MySQL |
| Autoryzacja | JWT, bcrypt |

## Wymagania

- Node.js 18+
- Python 3.10+
- MySQL

---

## Backend

```
backend/
├── main.py          # Główna aplikacja FastAPI + endpoints
├── auth.py          # Logowanie i autoryzacja JWT
├── browser.json     # Poświadczenia YouTube Music
└── requirements.txt # Zależności Python
```

### main.py

Główny serwer FastAPI. Zawiera wszystkie endpointy API:
- `/api/search` – wyszukiwanie utworów na YouTube Music
- `/api/add` – dodawanie utworu do playlisty
- `/api/list` – pobieranie listy utworów
- `/api/delete` – usuwanie utworu z playlisty
- `/api/clear-playlist` – czyszczenie całej playlisty
- `/api/login` – logowanie użytkownika

### auth.py

Moduł logowania i autoryzacji:
- `login(username, password)` – weryfikuje użytkownika w bazie MySQL i generuje token JWT
- `auth(key)` – sprawdza ważność tokena JWT

Hasła są hashowane przez bcrypt, tokeny generowane algorytmem HS256.

### browser.json

Pliki poświadczeń do logowania w YouTube Music API (ytmusicapi).
Pozyskuje się z DevTools przeglądarki (nagłówek Authorization lub X-YouTube-Malformed-Data).

### requirements.txt

Zależności Python:
- fastapi, uvicorn – serwer
- ytmusicapi – integracja z YouTube Music
- pymysql – połączenie MySQL
- pydantic – walidacja danych
- python-dotenv – zmienne środowiskowe
- pyjwt, bcrypt – autoryzacja

---

## Frontend

```
frontend/
├── src/
│   ├── main.js        # Entry point aplikacji Vue
│   ├── App.vue        # Główny komponent (tylko RouterView)
│   ├── router.js      # Konfiguracja routingu Vue
│   ├── style.css     # Style Tailwind + neonowe efekty
│   └── page/
│       ├── Home.vue         # Strona główna – wyszukiwanie i dodawanie utworów
│       ├── AdminPanel.vue # Panel admina – zarządzanie zgłoszeniami
│       ├── 404.vue        # Strona błędu 404
│       └── GitHubButton.vue # Przycisk linkujący do repo GitHub
├── package.json
└── .env
```

### main.js

Entry point aplikacji Vue 3. Inicjuje aplikację, ładuje router i montuje w DOM.

### App.vue

Główny komponent – zawiera tylko `<RouterView />` do renderowania podstron.

### router.js

Konfiguracja Vue Router. Definiuje trasy:
- `/` – Home
- `/admin-panel` – AdminPanel
- `/:pathMatch(.*)*` – 404

### style.css

Style Tailwind CSS z dodatkami:
- Fonty: Orbitron (nagłówki), VT323 (tekst)
- Kolory: neonowy zielony (#39FF14), neonowy różowy (#FF1493), ciemne tło (#0d0d2b)
- Efekty: neon-text, neon-box, retro-input, retro-button, retro-button-green
- Animacje: neon-pulse, neon-flicker

### Home.vue

Strona główna:
- Pole wyszukiwania utworów
- Lista wyników z YouTube Music
- Przycisk dodawania do playlisty
- Powiadomienia o sukcesie/błędzie
- Link do trybu eventowego (jeśli włączony w .env)

### AdminPanel.vue

Panel administratora:
- Formularz logowania
- Lista zgłoszeń z opcją usuwania
- Masowe zaznaczanie i usuwanie
- Czyszczenie całej playlisty (z modalem potwierdzenia)
- Zapamiętanie logowania w localStorage

### 404.vue

Strona błędu 404 – wyświetlana dla nieistniejących tras.

### GitHubButton.vue

Komponent z przyciskiem linkującym do repozytorium GitHub.

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

Pliki `.env` w `backend/`:
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
# Lista dozwolonych originów CORS (oddzielone przecinkami)
allowed_origins=http://localhost:5173,https://radiogorka.pl
# ID playlisty YouTube oraz limit żądań na minutę na IP
playlist_id=PLJhSTAItRjxJl8f9mcHenCKVotPkSDFVB
rate_limit=30
```

Uruchomienie:
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

---

## API

Endpointy administracyjne wymagają nagłówka `Authorization: Bearer {jwt}`.

| Metoda | Endpoint | Opis |
|--------|----------|------|
| GET | `/api/search?query={fraza}` | Wyszukaj utwory |
| GET | `/api/add?videoID={id}` | Dodaj do playlisty |
| GET | `/api/list` | Pobierz playlistę (wymaga tokenu) |
| DELETE | `/api/delete?videoID={id}` | Usuń utwór (wymaga tokenu) |
| DELETE | `/api/clear-playlist` | Wyczyść playlistę (wymaga tokenu) |
| POST | `/api/login` | Zaloguj |

Dokumentacja interaktywna: **https://frog02-20689.wykr.es/docs**

---

## Przyszłe rozbudowy

- Osobna playlista eventowa (dyskoteki)
- Historia odtworzeń
- Moderacja zgłoszeń
- Statystyki (top utwory, top użytkownicy)
- Powiadomienia (Discord/Telegram bot)

---

MIT License – Radio Górka 2026
