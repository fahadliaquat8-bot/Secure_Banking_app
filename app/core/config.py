import os
from typing import List

from dotenv import load_dotenv

load_dotenv()


def get_required_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"{name} is required")
    return value


def get_int_env(name: str, default: int, min_value: int | None = None) -> int:
    raw = os.getenv(name)
    value = int(raw) if raw is not None else default
    if min_value is not None and value < min_value:
        raise RuntimeError(f"{name} must be >= {min_value}")
    return value


def get_list_env(name: str, default: List[str] | None = None) -> List[str]:
    raw = os.getenv(name)
    if raw is None:
        return list(default) if default is not None else []
    return [item.strip() for item in raw.split(",") if item.strip()]
