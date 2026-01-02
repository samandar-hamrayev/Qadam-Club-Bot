import requests
from telegram import Update, ReplyKeyboardMarkup, WebAppInfo, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from config import Config

API_BASE_URL = Config.API_URL

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    
    # Register user via API
    try:
        response = requests.post(f"{API_BASE_URL}/auth/register", json={
            "telegram_id": user.id,
            "full_name": user.full_name,
            "username": user.username
        })
        data = response.json()
    except Exception as e:
        print(f"Registration Error: {e}")
        await update.message.reply_text("Backend bilan bog'lanishda xatolik yuz berdi.")
        return

    welcome_text = (
        f"Salom, {user.full_name}! 👋\n\n"
        "Qadam Club Botiga xush kelibsiz! Bu yerda siz o'z odatlaringizni "
        "shakllantirishingiz va challenge'larda qatnashishingiz mumkin.\n\n"
        "Boshlash uchun Mini App'ni oching!"
    )
    
    # Mini App Button
    keyboard = [
        [InlineKeyboardButton("Open Mini App", web_app=WebAppInfo(url=Config.PYTHONANYWHERE_DOMAIN or "https://your-domain.com"))]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(welcome_text, reply_markup=reply_markup)

async def submit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Fetch active challenges
    try:
        response = requests.get(f"{API_BASE_URL}/challenges/")
        challenges = response.json()
    except Exception as e:
        await update.message.reply_text("Challenge'larni olishda xatolik!")
        return
    
    if not challenges:
        await update.message.reply_text("Hozircha faol challenge'lar yo'q.")
        return
        
    text = "Qaysi challenge uchun natija topshirmoqchisiz?\n\n"
    keyboard = []
    for c in challenges:
        text += f"/{c['code']} - {c['title']}\n"
        
    await update.message.reply_text(text)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.effective_user.id
    
    if text.startswith('/'):
        code = text[1:].split()[0]
        # Check if it's a challenge code
        try:
            response = requests.get(f"{API_BASE_URL}/challenges/")
            challenges = response.json()
            challenge = next((c for c in challenges if c['code'] == code), None)
            
            if challenge:
                context.user_data['active_submission'] = challenge['id']
                await update.message.reply_text(f"{challenge['title']} uchun natijani kiriting (masalan: 10):")
                return
        except:
            pass

    # If we are waiting for a value
    if 'active_submission' in context.user_data:
        challenge_id = context.user_data.pop('active_submission')
        try:
            value = float(text)
            response = requests.post(f"{API_BASE_URL}/challenges/{challenge_id}/submit", json={
                "telegram_id": user_id,
                "value": value
            })
            res_data = response.json()
            
            if response.status_code == 200:
                await update.message.reply_text(
                    f"Muvaffaqiyatli qabul qilindi! ✅\n"
                    f"Streak: {res_data['current_streak']} kun\n"
                    f"Jami: {res_data['total_value']}"
                )
            else:
                error_msg = res_data.get('error', "Noma'lum xato")
                await update.message.reply_text(f"Xato: {error_msg}")
        except ValueError:
            await update.message.reply_text("Iltimos, faqat son kiriting.")
        except Exception as e:
            await update.message.reply_text("Topshirishda xatolik yuz berdi.")
