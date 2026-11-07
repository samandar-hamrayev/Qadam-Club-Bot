from flask import Blueprint, jsonify, request

from .. import services
from ..auth import now_local, require_tma_user
from ..database import session_scope
from ._helpers import int_arg

leaderboard_bp = Blueprint("leaderboard", __name__)


@leaderboard_bp.route("/", methods=["GET"])
@require_tma_user
def get_leaderboard():
    """
    Top 10 members of a challenge by total value.
    ---
    tags: [Leaderboard]
    security: [{TelegramInitData: []}]
    parameters:
      - {name: challenge_id, in: query, type: integer, required: true}
      - name: period
        in: query
        type: string
        enum: [today, weekly, monthly, all]
        default: today
    responses:
      200:
        description: Ranked entries (rank, full_name, username, total_value)
      400:
        description: Missing challenge_id or unknown period
    """
    challenge_id = int_arg("challenge_id")
    period = request.args.get("period", "today")
    with session_scope() as db:
        result = services.leaderboard(db, challenge_id, period, now_local())
    return jsonify(result)


@leaderboard_bp.route("/streaks", methods=["GET"])
@require_tma_user
def get_streak_leaderboard():
    """
    Top 10 members of a challenge by current streak (stale streaks count as 0).
    ---
    tags: [Leaderboard]
    security: [{TelegramInitData: []}]
    parameters:
      - {name: challenge_id, in: query, type: integer, required: true}
    responses:
      200:
        description: Entries (full_name, username, current_streak, max_streak)
    """
    challenge_id = int_arg("challenge_id")
    with session_scope() as db:
        result = services.streak_leaderboard(db, challenge_id, now_local())
    return jsonify(result)
