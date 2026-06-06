"""
JWT verification middleware for Cognito access tokens.

Every protected route must be decorated with @require_auth.
On success, the verified claims are stored in flask.g:
  g.user_id  – Cognito sub (UUID, used as the S3 prefix and DynamoDB PK)
  g.email    – user's email (from the token claims)
  g.claims   – full decoded claims dict
"""

import functools
import json
import time
import urllib.request
from typing import Any

from flask import g, jsonify, request
from jose import JWTError, jwt

from config import Config

# ---------------------------------------------------------------------------
# JWKS cache (refreshed at most once per hour)
# ---------------------------------------------------------------------------
_jwks_cache: dict[str, Any] = {"keys": None, "expires_at": 0.0}
_JWKS_TTL_SECONDS = 3600


def _fetch_jwks() -> dict:
    with urllib.request.urlopen(Config.jwks_url(), timeout=5) as resp:
        return json.loads(resp.read())


def _get_jwks() -> dict:
    now = time.monotonic()
    if _jwks_cache["keys"] is None or now >= _jwks_cache["expires_at"]:
        _jwks_cache["keys"] = _fetch_jwks()
        _jwks_cache["expires_at"] = now + _JWKS_TTL_SECONDS
    return _jwks_cache["keys"]


def _find_key(kid: str) -> dict | None:
    jwks = _get_jwks()
    return next((k for k in jwks.get("keys", []) if k["kid"] == kid), None)


# ---------------------------------------------------------------------------
# Token verification
# ---------------------------------------------------------------------------
def _verify_access_token(token: str) -> dict:
    """
    Validate a Cognito access token and return its claims.
    Raises ValueError with a descriptive message on failure.
    """
    try:
        headers = jwt.get_unverified_headers(token)
    except JWTError as exc:
        raise ValueError(f"Malformed token header: {exc}") from exc

    kid = headers.get("kid")
    if not kid:
        raise ValueError("Token header missing 'kid'")

    key = _find_key(kid)
    if key is None:
        # Kid not found – JWKS may have rotated; clear cache and retry once
        _jwks_cache["keys"] = None
        key = _find_key(kid)
    if key is None:
        raise ValueError("Unknown signing key")

    try:
        claims = jwt.decode(
            token,
            key,
            algorithms=["RS256"],
            # Cognito access tokens do NOT include an 'aud' claim
            options={"verify_aud": False},
        )
    except JWTError as exc:
        raise ValueError(f"Token decode failed: {exc}") from exc

    # Enforce Cognito-specific claims
    if claims.get("token_use") != "access":
        raise ValueError("Token is not an access token")

    expected_iss = Config.cognito_issuer()
    if claims.get("iss") != expected_iss:
        raise ValueError("Token issuer does not match User Pool")

    return claims


# ---------------------------------------------------------------------------
# Decorator
# ---------------------------------------------------------------------------
def require_auth(f):
    """Route decorator that validates a Bearer access token from Cognito."""

    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        auth_header: str = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return (
                jsonify({"error": "Authorization header missing or not Bearer"}),
                401,
            )

        token = auth_header[len("Bearer "):]
        try:
            claims = _verify_access_token(token)
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 401

        g.user_id = claims["sub"]
        g.email = claims.get("email", claims.get("username", ""))
        g.claims = claims

        return f(*args, **kwargs)

    return wrapper
