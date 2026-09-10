"""
Field-level encryption for sensitive text stored in the database (customer
names, notes, etc.). This is on top of the transport encryption (HTTPS/TLS)
and at-rest encryption your cloud database provider already does — this
layer means even someone with raw DB access can't read these fields without
the ENCRYPTION_KEY, which lives only in your server's environment variables,
never in the database itself.
"""
import os
from cryptography.fernet import Fernet, InvalidToken

_KEY = os.getenv("ENCRYPTION_KEY")
_fernet: Fernet | None = None

if _KEY:
    try:
        _fernet = Fernet(_KEY.encode())
    except Exception:
        _fernet = None


def encrypt_text(value: str | None) -> str | None:
    if value is None or value == "":
        return value
    if not _fernet:
        return value  # no key configured (e.g. local dev) -> store as-is
    return _fernet.encrypt(value.encode()).decode()


def decrypt_text(value: str | None) -> str | None:
    if value is None or value == "":
        return value
    if not _fernet:
        return value
    try:
        return _fernet.decrypt(value.encode()).decode()
    except (InvalidToken, ValueError):
        # value wasn't encrypted (e.g. created before ENCRYPTION_KEY was set)
        return value


def generate_key() -> str:
    """Run once to produce a key for ENCRYPTION_KEY. Keep it secret."""
    return Fernet.generate_key().decode()
