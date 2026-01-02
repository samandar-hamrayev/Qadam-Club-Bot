# Qadam Club Bot 🤖

Professional darajadagi Telegram Bot va Mini App (TMA) ekotizimi. Ushbu platforma foydalanuvchilarning kundalik odatlarini (habit tracking) shakllantirish, streaklarni hisoblash va sog'lom raqobat muhitini yaratishga mo'ljallangan.

## 🚀 Imkoniyatlar

- **Telegram Mini App (TMA):** Chiroyli va qulay interfeys orqali natijalarni topshirish.
- **Admin Panel:** Challenge'larni boshqarish, foydalanuvchilar statistikasini ko'rish.
- **Streak Tizimi:** Kunlik uzluksiz natijalar uchun "streak"lar (Duolingo uslubida).
- **Vaqtli Cheklovlar:** Muayyan vaqt oraliqlarida (masalan, 21:00-23:59) natija qabul qilish.
- **Avtomatlashtirish:** Kunlik eslatmalar va haftalik g'oliblarni aniqlash (APScheduler).
- **Docker Support:** Tezkor va xatosiz ishga tushirish.

## 📁 Loyiha Strukturasi

- `backend/`: Flask 3.0 API, SQLAlchemy 2.x modellari va route'lar.
- `bot/`: `python-telegram-bot` v21 orqali yozilgan bot logikasi.
- `frontend/`: TMA va Admin Panel uchun HTML/CSS/JS boilerplatelar.
- `config.py`: Global sozlamalar va o'zgaruvchilar.

## 🛠 O'rnatish va Ishga tushirish

### 1. Loyihani yuklab olish
```bash
git clone https://github.com/samandar-hamrayev/Qadam-Club-Bot.git
cd Qadam-Club-Bot
```

### 2. Muhitni sozlash (.env)
`.env.example` faylidan nusxa oling va o'zingizning ma'lumotlaringizni kiriting:
```bash
cp .env.example .env
```
`.env` fayli ichidagi muhim o'zgaruvchilar:
- `BOT_TOKEN`: @BotFather dan olingan token.
- `ADMIN_IDS`: Sizning Telegram ID'ingiz (admin bo'lish uchun).
- `API_URL`: Docker uchun `http://backend:5000/api`, oddiy ishga tushirish uchun `http://localhost:5000/api`.
- `PYTHONANYWHERE_DOMAIN`: Ngrok yoki production domeningiz (oxiriga `/tma` qo'shiladi).

### 3. Ishga tushirish (Variantlar)

#### A-variant: Docker orqali (Tavsiya qilinadi)
Kompyuteringizda Docker bo'lsa, bitta buyruq bilan hamma narsani ishga tushiring:
```bash
docker compose up --build
```
*Eslatma: macOS'da 5000-port band bo'lishi mumkinligi sababli, loyiha **5001** portda ishlaydi.*

#### B-variant: Oddiy buyruqlar orqali
1. Kutubxonalarni o'rnatish: `pip install -r requirements.txt`
2. Backendni boshlash: `python -m backend.app`
3. Botni boshlash (yangi terminalda): `python -m bot.bot`

## 🌐 Lokal Test qilish (ngrok)

TMA haqiqiy Telegram ichida ishlashi uchun lokal loyihangizni tashqi dunyoga ochishingiz kerak:
1. Terminalda: `ngrok http 5001`
2. Berilgan `https://...` manzilini `.env` faylidagi `PYTHONANYWHERE_DOMAIN` ga yozing.
3. Mini App URL: `https://sizning-manzil.ngrok-free.app/tma`
4. Admin Panel URL: `https://sizning-manzil.ngrok-free.app/admin-panel`

## 📋 Bot Komandalari
- `/start`: Botni boshlash va Mini App orqali ro'yxatdan o'tish.
- `/submit`: Natijalarni qo'lda (Mini App'siz) topshirish.

## ⚖️ License
MIT
