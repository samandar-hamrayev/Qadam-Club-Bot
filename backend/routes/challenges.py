from flask import Blueprint, request, jsonify
from datetime import datetime, timedelta, time
from ..database import SessionLocal
from ..models import User, Challenge, UserChallenge, Submission
from sqlalchemy import select, and_
from config import Config

challenges_bp = Blueprint('challenges', __name__)

@challenges_bp.route('/', methods=['GET'])
def get_challenges():
    telegram_id = request.args.get('telegram_id', type=int)
    db = SessionLocal()
    try:
        challenges = db.query(Challenge).filter(Challenge.is_active == True).all()
        
        user = None
        if telegram_id:
            user = db.query(User).filter(User.telegram_id == telegram_id).first()
            
        result = []
        for c in challenges:
            is_joined = False
            if user:
                uc = db.query(UserChallenge).filter(
                    and_(UserChallenge.user_id == user.id, UserChallenge.challenge_id == c.id)
                ).first()
                is_joined = uc.is_joined if uc else False
                
            result.append({
                "id": c.id,
                "title": c.title,
                "description": c.description,
                "code": c.code,
                "target_unit": c.target_unit,
                "time_window_start": c.time_window_start,
                "time_window_end": c.time_window_end,
                "is_joined": is_joined
            })
        return jsonify(result)
    finally:
        db.close()

@challenges_bp.route('/<int:challenge_id>/join', methods=['POST'])
def join_challenge(challenge_id):
    data = request.json
    telegram_id = data.get('telegram_id')
    
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.telegram_id == telegram_id).first()
        if not user:
            return jsonify({"error": "User not found"}), 404
        
        uc = db.query(UserChallenge).filter(
            and_(UserChallenge.user_id == user.id, UserChallenge.challenge_id == challenge_id)
        ).first()
        
        if uc:
            uc.is_joined = True
        else:
            uc = UserChallenge(user_id=user.id, challenge_id=challenge_id)
            db.add(uc)
        
        db.commit()
        return jsonify({"status": "success", "message": "Joined challenge"})
    finally:
        db.close()

@challenges_bp.route('/<int:challenge_id>/submit', methods=['POST'])
def submit_result(challenge_id):
    data = request.json
    telegram_id = data.get('telegram_id')
    value = float(data.get('value', 0))
    
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.telegram_id == telegram_id).first()
        if not user:
            return jsonify({"error": "User not found"}), 404
        
        challenge = db.query(Challenge).get(challenge_id)
        if not challenge:
            return jsonify({"error": "Challenge not found"}), 404
            
        # Time window check for Book Challenge (code='book')
        now = datetime.now()
        if challenge.code == 'book' and challenge.time_window_start and challenge.time_window_end:
            start_h, start_m = map(int, challenge.time_window_start.split(':'))
            end_h, end_m = map(int, challenge.time_window_end.split(':'))
            start_time = time(start_h, start_m)
            end_time = time(end_h, end_m)
            current_time = now.time()
            
            if not (start_time <= current_time <= end_time):
                return jsonify({"error": f"Submission only allowed between {challenge.time_window_start} and {challenge.time_window_end}"}), 400

        # Check if already submitted today
        today = now.date()
        existing_sub = db.query(Submission).filter(
            and_(Submission.user_id == user.id, Submission.challenge_id == challenge_id, Submission.date == today)
        ).first()
        
        if existing_sub:
            return jsonify({"error": "Already submitted today"}), 400
            
        # Create submission
        submission = Submission(user_id=user.id, challenge_id=challenge_id, value=value, date=today)
        db.add(submission)
        
        # Update streak and total
        uc = db.query(UserChallenge).filter(
            and_(UserChallenge.user_id == user.id, UserChallenge.challenge_id == challenge_id)
        ).first()
        
        if not uc:
            return jsonify({"error": "You must join the challenge first"}), 400
            
        # Streak logic
        yesterday = today - timedelta(days=1)
        last_sub = db.query(Submission).filter(
            and_(Submission.user_id == user.id, Submission.challenge_id == challenge_id, Submission.date == yesterday)
        ).first()
        
        if last_sub:
            uc.current_streak += 1
        else:
            uc.current_streak = 1
            
        if uc.current_streak > uc.max_streak:
            uc.max_streak = uc.current_streak
            
        uc.total_value += value
        
        db.commit()
        return jsonify({
            "status": "success", 
            "current_streak": uc.current_streak,
            "total_value": uc.total_value
        })
    except Exception as e:
        db.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        db.close()
