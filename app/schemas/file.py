from pydantic import BaseModel, ConfigDict
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
    content_type: str
    uploaded_at: datetime
    status: str

    model_config = ConfigDict(from_attributes=True)