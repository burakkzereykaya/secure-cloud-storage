from sqlalchemy.orm import Session

from app.db.models.user import User


def register_user(db: Session, email: str, password_hash: str) -> User:
    user = User(
        email=email,
        password_hash=password_hash,
        role="user",
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def login_user(db: Session, email: str):
    user = db.query(User).filter(User.email == email).first()
    return user