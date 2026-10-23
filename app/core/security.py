from datetime import datetime, timedelta, timezone

import jwt
from pwdlib import PasswordHash

from app.core.config import settings

password_hasher = PasswordHash.recommended()


def hash_password(plain_text: str) -> str:
    return password_hasher.hash(plain_text)


def verify_password(plain_text: str, hashed_password) -> bool:
    return password_hasher.verify(plain_text, hashed_password)


def create_access_token(user_id: int, tenant_id: int) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "tenant_id": tenant_id,
        "iat": now,
        "exp": now + timedelta(minutes=settings.access_token_expire_minutes),
    }

    return jwt.encode(payload, settings.signing_secret, algorithm="HS256")
