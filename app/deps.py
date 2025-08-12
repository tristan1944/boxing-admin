from __future__ import annotations

from typing import Optional

from fastapi import Depends, Header, HTTPException, status, Request
from sqlalchemy.orm import Session

from .config import get_settings
from .database import get_db_session
from .rate_limit import rate_limit_check


def get_db() -> Session:
    yield from get_db_session()


def require_token(request: Request, authorization: Optional[str] = Header(default=None)) -> str:
    settings = get_settings()
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token")
    token = authorization.split(" ", 1)[1].strip()
    if token != settings.api_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    # Rate limit per token + IP (if enabled)
    rate_limit_check(request, token)
    return token


