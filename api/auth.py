"""
Authentication router: signup, login, logout, and me endpoints.
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from datetime import datetime, timedelta

from fastapi import APIRouter, HTTPException, Response, Request, Depends
from pydantic import BaseModel, EmailStr
from passlib.context import CryptContext
from jose import jwt, JWTError

import config
from api.database import create_user, get_user_by_email, get_user_by_id, update_user_password
from api.email_utils import send_email

router = APIRouter(prefix="/api/auth", tags=["auth"])
me_router = APIRouter(tags=["auth"])

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

ALGORITHM = "HS256"
TOKEN_EXPIRE_DAYS = 7
RESET_TOKEN_EXPIRE_HOURS = 1
COOKIE_NAME = "access_token"
FRONTEND_BASE_URL = os.environ.get("FRONTEND_BASE_URL", "http://localhost:3000")

# Overridden in tests to point at a test database.
DB_PATH = None


def _get_db_path():
    """Return the database path, using the override if set."""
    if DB_PATH is not None:
        return DB_PATH
    from api.database import DEFAULT_DB_PATH
    return DEFAULT_DB_PATH


def _create_token(user_id):
    """Create a JWT token for the given user ID."""
    expire = datetime.utcnow() + timedelta(days=TOKEN_EXPIRE_DAYS)
    return jwt.encode({"sub": str(user_id), "exp": expire}, config.JWT_SECRET, algorithm=ALGORITHM)


def _set_cookie(response, token):
    """Set the auth cookie on a response."""
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        httponly=True,
        samesite="lax",
        max_age=TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
    )


class SignupRequest(BaseModel):
    email: str
    name: str
    password: str


@router.post("/signup")
async def signup(req: SignupRequest, response: Response):
    if len(req.password) < 8:
        raise HTTPException(status_code=422, detail="Password must be at least 8 characters.")
    if not req.name.strip():
        raise HTTPException(status_code=422, detail="Name is required.")
    if not req.email.strip() or "@" not in req.email:
        raise HTTPException(status_code=422, detail="Valid email is required.")

    db_path = _get_db_path()
    existing = await get_user_by_email(req.email, db_path)
    if existing:
        raise HTTPException(status_code=409, detail="An account with this email already exists.")

    hashed = pwd_context.hash(req.password)
    user = await create_user(req.email, req.name, hashed, db_path)
    token = _create_token(user["id"])
    _set_cookie(response, token)
    return {"id": user["id"], "email": user["email"], "name": user["name"]}


async def get_current_user(request: Request):
    """FastAPI dependency that extracts and verifies the JWT from the cookie.
    Returns the user dict or raises 401."""
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated.")
    try:
        payload = jwt.decode(token, config.JWT_SECRET, algorithms=[ALGORITHM])
        user_id = int(payload["sub"])
    except (JWTError, KeyError, ValueError):
        raise HTTPException(status_code=401, detail="Invalid or expired token.")

    db_path = _get_db_path()
    user = await get_user_by_id(user_id, db_path)
    if not user:
        raise HTTPException(status_code=401, detail="User not found.")
    return {"id": user["id"], "email": user["email"], "name": user["name"]}


class LoginRequest(BaseModel):
    email: str
    password: str


@router.post("/login")
async def login(req: LoginRequest, response: Response):
    db_path = _get_db_path()
    user = await get_user_by_email(req.email, db_path)
    if not user or not pwd_context.verify(req.password, user["hashed_password"]):
        raise HTTPException(status_code=401, detail="Invalid email or password.")

    token = _create_token(user["id"])
    _set_cookie(response, token)
    return {"id": user["id"], "email": user["email"], "name": user["name"]}


@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie(key=COOKIE_NAME)
    return {"detail": "Logged out."}


@me_router.get("/api/me")
async def me(user: dict = Depends(get_current_user)):
    return user


# ---------------------------------------------------------------------------
# Password reset
# ---------------------------------------------------------------------------


def _create_reset_token(user_id):
    """Create a JWT reset token with purpose claim and 1-hour expiry."""
    expire = datetime.utcnow() + timedelta(hours=RESET_TOKEN_EXPIRE_HOURS)
    return jwt.encode(
        {"sub": str(user_id), "exp": expire, "purpose": "password_reset"},
        config.JWT_SECRET,
        algorithm=ALGORITHM,
    )


class ForgotPasswordRequest(BaseModel):
    email: str


@router.post("/forgot-password")
async def forgot_password(req: ForgotPasswordRequest):
    db_path = _get_db_path()
    user = await get_user_by_email(req.email, db_path)
    if user:
        token = _create_reset_token(user["id"])
        reset_link = "%s/reset-password?token=%s" % (FRONTEND_BASE_URL, token)
        send_email(
            to=user["email"],
            subject="Reset your Prism Data Vault password",
            body_html=(
                "<p>Hi %s,</p>"
                "<p>Click the link below to reset your password. This link expires in 1 hour.</p>"
                "<p><a href=\"%s\">Reset your password</a></p>"
                "<p>If you didn't request this, you can safely ignore this email.</p>"
            ) % (user["name"], reset_link),
        )
    # Always return 200 to prevent email enumeration
    return {"detail": "If an account exists with that email, we've sent a reset link."}


class ResetPasswordRequest(BaseModel):
    token: str
    password: str


@router.post("/reset-password")
async def reset_password(req: ResetPasswordRequest):
    # Verify token
    try:
        payload = jwt.decode(req.token, config.JWT_SECRET, algorithms=[ALGORITHM])
        if payload.get("purpose") != "password_reset":
            raise HTTPException(status_code=400, detail="Invalid reset token.")
        user_id = int(payload["sub"])
    except (JWTError, KeyError, ValueError):
        raise HTTPException(status_code=400, detail="Invalid or expired reset link.")

    # Validate password
    if len(req.password) < 8:
        raise HTTPException(status_code=422, detail="Password must be at least 8 characters.")

    # Update password
    db_path = _get_db_path()
    hashed = pwd_context.hash(req.password)
    await update_user_password(user_id, hashed, db_path)
    return {"detail": "Password reset successfully."}
