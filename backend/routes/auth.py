from flask import Blueprint, request, jsonify
from ..database import SessionLocal
from ..models import User, AdminUser
from sqlalchemy import select

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.json
    if not data or 'telegram_id' not in data:
        return jsonify({"error": "Missing telegram_id"}), 400
    
    telegram_id = data['telegram_id']
    full_name = data.get('full_name', 'Unknown')
    username = data.get('username')
    
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.telegram_id == telegram_id).first()
        if not user:
            user = User(
                telegram_id=telegram_id,
                full_name=full_name,
                username=username
            )
            db.add(user)
        else:
            user.full_name = full_name
            user.username = username
        
        db.commit()
        
        # Check if admin
        is_admin = db.query(AdminUser).filter(AdminUser.telegram_id == telegram_id).first() is not None
        
        return jsonify({
            "status": "success",
            "user": {
                "id": user.id,
                "telegram_id": user.telegram_id,
                "full_name": user.full_name,
                "username": user.username,
                "is_active": user.is_active,
                "is_banned": user.is_banned,
                "is_admin": is_admin
            }
        })
    except Exception as e:
        db.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        db.close()
