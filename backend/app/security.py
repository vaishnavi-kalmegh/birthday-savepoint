from __future__ import annotations

import hashlib
import hmac
import secrets

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

_hasher = PasswordHasher()  # Argon2id with the library's current recommended parameters

# Alphabet without look-alike characters, for passwords that a person has to read and type once.
_PASSWORD_ALPHABET = "abcdefghjkmnpqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ23456789"

_dummy_hash: str | None = None


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(stored_hash: str | None, password: str) -> bool:
    """Verify in roughly constant time, whether or not the account exists.

    Pass None for an unknown account: a dummy hash is verified so the response time does not
    reveal whether the account exists.
    """
    global _dummy_hash
    if stored_hash is None:
        if _dummy_hash is None:
            _dummy_hash = _hasher.hash(secrets.token_urlsafe(16))
        try:
            _hasher.verify(_dummy_hash, password)
        except VerificationError:
            pass
        return False
    try:
        return _hasher.verify(stored_hash, password)
    except (VerificationError, InvalidHashError):
        return False


def password_needs_rehash(stored_hash: str) -> bool:
    return _hasher.check_needs_rehash(stored_hash)


def generate_one_time_password() -> str:
    """16 random characters in four groups, roughly 90 bits of entropy."""
    groups = ["".join(secrets.choice(_PASSWORD_ALPHABET) for _ in range(4)) for _ in range(4)]
    return "-".join(groups)


def new_public_id() -> str:
    """Opaque identifier safe to expose. It is never a substitute for an authorization check."""
    return secrets.token_urlsafe(12)


def new_entry_slug() -> str:
    """Identifies an account on the personal entry link (128 bits). Does not authenticate."""
    return secrets.token_urlsafe(16)


def new_session_token() -> str:
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    """Only this hash is stored; the raw session token exists only in the user's cookie."""
    return hashlib.sha256(token.encode()).hexdigest()


def hash_lookup_key(kind: str, value: str) -> str:
    return hashlib.sha256(f"{kind}:{value}".encode()).hexdigest()


def csrf_token_for(session_token: str, secret_key: str) -> str:
    """CSRF token derived from the session token, so nothing extra is stored."""
    return hmac.new(secret_key.encode(), session_token.encode(), hashlib.sha256).hexdigest()


def tokens_match(a: str, b: str) -> bool:
    return hmac.compare_digest(a.encode(), b.encode())
