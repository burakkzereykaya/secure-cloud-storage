from sqlalchemy import Column,DateTime,ForeignKey,Integer,String
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.db.base import Base

class AccessLog(Base):
    __tablename__ = "access_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    file_id = Column(Integer, ForeignKey("files.id"), nullable=False, index=True)
    action = Column(String, nullable=False)
    status = Column(String, nullable=False)
    ip_address = Column(String, nullable=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user = relationship("User", back_populates="access_logs")
    file = relationship("File", back_populates="access_logs")