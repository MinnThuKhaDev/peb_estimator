from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel

from .database import SessionLocal
from .models import User
from . import security

router = APIRouter(prefix="/api/auth", tags=["auth"])
users_router = APIRouter(prefix="/api/users", tags=["users"])


# ---------------------------------------------------------------- schemas
class LoginRequest(BaseModel):
    username: str
    password: str
    totp_code: Optional[str] = None


class LoginResponse(BaseModel):
    token: Optional[str] = None
    requires_2fa: bool = False
    is_admin: bool = False


class TotpVerify(BaseModel):
    code: str


class CreateUserRequest(BaseModel):
    username: str
    password: str
    is_admin: bool = False


# ---------------------------------------------------------------- current-user dependency
def get_current_user(authorization: str = Header(default="")) -> User:
    if not authorization.startswith("Bearer "):
        raise HTTPException(401, "Not authenticated")
    token = authorization.split(" ", 1)[1]
    payload = security.decode_access_token(token)
    if not payload:
        raise HTTPException(401, "Invalid or expired session")
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == payload["sub"]).first()
        if not user:
            raise HTTPException(401, "User no longer exists")
        return user
    finally:
        db.close()


def require_admin(user: User = Depends(get_current_user)) -> User:
    if not user.is_admin:
        raise HTTPException(403, "Admin access required")
    return user


# ---------------------------------------------------------------- login / 2FA
@router.post("/login", response_model=LoginResponse)
def login(req: LoginRequest):
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == req.username).first()
        if not user or not security.verify_password(req.password, user.password_hash):
            raise HTTPException(401, "Incorrect username or password")

        if user.totp_enabled:
            if not req.totp_code:
                return LoginResponse(requires_2fa=True)
            if not security.verify_totp(user.totp_secret, req.totp_code):
                raise HTTPException(401, "Incorrect 2FA code")

        token = security.create_access_token(user.username, user.is_admin)
        return LoginResponse(token=token, is_admin=user.is_admin)
    finally:
        db.close()


@router.post("/2fa/setup")
def setup_2fa(user: User = Depends(get_current_user)):
    """Generates a new TOTP secret + QR provisioning URI. Not enabled until /2fa/enable."""
    db = SessionLocal()
    try:
        db_user = db.query(User).filter(User.username == user.username).first()
        secret = security.new_totp_secret()
        db_user.totp_secret = secret
        db_user.totp_enabled = False
        db.commit()
        uri = security.totp_provisioning_uri(secret, db_user.username)
        return {"secret": secret, "provisioning_uri": uri}
    finally:
        db.close()


@router.post("/2fa/enable")
def enable_2fa(body: TotpVerify, user: User = Depends(get_current_user)):
    db = SessionLocal()
    try:
        db_user = db.query(User).filter(User.username == user.username).first()
        if not db_user.totp_secret:
            raise HTTPException(400, "Call /2fa/setup first")
        if not security.verify_totp(db_user.totp_secret, body.code):
            raise HTTPException(401, "Incorrect code")
        db_user.totp_enabled = True
        db.commit()
        return {"ok": True}
    finally:
        db.close()


@router.post("/2fa/disable")
def disable_2fa(user: User = Depends(get_current_user)):
    db = SessionLocal()
    try:
        db_user = db.query(User).filter(User.username == user.username).first()
        db_user.totp_enabled = False
        db_user.totp_secret = None
        db.commit()
        return {"ok": True}
    finally:
        db.close()


# ---------------------------------------------------------------- admin-only user management
@users_router.get("")
def list_users(_: User = Depends(require_admin)):
    db = SessionLocal()
    try:
        users = db.query(User).all()
        return [
            {"id": u.id, "username": u.username, "is_admin": u.is_admin,
             "totp_enabled": u.totp_enabled, "created_at": u.created_at}
            for u in users
        ]
    finally:
        db.close()


@users_router.post("")
def create_user(req: CreateUserRequest, _: User = Depends(require_admin)):
    db = SessionLocal()
    try:
        if db.query(User).filter(User.username == req.username).first():
            raise HTTPException(409, "Username already exists")
        if len(req.password) < 8:
            raise HTTPException(400, "Password must be at least 8 characters")
        new_user = User(
            username=req.username,
            password_hash=security.hash_password(req.password),
            is_admin=req.is_admin,
        )
        db.add(new_user)
        db.commit()
        return {"ok": True, "username": new_user.username}
    finally:
        db.close()


@users_router.delete("/{user_id}")
def delete_user(user_id: int, admin: User = Depends(require_admin)):
    db = SessionLocal()
    try:
        target = db.get(User, user_id)
        if not target:
            raise HTTPException(404, "User not found")
        if target.username == admin.username:
            raise HTTPException(400, "You can't delete your own account while logged in as it")
        db.delete(target)
        db.commit()
        return {"ok": True}
    finally:
        db.close()
