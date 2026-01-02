# Qadam Club Bot 🤖

Professional Telegram Bot and Mini App system for habit tracking and challenges.

## Project Structure

- `backend/`: Flask 3.0 API with SQLAlchemy 2.x models and routes.
- `bot/`: Telegram Bot implementation using `python-telegram-bot` v21.
- `frontend/`: Boilerplates for Telegram Mini App and Admin Panel.
- `config.py`: Global configuration using environment variables.

## Ishga tushirish (Run)

### 0. Tayyorgarlik (.env sozlash)
Avval `.env.example` faylidan nusxa olib, `.env` faylini yarating:
```bash
cp .env.example .env
```
Keyin `.env` faylini ochib, ichiga o'zingizning ma'lumotlaringizni (BOT_TOKEN, ADMIN_IDS va h.k.) yozing.

### 1-variant: Docker orqali (Tavsiya qilinadi)
Agar kompyuteringizda Docker o'rnatilgan bo'lsa, loyihani birgina buyruq bilan ishga tushirishingiz mumkin:

```bash
docker-compose up --build
```
Bu buyruq Backend va Bot'ni bir vaqtda ishga tushiradi.

### 2-variant: Oddiy buyruqlar orqali

1. **Kutubxonalarni o'rnatish:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Backend'ni ishga tushirish:**
   ```bash
   python -m backend.app
   ```

3. **Bot'ni ishga tushirish:**
   ```bash
   python -m bot.bot
   ```

## Muhim
Ishga tushirishdan oldin `.env` faylini yarating va kerakli o'zgaruvchilarni (`BOT_TOKEN` va boshqalar) kiriting.

## Development

- **Database**: `backend/models.py`
- **Bot Handlers**: `bot/handlers.py`
- **UI**: `frontend/tma/index.html`

## License
MIT
