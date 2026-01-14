import os
from datetime import datetime, timedelta
from typing import Optional

from fastapi.security import APIKeyHeader
from jose import jwt
from passlib.context import CryptContext

from app.core.config import get_int_env, get_required_env

SECRET_KEY = get_required_env("SECRET_KEY")
ALGORITHM = get_required_env("ALGORITHM") if "ALGORITHM" in os.environ else "HS256"
if ALGORITHM not in {"HS256", "HS384", "HS512"}:
    raise RuntimeError("ALGORITHM must be one of: HS256, HS384, HS512")
ACCESS_TOKEN_EXPIRE_MINUTES = get_int_env("ACCESS_TOKEN_EXPIRE_MINUTES", 60, min_value=1)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Token extraction header (works for swagger + manual Bearer)
oauth2_scheme = APIKeyHeader(name="Authorization", auto_error=False)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    now = datetime.utcnow()
    expire = now + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"iat": now})
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
