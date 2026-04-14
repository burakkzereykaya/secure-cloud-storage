
from fastapi import APIRouter,Depends,File as FastAPIFile, UploadFile, HTTPException
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.db.models.file import File
from app.db.models.user import User
from app.db.session import get_db
from app.schemas.file import  FileUploadResponse,FileMetadata

import uuid

from app.services.crypto_service import generate_dek, encrypt_file, decrypt_file
from app.services.storage_service import upload_encrypted_file, download_encrypted_file
from app.services.file_access_service import ensure_file_access

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

@router.get("/{file_id}/download")
def download_file(
        file_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user),
):
    file_record = db.query(File).filter(File.id == file_id).first()

    if not file_record:
        raise HTTPException(status_code=404,detail="File not found")

    ensure_file_access(file_record,current_user)

    if file_record.owner_id != current_user.id:
        raise HTTPException(status_code=403,detail="Not authorized")

    try:
        encrypted_data = download_encrypted_file(file_record.blob_path)

        dek = bytes(file_record.encrypted_dek)
        nonce = bytes(file_record.iv_or_nonce)


        decrypted_data = decrypt_file(
            encrypted_data,
            dek,
            nonce,
        )

        return Response(
            content=decrypted_data,
            media_type=file_record.content_type or "application/octet-stream",
            headers={
                "Content-Disposition": f'attachment; filename="{file_record.original_filename}"'
            },
        )

    except Exception as e:
        raise HTTPException(status_code=500,detail=f"Download failed: {str(e)}")


@router.get("/my-files", response_model=list[FileMetadata])
def list_my_files(
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user),
):
    files = (
        db.query(File)
        .filter(File.owner_id == current_user.id)
        .order_by(File.id.desc())
        .all()
    )
    return files