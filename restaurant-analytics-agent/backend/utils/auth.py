"""
Authentication Utilities
JWT token generation, validation, and password hashing
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

import jwt
from passlib.context import CryptContext

from ..config.settings import get_settings

logger = logging.getLogger(__name__)

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT Configuration
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours


def get_jwt_secret() -> str:
    """Get JWT secret from settings or generate a default for development"""
    settings = get_settings()
    secret = getattr(settings, "jwt_secret_key", None)
    if not secret:
        # Fallback to a combination of other secrets for development
        # In production, JWT_SECRET_KEY should always be set
        # Prefer NVIDIA API key (default), then Grok, otherwise default
        api_key = settings.nvidia_api_key or settings.grok_api_key
        if api_key:
            secret = api_key[:32] + "restaurant_analytics_jwt_secret"
        else:
            secret = "default_jwt_secret_change_in_production_restaurant_analytics"
        logger.warning("JWT_SECRET_KEY not set, using derived secret. Set JWT_SECRET_KEY in production!")
    return secret


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Generate password hash"""
    return pwd_context.hash(password)


def create_access_token(
    data: dict[str, Any],
    expires_delta: timedelta | None = None
) -> tuple[str, int]:
    """
    Create a JWT access token.
    
    Args:
        data: Data to encode in the token
        expires_delta: Optional custom expiration time
        
    Returns:
        Tuple of (token_string, expires_in_seconds)
    """
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
        expires_in = int(expires_delta.total_seconds())
    else:
        expires_in = ACCESS_TOKEN_EXPIRE_MINUTES * 60
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "type": "access"
    })
    
    encoded_jwt = jwt.encode(to_encode, get_jwt_secret(), algorithm=ALGORITHM)
    return encoded_jwt, expires_in


def decode_access_token(token: str) -> dict[str, Any] | None:
    """
    Decode and validate a JWT access token.
    
    Args:
        token: The JWT token string
        
    Returns:
        Decoded token payload or None if invalid
    """
    try:
        payload = jwt.decode(token, get_jwt_secret(), algorithms=[ALGORITHM])
        
        # Verify token type
        if payload.get("type") != "access":
            logger.warning("Invalid token type")
            return None
            
        return payload
        
    except jwt.ExpiredSignatureError:
        logger.warning("Token has expired")
        return None
    except jwt.InvalidTokenError as e:
        logger.warning(f"Invalid token: {e}")
        return None


def get_user_id_from_token(token: str) -> UUID | None:
    """
    Extract user ID from a JWT token.
    
    Args:
        token: The JWT token string
        
    Returns:
        User UUID or None if invalid
    """
    payload = decode_access_token(token)
    if payload and "sub" in payload:
        try:
            return UUID(payload["sub"])
        except (ValueError, TypeError):
            return None
    return None
