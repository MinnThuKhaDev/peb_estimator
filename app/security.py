"""
Auth helpers: password hashing (bcrypt), JWT session tokens, and TOTP 2FA.
Nothing here ever stores a plaintext password.
"""
import os
import time
from datetime import datetime, timedelta
from typing import Optional

import pyotp
from jose import jwt, JWTError
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Must be set in the environment in production. A random fallback is generated
# so local/dev runs still work, but it will invalidate sessions on restart.
JWT_SECRET = os.getenv("JWT_SECRET") or os.urandom(32).hex()
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "480"))  # 8 hours


def hash_password(plain: str) -> str:
    return pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(username: str, is_admin: bool) -> str:
    expire = datetime.utcnow() + timedelta(minutes=JWT_EXPIRE_MINUTES)
    payload = {"sub": username, "admin": is_admin, "exp": expire}
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> Optional[dict]:
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except JWTError:
        return None


# ---------------------------------------------------------------- 2FA (TOTP)
def new_totp_secret() -> str:
    return pyotp.random_base32()


def totp_provisioning_uri(secret: str, username: str, issuer: str = "PEB Estimator") -> str:
    return pyotp.totp.TOTP(secret).provisioning_uri(name=username, issuer_name=issuer)


def verify_totp(secret: str, code: str) -> bool:
    if not secret or not code:
        return False
    return pyotp.totp.TOTP(secret).verify(code, valid_window=1)
