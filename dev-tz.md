Ushbu texnik topshiriq (TZ) LLM modellari (ChatGPT, Claude, Gemini) loyiha arxitekturasini va funksionalligini aniq tushunishi uchun tizimlashtirilgan Markdown formatiga o'tkazildi.

---

# Qadam Club Bot – Texnik Topshiriq (TZ)

## 1. Loyiha Maqsadi

**Qadam Club Bot** — foydalanuvchilarning kundalik odatlarini shakllantirish, intizomni oshirish va sog‘lom raqobat muhitini yaratishga mo‘ljallangan platforma. Tizim Telegram Bot va Telegram Mini App (TMA) negizida ishlaydi.

**Asosiy imkoniyatlar:**

* 
**Foydalanuvchilar:** Challenge’larda qatnashish, kunlik natijalarni topshirish va reytinglarni kuzatish.


* 
**Adminlar:** Challenge’larni boshqarish, foydalanuvchilar statistikasini kuzatish va platformani nazorat qilish.



## 2. Texnik Stek va Arxitektura

Loyiha 4 ta asosiy komponentdan iborat bo'lib, yagona Backend va Ma'lumotlar bazasiga ulanadi.

* 
**Runtime:** Python 3.10 (Majburiy).


* 
**Platforma:** PythonAnywhere (Bot polling rejimida ishlaydi, Webhook ishlatilmaydi).


* 
**Backend:** Flask 3.0, SQLAlchemy 2.x, Flask-CORS.


* 
**Telegram:** `python-telegram-bot >= 21`.


* 
**Frontend:** HTML/CSS/JS (Mini App va Admin Panel uchun).


* 
**Task Scheduler:** APScheduler (Eslatmalar va yakuniy hisob-kitoblar uchun).



## 3. Funksional Talablar

### 3.1. Telegram Bot (`/start` va Registratsiya)

* 
**Salomlashuv:** Bot vazifasini tushuntiradi va Mini App’ni ochish tugmasini ko'rsatadi.


* **Registratsiya:** Majburiy jarayon. Foydalanuvchi `user_id`, ism va username (agar bo'lsa) bilan bazaga bog'lanadi.


* 
**Cheklov:** Registratsiya tugallanmaguncha challenge’larga qo'shilish imkonsiz.


* 
**Alternativ submission:** Mini App ishlamagan holatlar uchun `/submit` komandasi orqali raqamli natija qabul qilinadi.



### 3.2. Telegram Mini App (TMA)

TMA faqat ro'yxatdan o'tgan foydalanuvchilar uchun ochiq bo'ladi.

* 
**Profil:** Foydalanuvchi ismi, faol challenge’lar va joriy "streak" (davomiylik) ko'rsatiladi.


* 
**Challenge’lar bo'limi:** Barcha mavjud challenge’larni ko'rish, ularga qo'shilish yoki chiqish.


* 
**Natija topshirish:** Modal oyna orqali `float` (o'nlik son) qiymat kiritish.


* 
**Leaderboard:** Har bir challenge uchun "Today", "Weekly", "Monthly" va "All-time" reytinglari.



### 3.3. Challenge Logikasi va Qoidalar

* Har bir challenge uchun kuniga faqat bitta submission (natija) qabul qilinadi.


* "Streak" (uzluksiz kunlar) avtomatik hisoblab boriladi.


* 
**Maxsus qoida (Book Challenge):** Natija faqat belgilangan vaqt oralig'ida (masalan, 21:00-23:59) qabul qilinadi, boshqa vaqtda rad etiladi.



## 4. Admin Panel

Faqat maxsus role yoki Telegram ID’ga ega adminlar kirishi mumkin.

* 
**Challenge Management:** Yangi challenge yaratish, tahrirlash, aktiv/deaktiv qilish va vaqt chegarasini (`time window`) o'rnatish.


* 
**User Management:** Foydalanuvchilar ro'yxati, ularning statistikasi va blocklash (ban) imkoniyati.


* 
**Analitika:** Kunlik faol foydalanuvchilar, ommabop challenge’lar va g'oliblar ro'yxati.


* 
**Manual Actions:** Natijalarni o'chirish, streak’ni yangilash yoki foydalanuvchini challenge’dan chiqarib yuborish.



## 5. Ma'lumotlar Bazasi Strukturasi (SQLAlchemy)

Quyidagi asosiy jadvallar bo'lishi shart:

* 
`users`: Foydalanuvchi ma'lumotlari.


* 
`challenges`: Challenge sozlamalari.


* 
`user_challenges`: Foydalanuvchi va challenge bog'liqligi.


* 
`submissions`: Kunlik topshirilgan natijalar.


* 
`admin_users`: Adminlar ro'yxati.


* 
`weekly_results` / `monthly_results`: Yakuniy natijalar jadvallari.



## 6. Backend API Endpoint'lar

* 
`POST /api/auth/register` — Ro'yxatdan o'tish.


* 
`GET /api/challenges` — Challenge’lar ro'yxati.


* 
`POST /api/challenges/<id>/join` — Qo'shilish.


* 
`POST /api/challenges/<id>/submit` — Natija topshirish.


* 
`GET /api/leaderboard?type=today|weekly|monthly|all` — Reytinglar.


* 
`/api/admin/*` — Admin paneli uchun ichki endpoint’lar.



---

**Kutilayotgan natija:** Toza va hujjatlashtirilgan kod, to'liq ishlaydigan Bot, TMA va Admin Panel.

Ushbu TZ asosida loyihaning ma'lumotlar bazasi sxemasini (database schema) chizib berishimni xohlaysizmi?