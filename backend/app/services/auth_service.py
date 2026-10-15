"""Authentication service: password hashing, session management, rate limiting, and email verification tokens."""

import hashlib
import hmac
import os
import secrets
import time
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple
from fastapi import Cookie, Depends, Header, HTTPException, Request, Response, status
from sqlalchemy.orm import Session
from ..database import get_db
from ..models.models import EmailVerificationToken, User, UserSession, utc_now

# Constants
COOKIE_NAME = "changeradar_session"
SESSION_DURATION_DAYS = 7
VERIFICATION_TOKEN_DURATION_HOURS = 24
PBKDF2_ITERATIONS = 600_000

# In-memory sliding window rate limiter for brute-force protection
# Key: (ip, action), Value: list of timestamps
_ATTEMPTS = defaultdict(list)
RATE_LIMIT_WINDOW = 60  # seconds
MAX_LOGIN_ATTEMPTS = 5   # max 5 attempts per minute per IP
MAX_REGISTER_ATTEMPTS = 3  # max 3 registrations per minute per IP

def reset_rate_limits():
    """Clear rate limit tracking dictionary (used primarily for automated test suites)."""
    _ATTEMPTS.clear()


def check_rate_limit(request: Request, action: str = "login"):
    """Prevent brute-force abuse by checking client IP against sliding window rate limit."""

    client_ip = request.client.host if request.client else "127.0.0.1"
    now = time.time()
    key = (client_ip, action)
    
    # Prune old timestamps
    _ATTEMPTS[key] = [t for t in _ATTEMPTS[key] if now - t < RATE_LIMIT_WINDOW]
    
    max_allowed = MAX_LOGIN_ATTEMPTS if action == "login" else MAX_REGISTER_ATTEMPTS
    if len(_ATTEMPTS[key]) >= max_allowed:
        retry_after = int(RATE_LIMIT_WINDOW - (now - _ATTEMPTS[key][0]))
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Too many {action} attempts. Please wait {max(1, retry_after)} seconds before trying again.",
            headers={"Retry-After": str(max(1, retry_after))}
        )
    _ATTEMPTS[key].append(now)


def hash_password(password: str) -> str:
    """Hash password using OWASP-recommended PBKDF2-HMAC-SHA256 with cryptographically secure random salt."""
    salt = secrets.token_hex(16)
    key = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        PBKDF2_ITERATIONS,
    )
    return f"{salt}${key.hex()}"


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password hash using constant-time comparison to prevent timing attacks."""
    try:
        parts = hashed_password.split("$")
        if len(parts) != 2:
            return False
        salt, expected_hex = parts
        computed_key = hashlib.pbkdf2_hmac(
            "sha256",
            plain_password.encode("utf-8"),
            salt.encode("utf-8"),
            PBKDF2_ITERATIONS,
        )
        return hmac.compare_digest(computed_key.hex(), expected_hex)
    except Exception:
        return False


def create_user_session(db: Session, user: User, response: Optional[Response] = None) -> str:
    """Generate high-entropy session token, persist to DB, and set secure HttpOnly cookie."""
    token = secrets.token_urlsafe(48)
    expires_at = utc_now() + timedelta(days=SESSION_DURATION_DAYS)
    
    session = UserSession(
        user_id=user.id,
        token=token,
        created_at=utc_now(),
        expires_at=expires_at
    )
    db.add(session)
    db.commit()
    
    if response:
        # Determine cookie security (secure=True if HTTPS or in production)
        is_production = os.getenv("ENVIRONMENT", "").lower() == "production"
        response.set_cookie(
            key=COOKIE_NAME,
            value=token,
            max_age=SESSION_DURATION_DAYS * 86400,
            httponly=True,
            samesite="lax",
            secure=is_production,
            path="/"
        )
    return token


def invalidate_user_session(db: Session, token: str, response: Optional[Response] = None):
    """Delete session from database and clear the session cookie."""
    db.query(UserSession).filter(UserSession.token == token).delete()
    db.commit()
    if response:
        response.delete_cookie(key=COOKIE_NAME, path="/")


def create_verification_token(db: Session, user: User) -> str:
    """Generate an expiring single-use verification token for the user."""
    # Invalidate any pending verification tokens for this user
    db.query(EmailVerificationToken).filter(
        EmailVerificationToken.user_id == user.id,
        EmailVerificationToken.used_at.is_(None)
    ).delete()
    
    token = secrets.token_urlsafe(32)
    expires_at = utc_now() + timedelta(hours=VERIFICATION_TOKEN_DURATION_HOURS)
    
    token_obj = EmailVerificationToken(
        user_id=user.id,
        token=token,
        created_at=utc_now(),
        expires_at=expires_at,
        used_at=None
    )
    db.add(token_obj)
    db.commit()
    return token


def verify_email_token(db: Session, token: str) -> User:
    """Validate token: must exist, not expired, and not previously used."""
    token_obj = db.query(EmailVerificationToken).filter(EmailVerificationToken.token == token).first()
    if not token_obj:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid email verification token."
        )
    
    if token_obj.used_at is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This verification token has already been used. Please request a new one."
        )
    
    # Check expiration (ensure both are UTC aware for comparison)
    now = utc_now()
    expires_at = token_obj.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
        
    if now > expires_at:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Verification token has expired. Please request a new verification email."
        )
    
    # Mark as used and mark user verified
    token_obj.used_at = now
    user = token_obj.user
    user.email_verified = True
    db.commit()
    db.refresh(user)
    return user


def get_current_user_from_token(
    db: Session,
    cookie_token: Optional[str],
    auth_header: Optional[str]
) -> Optional[User]:
    """Extract token from cookie or Authorization: Bearer header, look up valid session."""
    token = cookie_token
    if not token and auth_header and auth_header.startswith("Bearer "):
        token = auth_header[7:].strip()
        
    if not token:
        return None
        
    session = db.query(UserSession).filter(UserSession.token == token).first()
    if not session:
        return None
        
    # Check expiration
    now = utc_now()
    expires_at = session.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
        
    if now > expires_at:
        db.delete(session)
        db.commit()
        return None
        
    return session.user


def get_current_user(
    db: Session = Depends(get_db),
    changeradar_session: Optional[str] = Cookie(None),
    authorization: Optional[str] = Header(None)
) -> User:
    """Dependency that requires an authenticated user. Raises 401 if not authenticated."""
    user = get_current_user_from_token(db, changeradar_session, authorization)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Please sign in.",
            headers={"WWW-Authenticate": "Bearer"}
        )
    return user


def get_optional_current_user(
    db: Session = Depends(get_db),
    changeradar_session: Optional[str] = Cookie(None),
    authorization: Optional[str] = Header(None)
) -> Optional[User]:
    """Dependency that returns the authenticated user if present, or None if anonymous."""
    return get_current_user_from_token(db, changeradar_session, authorization)
