
from fastapi import APIRouter,Depends,File as FastAPIFile, UploadFile, HTTPException
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.db.models.file import File
from app.db.models.user import User
from app.db.session import get_db
from app.schemas.file import  FileUploadResponse

import uuid

from app.services.crypto_service import generate_dek, encrypt_file
from app.services.storage_service import upload_encrypted_file

router = APIRouter(prefix="/files", tags=["files"])

#max file size (örnek: 5MB)
MAX_FILE_SIZE = 1024 * 1024 * 5

#allowed content types
ALLOWED_TYPES = ["image/png","image/jpeg","application/pdf"]

@router.post("/upload",response_model=FileUploadResponse)
async def upload_file(
    file: UploadFile = FastAPIFile(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not file.filename:
        raise HTTPException(status_code=400,detail="File name is required")

    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(status_code=400,detail=f"File type is not supported {file.content_type}")

    #read
    contents= await file.read()

    if not contents:
        raise HTTPException(status_code=400,detail="File is empty")

    #size
    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400,detail="File is too big to upload")

    #METADATA
    filename = file.filename
    size = len(contents)
    content_type = file.content_type

    dek=generate_dek()
    encrypted_data,iv_or_nonce = encrypt_file(contents,dek)

    #placeholders for now
    unique_id = uuid.uuid4()
    blob_path =f"uploads/{current_user.id}/{unique_id}.enc"

    upload_encrypted_file(encrypted_data,blob_path)

    new_file = File(
        owner_id=current_user.id,
        original_filename=filename,
        size=size,
        content_type=content_type,
        blob_path=blob_path,
        encrypted_dek=dek, #şu anlik plain dek
        iv_or_nonce=iv_or_nonce,
        status="encrypted"
    )

    db.add(new_file)
    db.commit()
    db.refresh(new_file)

    return FileUploadResponse(
        id=new_file.id,
        filename=file.filename,
        size=new_file.size,
        uploaded_at=new_file.uploaded_at,
        message=f"Authenticated upload request accepted for user {current_user.email}"
    )

@router.get("/download")
def download_file():
    return {"message": "Download endpoint placeholder"}