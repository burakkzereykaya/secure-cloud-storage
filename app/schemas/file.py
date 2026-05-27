from pydantic import BaseModel, ConfigDict
from pydantic import EmailStr, Field
from datetime import datetime


class FileUploadResponse(BaseModel):
    id: int
    filename: str
    # blob_path: str
    # status: str
    # message: str
    uploaded_at: datetime
    size: int

    model_config = ConfigDict(from_attributes=True)


class FileMetadata(BaseModel):
    id: int
    owner_id: int
    original_filename: str
    blob_path: str
    size: int
    content_type: str | None
    uploaded_at: datetime
    status: str

    model_config = ConfigDict(from_attributes=True)


class ShareFileRequest(BaseModel):
    shared_with_email: EmailStr
    permission_type: str = "read"


class FileShareResponse(BaseModel):
    id: int
    file_id: int
    owner_id: int
    shared_with_user_id: int
    permission_type: str
    created_at: datetime
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


class ShareLinkCreateRequest(BaseModel):
    expires_in_minutes: int = Field(gt=0, le=10080)


class ShareLinkResponse(BaseModel):
    id: int
    file_id: int
    token: str
    expires_at: datetime
    is_active: bool

    model_config = ConfigDict(from_attributes=True)
