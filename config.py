import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Bot Settings
    BOT_TOKEN = os.getenv("BOT_TOKEN")
    ADMIN_IDS = [int(id.strip()) for id in os.getenv("ADMIN_IDS", "").split(",") if id.strip()]
    
    # Database Settings
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///qadam_club.db")
    
    # Flask Settings
    SECRET_KEY = os.getenv("SECRET_KEY", "super-secret-key-12345")
    API_URL = os.getenv("API_URL", "http://localhost:5000/api")
    
    # Challenge Settings
    BOOK_CHALLENGE_WINDOW = (21, 23) # 21:00 to 23:59
    
    # PythonAnywhere specific
    PYTHONANYWHERE_DOMAIN = os.getenv("PYTHONANYWHERE_DOMAIN")
