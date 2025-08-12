from __future__ import annotations

import time
from typing import Tuple

from fastapi import HTTPException, Request, status

from .config import get_settings


_window_counts: dict[Tuple[str, str, int], int] = {}


def rate_limit_check(request: Request, token: str) -> None:
    settings = get_settings()
    if not settings.rate_limit_enabled:
        return
    ip = request.client.host if request.client else "unknown"
    minute = int(time.time() // 60)
    key = (token, ip, minute)
    count = _window_counts.get(key, 0) + 1
    _window_counts[key] = count
    if count > settings.rate_limit_per_minute:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Rate limit exceeded")


