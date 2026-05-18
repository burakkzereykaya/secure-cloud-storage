from fastapi import APIRouter,Depends,Request,HTTPException
from sqlalchemy.orm import Session

from app.db.models import User
from app.db.session import get_db
from app.schemas.auth import TokenResponse,LoginRequest
from app.schemas.user import UserCreate,UserResponse
from app.services.auth_service import login_user,register_user
from app.services.log_service import create_log

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register",response_model=UserResponse)
def register(user:UserCreate,db:Session = Depends(get_db)):
    new_user = register_user(
        db=db,
        email=user.email,
        password=user.password
    )
    return new_user


@router.post("/login",response_model=TokenResponse)
def login(request: Request,user:LoginRequest,db:Session = Depends(get_db)):

    ip_address=request.client.host if request.client else None

    try:
        token_response = login_user(
            db=db,
            email=user.email,
            password=user.password,
        )

        logged_in_user=db.query(User).filter(User.email==user.email).first()

        create_log(
            db=db,
            user_id=logged_in_user.id if logged_in_user else None,
            action="LOGIN_SUCCESS",
            status="success",
            ip_address=ip_address,
            details=f"Successful login for email: {user.email}",
        )

        return token_response
    except HTTPException:
        create_log(
            db=db,
            user_id=None,
            action="LOGIN_FAILED",
            status="failure",
            ip_address=ip_address,
            details=f"Failed login attempt for email: {user.email}",
        )
        raise