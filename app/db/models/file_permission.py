from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.base import Base


class FilePermission(Base):
    __tablename__ = "file_permissions"

    id = Column(Integer, primary_key=True, index=True)
    file_id = Column(Integer, ForeignKey("files.id"), nullable=False, index=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    shared_with_user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    permission_type = Column(String, nullable=False, default="read")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)

    file = relationship("File", back_populates="permissions")
    owner = relationship("User", foreign_keys=[owner_id], back_populates="owned_file_permissions")
    shared_with_user = relationship(
        "User",
        foreign_keys=[shared_with_user_id],
        back_populates="shared_file_permissions",
    )
