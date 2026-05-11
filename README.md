# Qadam Club Bot

A Telegram bot and Mini App (TMA) ecosystem for daily habit tracking. Users submit results through a Telegram Mini App, track streaks, and compete on a leaderboard.

## Features

- **Telegram Mini App (TMA)** — clean UI for submitting daily results
- **Streak system** — Duolingo-style consecutive day tracking
- **Time-gated submissions** — accepts results only within a configured window (e.g., 21:00–23:59)
- **Admin panel** — manage challenges and view user statistics
- **Automation** — daily reminders and weekly winner detection via APScheduler
- **Docker support** — single-command deployment

## Tech Stack

- **Backend**: Flask 3.0, SQLAlchemy 2.x
- **Bot**: python-telegram-bot v21
- **Frontend**: HTML/CSS/JS (Telegram Mini App + Admin Panel)
- **Scheduler**: APScheduler
- **Container**: Docker + docker-compose

## Setup

### 1. Clone

```bash
git clone https://github.com/samandar-hamrayev/Qadam-Club-Bot.git
cd Qadam-Club-Bot
```

### 2. Configure environment

```bash
cp .env.example .env
```

Key variables:

| Variable | Description |
|----------|-------------|
| `BOT_TOKEN` | Bot token from @BotFather |
| `ADMIN_IDS` | Your Telegram ID (grants admin access) |
| `API_URL` | `http://backend:5000/api` (Docker) or `http://localhost:5000/api` (local) |
| `PYTHONANYWHERE_DOMAIN` | Your ngrok or production domain |

### 3. Run

**Docker (recommended):**

```bash
docker compose up --build
```

> On macOS, port 5000 may be occupied by AirPlay — the app runs on port **5001** instead.

**Local:**

```bash
pip install -r requirements.txt
python -m backend.app      # start Flask backend
python -m bot.bot          # start bot (new terminal)
```

## Local Testing with ngrok

The Telegram Mini App requires an HTTPS URL. Expose your local server:

1. Run `ngrok http 5001`
2. Copy the `https://...` URL into `PYTHONANYWHERE_DOMAIN` in `.env`
3. Mini App: `https://your-domain.ngrok-free.app/tma`
4. Admin panel: `https://your-domain.ngrok-free.app/admin-panel`

## Bot Commands

| Command | Description |
|---------|-------------|
| `/start` | Register and open the Mini App |
| `/submit` | Submit results manually without TMA |

## Project Structure

```
Qadam-Club-Bot/
├── backend/     # Flask API + SQLAlchemy models
├── bot/         # Telegram bot handlers
├── frontend/    # TMA and Admin Panel (HTML/CSS/JS)
└── config.py    # Global configuration
```

## License

MIT
