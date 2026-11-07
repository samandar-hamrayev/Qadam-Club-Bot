from flask import Blueprint, jsonify, request

from .. import services
from ..auth import require_admin
from ..database import session_scope
from ._helpers import int_arg

admin_bp = Blueprint("admin", __name__)


@admin_bp.route("/challenges", methods=["GET"])
@require_admin
def list_challenges():
    """
    List all challenges, including inactive ones.
    ---
    tags: [Admin]
    security: [{AdminToken: []}, {TelegramInitData: []}]
    responses:
      200:
        description: All challenges
      401:
        description: Missing or invalid credentials
    """
    with session_scope() as db:
        return jsonify(services.list_all_challenges(db))


@admin_bp.route("/challenges", methods=["POST"])
@require_admin
def create_challenge():
    """
    Create a challenge.
    ---
    tags: [Admin]
    security: [{AdminToken: []}, {TelegramInitData: []}]
    parameters:
      - name: body
        in: body
        required: true
        schema:
          type: object
          required: [title, code]
          properties:
            title: {type: string, example: Book Challenge}
            description: {type: string}
            code: {type: string, example: book, description: "a-z, 0-9, _ (also a bot command)"}
            target_unit: {type: string, example: pages}
            time_window_start: {type: string, example: "21:00"}
            time_window_end: {type: string, example: "23:59"}
            is_active: {type: boolean}
    responses:
      201:
        description: Created
      400:
        description: Validation error
      401:
        description: Missing or invalid credentials
      409:
        description: Code already exists
    """
    with session_scope() as db:
        challenge = services.create_challenge(db, request.get_json(silent=True))
        payload = services.challenge_to_dict(challenge)
    return jsonify({"status": "success", "id": payload["id"], "challenge": payload}), 201


@admin_bp.route("/challenges/<int:challenge_id>", methods=["PATCH"])
@require_admin
def update_challenge(challenge_id: int):
    """
    Update whitelisted challenge fields.
    ---
    tags: [Admin]
    security: [{AdminToken: []}, {TelegramInitData: []}]
    parameters:
      - {name: challenge_id, in: path, type: integer, required: true}
      - name: body
        in: body
        required: true
        schema:
          type: object
          properties:
            title: {type: string}
            description: {type: string}
            code: {type: string}
            target_unit: {type: string}
            time_window_start: {type: string}
            time_window_end: {type: string}
            is_active: {type: boolean}
    responses:
      200:
        description: Updated
      400:
        description: Validation error or unknown field
      404:
        description: Challenge not found
    """
    with session_scope() as db:
        challenge = services.update_challenge(db, challenge_id, request.get_json(silent=True))
        payload = services.challenge_to_dict(challenge)
    return jsonify({"status": "success", "challenge": payload})


@admin_bp.route("/users", methods=["GET"])
@require_admin
def list_users():
    """
    List users (paginated).
    ---
    tags: [Admin]
    security: [{AdminToken: []}, {TelegramInitData: []}]
    parameters:
      - {name: limit, in: query, type: integer, default: 100}
      - {name: offset, in: query, type: integer, default: 0}
    responses:
      200:
        description: Users
    """
    limit = min(max(int_arg("limit", required=False, default=100), 1), 500)
    offset = max(int_arg("offset", required=False, default=0), 0)
    with session_scope() as db:
        return jsonify(services.list_users(db, limit=limit, offset=offset))


def _set_banned(user_id: int, banned: bool):
    with session_scope() as db:
        user = services.set_banned(db, user_id, banned)
        payload = services.user_to_dict(user)
    return jsonify({"status": "success", "user": payload})


@admin_bp.route("/users/<int:user_id>/ban", methods=["POST"])
@require_admin
def ban_user(user_id: int):
    """
    Ban a user (blocks joining and submitting, hides them from leaderboards).
    ---
    tags: [Admin]
    security: [{AdminToken: []}, {TelegramInitData: []}]
    parameters:
      - {name: user_id, in: path, type: integer, required: true}
    responses:
      200:
        description: Banned
      404:
        description: User not found
    """
    return _set_banned(user_id, True)


@admin_bp.route("/users/<int:user_id>/unban", methods=["POST"])
@require_admin
def unban_user(user_id: int):
    """
    Lift a ban.
    ---
    tags: [Admin]
    security: [{AdminToken: []}, {TelegramInitData: []}]
    parameters:
      - {name: user_id, in: path, type: integer, required: true}
    responses:
      200:
        description: Unbanned
      404:
        description: User not found
    """
    return _set_banned(user_id, False)
