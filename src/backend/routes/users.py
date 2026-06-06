"""
User-related routes.

POST /api/users/setup
  Called once after the very first login (or on every login – idempotent).
  Creates the user's folder prefix in S3.

GET  /api/users/profile
  Returns the authenticated user's basic profile from the JWT claims.
"""

from flask import Blueprint, g, jsonify

from middleware.auth import require_auth
from services import s3_service

users_bp = Blueprint("users", __name__)


@users_bp.route("/setup", methods=["POST"])
@require_auth
def setup_user():
    """
    Create the user's S3 prefix (folder) in UniversalDocumentRepository.
    Safe to call multiple times – S3 put_object is idempotent.
    """
    user_id: str = g.user_id
    s3_service.create_user_prefix(user_id)
    return jsonify({"message": "User workspace initialised", "userId": user_id}), 200


@users_bp.route("/profile", methods=["GET"])
@require_auth
def get_profile():
    """Return the caller's user_id and email extracted from the Cognito token."""
    return jsonify(
        {
            "userId": g.user_id,
            "email": g.email,
        }
    )
