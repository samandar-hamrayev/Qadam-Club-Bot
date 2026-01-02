from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime, timedelta
from telegram.ext import ContextTypes
import requests
from config import Config
from backend.database import SessionLocal
from backend.models import User, Submission, Challenge, UserChallenge, WeeklyResult, MonthlyResult
from sqlalchemy import func, and_

API_BASE_URL = Config.API_URL

async def send_daily_reminders(context: ContextTypes.DEFAULT_TYPE):
    db = SessionLocal()
    try:
        # Get users who haven't submitted today for active challenges
        today = datetime.now().date()
        active_challenges = db.query(Challenge).filter(Challenge.is_active == True).all()
        
        for challenge in active_challenges:
            # Users joined this challenge
            users_in_challenge = db.query(User).join(UserChallenge).filter(
                and_(UserChallenge.challenge_id == challenge.id, UserChallenge.is_joined == True)
            ).all()
            
            for user in users_in_challenge:
                # Check submission
                sub = db.query(Submission).filter(
                    and_(Submission.user_id == user.id, Submission.challenge_id == challenge.id, Submission.date == today)
                ).first()
                
                if not sub:
                    try:
                        await context.bot.send_message(
                            chat_id=user.telegram_id,
                            text=f"🔔 Eslatma: Bugun '{challenge.title}' challenge uchun natija topshirishni unutdingiz!"
                        )
                    except:
                        pass
    finally:
        db.close()

async def calculate_weekly_winners():
    db = SessionLocal()
    try:
        now = datetime.now()
        last_week_start = (now - timedelta(days=now.weekday() + 7)).date()
        last_week_end = (now - timedelta(days=now.weekday() + 1)).date()
        
        challenges = db.query(Challenge).all()
        for challenge in challenges:
            results = db.query(
                Submission.user_id,
                func.sum(Submission.value).label('total')
            ).filter(
                and_(
                    Submission.challenge_id == challenge.id,
                    Submission.date >= last_week_start,
                    Submission.date <= last_week_end
                )
            ).group_by(Submission.user_id).order_by(func.sum(Submission.value).desc()).all()
            
            for i, res in enumerate(results):
                wr = WeeklyResult(
                    user_id=res.user_id,
                    challenge_id=challenge.id,
                    week_start=last_week_start,
                    total_value=float(res.total),
                    rank=i+1
                )
                db.add(wr)
        db.commit()
    finally:
        db.close()

def setup_scheduler(application):
    scheduler = AsyncIOScheduler()
    
    # Daily reminders at 21:00
    scheduler.add_job(send_daily_reminders, 'cron', hour=21, minute=0, args=[application.job_queue])
    
    # Weekly results every Monday at 00:01
    scheduler.add_job(calculate_weekly_winners, 'cron', day_of_week='mon', hour=0, minute=1)
    
    scheduler.start()
