from flask import Blueprint, jsonify

from .. import services
from ..auth import current_user, now_local, require_tma_user
from ..database import session_scope
from ._helpers import json_body

challenges_bp = Blueprint("challenges", __name__)


@challenges_bp.route("/", methods=["GET"])
@require_tma_user
def get_challenges():
    """
    List active challenges with the caller's membership status.
    ---
    tags: [Challenges]
    security: [{TelegramInitData: []}]
    responses:
      200:
        description: Active challenges (each with is_joined)
      401:
        description: Missing, forged or expired initData
    """
    with session_scope() as db:
        result = services.list_active_challenges(db, current_user(db))
    return jsonify(result)


@challenges_bp.route("/<int:challenge_id>/join", methods=["POST"])
@require_tma_user
def join_challenge(challenge_id: int):
    """
    Join a challenge.
    ---
    tags: [Challenges]
    security: [{TelegramInitData: []}]
    parameters:
      - {name: challenge_id, in: path, type: integer, required: true}
    responses:
      200:
        description: Joined
      403:
        description: User is banned
      404:
        description: Challenge not found or inactive
    """
    with session_scope() as db:
        services.join_challenge(db, current_user(db), challenge_id)
    return jsonify({"status": "success", "message": "Joined challenge"})


@challenges_bp.route("/<int:challenge_id>/submit", methods=["POST"])
@require_tma_user
def submit_result(challenge_id: int):
    """
    Submit today's result. One submission per challenge day; the streak is
    computed over local dates in the configured TIMEZONE.
    ---
    tags: [Challenges]
    security: [{TelegramInitData: []}]
    parameters:
      - {name: challenge_id, in: path, type: integer, required: true}
      - name: body
        in: body
        required: true
        schema:
          type: object
          required: [value]
          properties:
            value: {type: number, example: 25, description: "0 < value <= 1,000,000"}
    responses:
      200:
        description: Accepted; returns current_streak, max_streak and total_value
      400:
        description: Invalid value
      403:
        description: User is banned
      404:
        description: Challenge not found or inactive
      409:
        description: Already submitted for this challenge day
      422:
        description: Outside the submission window
    """
    body = json_body()
    with session_scope() as db:
        outcome = services.submit_result(
            db, current_user(db), challenge_id, body.get("value"), now_local()
        )
    return jsonify(outcome.to_dict())
