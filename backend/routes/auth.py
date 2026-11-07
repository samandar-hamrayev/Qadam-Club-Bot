from flask import Blueprint, g, jsonify

from .. import services
from ..auth import require_tma_user
from ..database import session_scope

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/register", methods=["POST"])
@require_tma_user
def register():
    """
    Register the Mini App user or refresh their profile.
    The identity comes exclusively from the validated Telegram initData.
    ---
    tags: [Auth]
    security: [{TelegramInitData: []}]
    responses:
      200:
        description: Registered user
      401:
        description: Missing, forged or expired initData
    """
    tg_user = g.init_data.user
    with session_scope() as db:
        user = services.upsert_user(db, tg_user.id, tg_user.full_name, tg_user.username)
        payload = services.user_to_dict(user, is_admin=services.is_admin(db, tg_user.id))
    return jsonify({"status": "success", "user": payload})
