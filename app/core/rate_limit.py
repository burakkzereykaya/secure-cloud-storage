from fastapi import Request
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.db.session import SessionLocal
from app.services.log_service import create_log

limiter = Limiter(key_func=get_remote_address)


async def rate_limit_exceeded_handler(
    request: Request,
    exc: RateLimitExceeded,
) -> JSONResponse:
    db = SessionLocal()
    try:
        create_log(
            db=db,
            action="RATE_LIMIT_EXCEEDED",
            status="failure",
            ip_address=request.client.host if request.client else None,
            details=f"Rate limit exceeded for {request.url.path}",
        )
    finally:
        db.close()

    return JSONResponse(
        status_code=429,
        content={"detail": "Too many requests"},
    )
