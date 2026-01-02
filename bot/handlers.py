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
    base_url = Config.PYTHONANYWHERE_DOMAIN or "https://your-domain.com"
    # Clean the base_url: remove trailing slash and /tma if present
    base_url = base_url.rstrip('/')
    if base_url.endswith('/tma'):
        base_url = base_url[:-4]
    
    keyboard = [
        [InlineKeyboardButton("Open Mini App", web_app=WebAppInfo(url=f"{base_url}/tma"))]
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
    text = update.message.text.strip()
    user_id = update.effective_user.id
    
    # 1. Check if it's a command like /code or /code 1500
    if text.startswith('/'):
        parts = text[1:].split()
        if not parts:
            return
        
        code = parts[0]
        # Check if it's a challenge code
        try:
            response = requests.get(f"{API_BASE_URL}/challenges/")
            challenges = response.json()
            challenge = next((c for c in challenges if c['code'] == code), None)
            
            if challenge:
                challenge_id = challenge['id']
                # If value is provided in the same message: /code 1500
                if len(parts) > 1:
                    try:
                        value = float(parts[1])
                        await _process_submission(update, context, user_id, challenge_id, value)
                        return
                    except ValueError:
                        pass # Continue to 'kiriting' logic if not a number
                
                # Otherwise, set state and ask for value
                context.user_data['active_submission'] = challenge_id
                await update.message.reply_text(f"{challenge['title']} uchun natijani kiriting (masalan: 10):")
                return
        except Exception as e:
            print(f"Challenge check error: {e}")

    # 2. If we are waiting for a value (normal text or invalid command that might be a value)
    if 'active_submission' in context.user_data:
        challenge_id = context.user_data['active_submission']
        try:
            # Try to get value from the whole text (if it's just a number)
            # or from the second part if they accidentally sent /code value again
            clean_text = text
            if text.startswith('/'):
                parts = text.split()
                if len(parts) > 1:
                    clean_text = parts[1]
                else:
                    # It's just a /command, maybe a different one? 
                    # If it's a known challenge we already handled it above.
                    # If it's unknown, we should probably ignore it or tell them to enter a number.
                    return

            value = float(clean_text)
            context.user_data.pop('active_submission')
            await _process_submission(update, context, user_id, challenge_id, value)
        except ValueError:
            await update.message.reply_text("Iltimos, faqat son kiriting (yoki /cancel deb yozing).")
        except Exception as e:
            print(f"Submission Error: {e}")
            await update.message.reply_text("Topshirishda xatolik yuz berdi.")

async def _process_submission(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id, challenge_id, value):
    try:
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
    except Exception as e:
        print(f"Processing Error: {e}")
        await update.message.reply_text("Topshirishda xatolik yuz berdi.")

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if 'active_submission' in context.user_data:
        context.user_data.pop('active_submission')
        await update.message.reply_text("Bekor qilindi. ❌")
    else:
        await update.message.reply_text("Hozircha bekor qiladigan narsa yo'q.")
