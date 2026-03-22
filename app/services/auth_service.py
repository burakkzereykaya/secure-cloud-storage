from venv import create

from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.db.models.user import User
from app.core.security import hash_password, create_access_token,verify_password


def register_user(db: Session, email: str, password: str) -> User:
    #1.Does User exist in the database?
    existing_user = db.query(User).filter(User.email == email).first()


    if existing_user:
        raise HTTPException(
            status_code=400,
            detail="User already registered",
        )
    #2.password hashing
    hashed_password = hash_password(password)

    #3.Create User
    new_user = User(
        email=email,
        password_hash=hashed_password,
        role="user",
        is_active=True,
    )
    #4.Save to the Database
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return new_user


def login_user(db: Session, email: str,password: str) -> dict:
    user = db.query(User).filter(User.email == email).first()

    if not user:
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password",
        )
    if not verify_password(password,user.password_hash):
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=403,
            detail="User is inactive",
        )
    access_token = create_access_token(
        {
            "sub":str(user.id),
            "email":user.email,
            "role":user.role,
        }
    )
    return {"access_token":access_token,
            "token_type":"bearer",
            }