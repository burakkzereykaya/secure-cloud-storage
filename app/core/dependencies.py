from fastapi import Depends,HTTPException,status,Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.security import decode_access_token
from app.db.models.user import User
from app.db.session import get_db
from app.services.log_service import create_log

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    # Invalid token
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    payload = decode_access_token(token)
    if payload is None:
        raise credentials_exception

    user_id = payload.get("sub")
    if user_id is None:
        raise credentials_exception

    try:
        user_id = int(user_id)
    except (TypeError, ValueError):
        raise credentials_exception

    user = db.query(User).filter(User.id == user_id).first()

    if user is None:
        raise credentials_exception

    if not user.is_active:
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
            action="UNAUTHORIZED ACCESS",
            status="forbidden",
            ip_address=request.client.host if request.client.host else None,
            details="User attempted to access an admin-only endpoint",
        )
        raise HTTPException(
            status_code =status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return current_user