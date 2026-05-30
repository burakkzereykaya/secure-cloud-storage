from fastapi import Depends,HTTPException,status,Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.security import TokenExpiredError, TokenInvalidError, decode_access_token
from app.db.models.user import User
from app.db.session import get_db
from app.services.log_service import create_log

bearer_scheme = HTTPBearer(scheme_name="BearerAuth")

def get_current_user(
    request: Request,
    token: str | HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    access_token = token.credentials if isinstance(token, HTTPAuthorizationCredentials) else token

    # Invalid token
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    token_expired_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token expired",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = decode_access_token(access_token)
    except TokenExpiredError:
        create_log(
            db=db,
            action="TOKEN_INVALID",
            status="failure",
            ip_address=request.client.host if request.client else None,
            details="Expired access token",
        )
        raise token_expired_exception
    except TokenInvalidError:
        create_log(
            db=db,
            action="TOKEN_INVALID",
            status="failure",
            ip_address=request.client.host if request.client else None,
            details="Invalid access token",
        )
        raise credentials_exception

    user_id = payload.get("sub")
    if user_id is None:
        create_log(
            db=db,
            action="TOKEN_INVALID",
            status="failure",
            ip_address=request.client.host if request.client else None,
            details="Token missing subject",
        )
        raise credentials_exception

    try:
        user_id = int(user_id)
    except (TypeError, ValueError):
        create_log(
            db=db,
            action="TOKEN_INVALID",
            status="failure",
            ip_address=request.client.host if request.client else None,
            details="Token subject is invalid",
        )
        raise credentials_exception

    user = db.query(User).filter(User.id == user_id).first()

    if user is None:
        create_log(
            db=db,
            action="TOKEN_INVALID",
            status="failure",
            ip_address=request.client.host if request.client else None,
            details="Token subject user was not found",
        )
        raise credentials_exception

    if not user.is_active:
        create_log(
            db=db,
            user_id=user.id,
            action="UNAUTHORIZED_ACCESS",
            status="forbidden",
            ip_address=request.client.host if request.client else None,
            details="Inactive user attempted to access a protected endpoint",
        )
        raise HTTPException(
            status_code=403,
            detail="Inactive user",
        )

    return user

def get_current_admin(
        request: Request,
        current_user: User =Depends(get_current_user),
        db: Session = Depends(get_db),
)->User:
    if current_user.role != "admin":
        create_log(
            db=db,
            user_id=current_user.id,
            action="UNAUTHORIZED_ACCESS",
            status="forbidden",
            ip_address=request.client.host if request.client else None,
            details="User attempted to access an admin-only endpoint",
        )
        raise HTTPException(
            status_code =status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return current_user
