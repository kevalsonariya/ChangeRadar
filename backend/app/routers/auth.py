"""Authentication and User Account endpoints."""

from typing import Optional
from fastapi import APIRouter, Cookie, Depends, Header, HTTPException, Request, Response, status
from sqlalchemy.orm import Session
from ..database import get_db
from ..models.models import User
from ..schemas.schemas import (
    ResendVerificationRequest,
    UserLogin,
    UserRegister,
    UserResponse,
    UserUpdateSettings,
    VerifyEmailRequest,
)
from ..services import auth_service, email_service

router = APIRouter(tags=["authentication"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED, summary="Register a new user")
async def register(
    user_in: UserRegister,
    request: Request,
    response: Response,
    db: Session = Depends(get_db)
):
    """Register a new user account, hash password, create session, and send verification token."""
    auth_service.check_rate_limit(request, action="register")

    # Check for existing user with normalized email
    normalized_email = user_in.email.strip().lower()
    existing_user = db.query(User).filter(User.email == normalized_email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email address already exists."
        )

    # Hash password securely using PBKDF2-HMAC-SHA256
    password_hash = auth_service.hash_password(user_in.password)

    new_user = User(
        name=user_in.name,
        email=normalized_email,
        password_hash=password_hash,
        email_verified=False,
        email_notifications_enabled=True,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    # Create session cookie so the user is immediately signed in
    token = auth_service.create_user_session(db, new_user, response=response)

    # Create single-use expiring email verification token
    verification_token = auth_service.create_verification_token(db, new_user)

    # Attempt to send verification email (fail-safe: will not abort registration if SMTP is offline)
    email_sent, err_msg = await email_service.send_verification_email(
        recipient_name=new_user.name,
        recipient_email=new_user.email,
        token=verification_token
    )

    return new_user


@router.post("/login", response_model=UserResponse, summary="Log in with email and password")
def login(
    credentials: UserLogin,
    request: Request,
    response: Response,
    db: Session = Depends(get_db)
):
    """Authenticate user with email and password, returning user data and setting secure session cookie."""
    auth_service.check_rate_limit(request, action="login")

    normalized_email = credentials.email.strip().lower()
    user = db.query(User).filter(User.email == normalized_email).first()

    if not user or not auth_service.verify_password(credentials.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password."
        )

    # Set session cookie
    auth_service.create_user_session(db, user, response=response)
    return user


@router.post("/logout", summary="Log out the current user")
def logout(
    response: Response,
    db: Session = Depends(get_db),
    changeradar_session: Optional[str] = Cookie(None),
    authorization: Optional[str] = Header(None)
):
    """Invalidate the session in the database and clear the session cookie."""
    token = changeradar_session
    if not token and authorization and authorization.startswith("Bearer "):
        token = authorization[7:].strip()

    if token:
        auth_service.invalidate_user_session(db, token, response=response)
    else:
        auth_service.invalidate_user_session(db, "", response=response)

    return {"message": "Successfully logged out"}


@router.get("/me", response_model=UserResponse, summary="Get current authenticated user profile")
def get_me(current_user: User = Depends(auth_service.get_current_user)):
    """Retrieve profile and settings of current authenticated user."""
    return current_user


@router.patch("/settings", response_model=UserResponse, summary="Update account settings and notification preferences")
def update_settings(
    settings_in: UserUpdateSettings,
    current_user: User = Depends(auth_service.get_current_user),
    db: Session = Depends(get_db)
):
    """Update user's name or notification preferences."""
    if settings_in.email_notifications_enabled is not None:
        current_user.email_notifications_enabled = settings_in.email_notifications_enabled
    if settings_in.name is not None and settings_in.name.strip():
        current_user.name = settings_in.name.strip()

    db.commit()
    db.refresh(current_user)
    return current_user


@router.post("/verify-email", summary="Verify email address with token")
def verify_email(
    request_data: VerifyEmailRequest,
    db: Session = Depends(get_db)
):
    """Validate verification token and mark user email as verified."""
    user = auth_service.verify_email_token(db, request_data.token)
    return {
        "success": True,
        "message": f"Email address '{user.email}' has been successfully verified! Alerts are now active.",
        "email_verified": True
    }


@router.post("/resend-verification", summary="Resend email verification token")
async def resend_verification(
    request_data: Optional[ResendVerificationRequest] = None,
    current_user: Optional[User] = Depends(auth_service.get_optional_current_user),
    db: Session = Depends(get_db)
):
    """Resend a new verification token to the user's email."""
    target_user = current_user
    if not target_user and request_data and request_data.email:
        target_user = db.query(User).filter(User.email == request_data.email.strip().lower()).first()

    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User email is required to resend verification."
        )

    if target_user.email_verified:
        return {
            "success": True,
            "message": "Email is already verified.",
            "email_verified": True
        }

    token = auth_service.create_verification_token(db, target_user)
    sent, err = await email_service.send_verification_email(
        recipient_name=target_user.name,
        recipient_email=target_user.email,
        token=token
    )

    if not sent and not email_service.is_smtp_configured():
        return {
            "success": True,
            "message": f"SMTP is not configured in development. Verification token: {token}",
            "token": token
        }

    return {
        "success": True,
        "message": f"A new verification email has been sent to {target_user.email}."
    }
