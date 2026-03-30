from sqlalchemy import Column, DateTime, ForeignKey, Integer, LargeBinary ,String
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.db.base import Base

class File(Base):
    __tablename__ = 'files'

    id=Column(Integer, primary_key=True,index=True)
    owner_id = Column(Integer, ForeignKey('users.id'),nullable=False,index=True)
    original_filename = Column(String,nullable=False)
    blob_path = Column(String,nullable=False,unique=True)
    size = Column(Integer,nullable=False)
    content_type = Column(String,nullable=False)
    encrypted_dek = Column(LargeBinary,nullable=False)
    iv_or_nonce = Column(LargeBinary,nullable=False)
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now(),nullable=False)
    status = Column(String,nullable=False,default="uploaded")

    owner = relationship("User", back_populates="files")
    access_logs = relationship("AccessLog", back_populates="file")