from flask import Blueprint, request, jsonify
from ..database import SessionLocal
from ..models import User, Challenge, AdminUser, Submission
from sqlalchemy import select, and_

admin_bp = Blueprint('admin', __name__)

def check_admin(telegram_id):
    db = SessionLocal()
    try:
        admin = db.query(AdminUser).filter(AdminUser.telegram_id == telegram_id).first()
        return admin is not None
    finally:
        db.close()

@admin_bp.route('/challenges', methods=['POST'])
def create_challenge():
    data = request.json
    admin_id = data.get('admin_id')
    if not check_admin(admin_id):
        return jsonify({"error": "Unauthorized"}), 403
    
    db = SessionLocal()
    try:
        challenge = Challenge(
            title=data['title'],
            description=data.get('description'),
            code=data['code'],
            target_unit=data.get('target_unit', 'units'),
            time_window_start=data.get('time_window_start'),
            time_window_end=data.get('time_window_end')
        )
        db.add(challenge)
        db.commit()
        return jsonify({"status": "success", "id": challenge.id})
    except Exception as e:
        db.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        db.close()

@admin_bp.route('/challenges/<int:id>', methods=['PATCH'])
def update_challenge(id):
    data = request.json
    admin_id = data.get('admin_id')
    if not check_admin(admin_id):
        return jsonify({"error": "Unauthorized"}), 403
    
    db = SessionLocal()
    try:
        challenge = db.query(Challenge).get(id)
        if not challenge:
            return jsonify({"error": "Challenge not found"}), 404
        
        for key, value in data.items():
            if hasattr(challenge, key) and key != 'id':
                setattr(challenge, key, value)
        
        db.commit()
        return jsonify({"status": "success"})
    finally:
        db.close()

@admin_bp.route('/users', methods=['GET'])
def list_users():
    admin_id = request.args.get('admin_id', type=int)
    if not check_admin(admin_id):
        return jsonify({"error": "Unauthorized"}), 403
        
    db = SessionLocal()
    try:
        users = db.query(User).all()
        return jsonify([{
            "id": u.id,
            "telegram_id": u.telegram_id,
            "full_name": u.full_name,
            "username": u.username,
            "is_active": u.is_active,
            "is_banned": u.is_banned
        } for u in users])
    finally:
        db.close()

@admin_bp.route('/users/<int:id>/ban', methods=['POST'])
def ban_user(id):
    data = request.json
    admin_id = data.get('admin_id')
    if not check_admin(admin_id):
        return jsonify({"error": "Unauthorized"}), 403
        
    db = SessionLocal()
    try:
        user = db.query(User).get(id)
        if not user:
            return jsonify({"error": "User not found"}), 404
        user.is_banned = True
        db.commit()
        return jsonify({"status": "success"})
    finally:
        db.close()
