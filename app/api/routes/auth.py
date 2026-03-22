from fastapi import APIRouter,Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.auth import TokenResponse,LoginRequest
from app.schemas.user import UserCreate,UserResponse
from app.services.auth_service import login_user,register_user

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
def login(user:LoginRequest,db:Session = Depends(get_db)):
    return login_user(
        db=db,
        email=user.email,
        password=user.password
    )