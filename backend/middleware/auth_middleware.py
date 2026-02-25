"""
auth_middleware.py — JWT Authentication Middleware
===================================================

Verifies JWT tokens from NextAuth.js on the frontend.
Extracts user info and provides it as a FastAPI dependency.

Usage in routes:
    from middleware.auth_middleware import get_current_user

    @router.get("/protected")
    async def protected(user = Depends(get_current_user)):
        return {"user": user.email}
"""

import os
import logging
from typing import Optional

from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logger = logging.getLogger(__name__)

security = HTTPBearer(auto_error=False)

# Secret used to sign JWTs — must match NEXTAUTH_SECRET on the frontend
JWT_SECRET = os.getenv("NEXTAUTH_SECRET", "your-secret-key-change-in-production")


def _decode_jwt(token: str) -> dict:
    """
    Decode and verify a JWT token from NextAuth.js.

    NextAuth uses the JOSE library with HS256 by default.
    """
    try:
        import jwt  # PyJWT
    except ImportError:
        # Fallback: try jose
        try:
            from jose import jwt as jose_jwt
            payload = jose_jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
            return payload
        except ImportError:
            raise ImportError("Install PyJWT or python-jose: pip install PyJWT")

    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(401, "Token expired")
    except jwt.InvalidTokenError as e:
        raise HTTPException(401, f"Invalid token: {str(e)}")


class CurrentUser:
    """Lightweight user object extracted from JWT."""
    def __init__(self, user_id: str, email: str, name: str = "", image: str = ""):
        self.id = user_id
        self.email = email
        self.name = name
        self.image = image


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> CurrentUser:
    """
    FastAPI dependency: extract and verify JWT → return CurrentUser.

    Use in route parameters:
        user = Depends(get_current_user)
    """
    if not credentials:
        raise HTTPException(401, "Authentication required")

    token = credentials.credentials
    payload = _decode_jwt(token)

    # NextAuth JWT payload typically has: sub, email, name, picture
    user_id = payload.get("sub") or payload.get("id")
    email = payload.get("email")

    if not user_id or not email:
        raise HTTPException(401, "Invalid token payload")

    return CurrentUser(
        user_id=user_id,
        email=email,
        name=payload.get("name", ""),
        image=payload.get("picture", payload.get("image", "")),
    )


async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> Optional[CurrentUser]:
    """
    Same as get_current_user but returns None instead of 401
    for unauthenticated requests. Useful for public endpoints.
    """
    if not credentials:
        return None

    try:
        return await get_current_user(credentials)
    except HTTPException:
        return None
