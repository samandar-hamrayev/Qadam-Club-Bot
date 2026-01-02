import logging
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters
from config import Config
from .handlers import start, submit, handle_message

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

def run_bot():
    if not Config.BOT_TOKEN:
        print("Error: BOT_TOKEN not found in environment variables")
        return

    application = ApplicationBuilder().token(Config.BOT_TOKEN).build()
    
    # Handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("submit", submit))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Scheduler
    from .scheduler import setup_scheduler
    setup_scheduler(application)
    
    print("Bot is starting...")
    application.run_polling()

if __name__ == "__main__":
    run_bot()
