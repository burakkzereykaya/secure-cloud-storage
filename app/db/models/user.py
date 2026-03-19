from sqlalchemy import Boolean,Column,DateTime,Integer,String
from sqlalchemy.sql import func

from app.db.base import Base

class User(Base):
    __tablename__ = 'user'

    id = Column(Integer,primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    role = Column(String, nullable=False, default='user')
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
