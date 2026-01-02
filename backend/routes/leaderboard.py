from flask import Blueprint, request, jsonify
from datetime import datetime, timedelta
from ..database import SessionLocal
from ..models import User, Challenge, Submission, UserChallenge
from sqlalchemy import func, and_

leaderboard_bp = Blueprint('leaderboard', __name__)

@leaderboard_bp.route('/', methods=['GET'])
def get_leaderboard():
    """
    Challenge peshqadamlar jadvalini olish
    ---
    tags:
      - Leaderboard
    parameters:
      - name: challenge_id
        in: query
        type: integer
        required: true
      - name: period
        in: query
        type: string
        enum: [today, weekly, monthly, all]
        default: today
    responses:
      200:
        description: Peshaqadamlar ro'yxati
        schema:
          type: array
          items:
            properties:
              full_name:
                type: string
              username:
                type: string
              total_value:
                type: number
    """
    challenge_id = request.args.get('challenge_id', type=int)
    period = request.args.get('period', 'today') # today, weekly, monthly, all
    
    if not challenge_id:
        return jsonify({"error": "Missing challenge_id"}), 400
        
    db = SessionLocal()
    try:
        query = db.query(
            User.full_name,
            User.username,
            func.sum(Submission.value).label('total_value')
        ).join(Submission, User.id == Submission.user_id).filter(Submission.challenge_id == challenge_id)
        
        now = datetime.now()
        if period == 'today':
            query = query.filter(Submission.date == now.date())
        elif period == 'weekly':
            week_start = now.date() - timedelta(days=now.weekday())
            query = query.filter(Submission.date >= week_start)
        elif period == 'monthly':
            month_start = now.date().replace(day=1)
            query = query.filter(Submission.date >= month_start)
        # 'all' doesn't need additional filter
        
        results = query.group_by(User.id).order_by(func.sum(Submission.value).desc()).limit(10).all()
        
        return jsonify([{
            "full_name": r.full_name,
            "username": r.username,
            "total_value": float(r.total_value)
        } for r in results])
    finally:
        db.close()

@leaderboard_bp.route('/streaks', methods=['GET'])
def get_streak_leaderboard():
    """
    Streak bo'yicha peshqadamlar jadvali
    ---
    tags:
      - Leaderboard
    parameters:
      - name: challenge_id
        in: query
        type: integer
        required: true
    responses:
      200:
        description: Streak peshqadamlari ro'yxati
        schema:
          type: array
          items:
            properties:
              full_name:
                type: string
              username:
                type: string
              current_streak:
                type: integer
              max_streak:
                type: integer
    """
    challenge_id = request.args.get('challenge_id', type=int)
    if not challenge_id:
        return jsonify({"error": "Missing challenge_id"}), 400
        
    db = SessionLocal()
    try:
        results = db.query(
            User.full_name,
            User.username,
            UserChallenge.current_streak,
            UserChallenge.max_streak
        ).join(UserChallenge, User.id == UserChallenge.user_id).filter(
            UserChallenge.challenge_id == challenge_id
        ).order_by(UserChallenge.current_streak.desc()).limit(10).all()
        
        return jsonify([{
            "full_name": r.full_name,
            "username": r.username,
            "current_streak": r.current_streak,
            "max_streak": r.max_streak
        } for r in results])
    finally:
        db.close()
