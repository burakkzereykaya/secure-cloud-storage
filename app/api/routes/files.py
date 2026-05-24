
from fastapi import APIRouter,Depends,File as FastAPIFile, UploadFile, HTTPException,Request
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.core.rate_limit import limiter
from app.services.log_service import create_log
from app.db.models.file import File
from app.db.models.user import User
from app.db.session import get_db
from app.schemas.file import  FileUploadResponse,FileMetadata


import uuid
from urllib.parse import quote

from app.services.crypto_service import generate_dek, encrypt_file, decrypt_file
from app.services.storage_service import upload_encrypted_file, download_encrypted_file
from app.services.file_access_service import ensure_file_access

router = APIRouter(prefix="/files", tags=["files"])

#max file size (örnek: 5MB)
MAX_FILE_SIZE = 10 * 1024 * 1024

#allowed content types
ALLOWED_TYPES = {"image/png", "image/jpeg", "application/pdf", "text/plain"}

@router.post("/upload",response_model=FileUploadResponse)
@limiter.limit("10/minute")
async def upload_file(
    request: Request,
    file: UploadFile = FastAPIFile(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not file.filename:
        raise HTTPException(status_code=400,detail="File name is required")

    if file.content_type not in ALLOWED_TYPES:
        create_log(
            db=db,
            user_id=current_user.id,
            action="INVALID_FILE_TYPE",
            status="failure",
            ip_address=request.client.host if request.client else None,
            details=f"Rejected upload with content type: {file.content_type}",
        )
        raise HTTPException(status_code=400,detail="Invalid file type")

    #read
    contents = await file.read(MAX_FILE_SIZE + 1)

    if not contents:
        raise HTTPException(status_code=400,detail="File is empty")

    #size
    if len(contents) > MAX_FILE_SIZE:
        create_log(
            db=db,
            user_id=current_user.id,
            action="FILE_TOO_LARGE",
            status="failure",
            ip_address=request.client.host if request.client else None,
            details=f"Rejected upload larger than {MAX_FILE_SIZE} bytes",
        )
        raise HTTPException(status_code=413,detail="Payload too large")

    #METADATA
    filename = file.filename
    size = len(contents)
    content_type = file.content_type

    dek=generate_dek()
    encrypted_data,iv_or_nonce = encrypt_file(contents,dek)

    uuid_filename = f"{uuid.uuid4()}.enc"
    blob_path = f"uploads/{current_user.id}/{uuid_filename}"

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

    create_log(
        db=db,
        user_id=current_user.id,
        file_id=new_file.id,
        action="UPLOAD_SUCCESS",
        status="success",
        ip_address=request.client.host if request.client else None,
        details=f"Uploaded file: {new_file.original_filename}",
    )


    return FileUploadResponse(
        id=new_file.id,
        filename=file.filename,
        size=new_file.size,
        uploaded_at=new_file.uploaded_at,
        message=f"Authenticated upload request accepted for user {current_user.email}"
    )

@router.get("/{file_id}/download")
@limiter.limit("20/minute")
def download_file(
        request: Request,
        file_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user),
):
    file_record = db.query(File).filter(File.id == file_id).first()

    if not file_record:
        create_log(
            db=db,
            user_id=current_user.id,
            file_id=file_id,
            action="DOWNLOAD_FAILED",
            status="failed",
            ip_address=request.client.host if request.client else None,
            details=f"File not found during download attempt",
        )
        raise HTTPException(status_code=404,detail="File not found")

    try:
        ensure_file_access(file_record,current_user)
    except HTTPException:
        create_log(
            db=db,
            user_id=current_user.id,
            file_id=file_record.id,
            action="UNAUTHORIZED_ACCESS",
            status="forbidden",
            ip_address=request.client.host if request.client else None,
            details="User attempted to download a file owned by another user",
        )
        raise

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

        create_log(
            db=db,
            user_id=current_user.id,
            file_id=file_record.id,
            action="DOWNLOAD_SUCCESS",
            status="success",
            ip_address=request.client.host if request.client else None,
            details=f"Downloaded file: {file_record.original_filename}",
        )


        safe_download_name = quote(file_record.original_filename or "download", safe="")

        return Response(
            content=decrypted_data,
            media_type=file_record.content_type or "application/octet-stream",
            headers={
                "Content-Disposition": f"attachment; filename*=UTF-8''{safe_download_name}"
            },
        )

    except Exception:
        create_log(
            db=db,
            user_id=current_user.id,
            file_id=file_record.id,
            action="DOWNLOAD_FAILED",
            status="failure",
            ip_address=request.client.host if request.client else None,
            details="Unexpected error during file download",
        )
        raise HTTPException(status_code=500,detail="An unexpected error occurred")


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

@router.get("/{file_id}", response_model=FileMetadata)
def get_file_detail(
        request: Request,
        file_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user),
):
    file_record = db.query(File).filter(File.id == file_id).first()

    if not file_record:
        create_log(
            db=db,
            user_id=current_user.id,
            file_id=file_id,
            action="METADATA_VIEW_FAILED",
            status="failed",
            ip_address=request.client.host if request.client else None,
            details="File metadata requested but file was not found",
        )
        raise HTTPException(status_code=404,detail="File not found")
    try:
        ensure_file_access(file_record,current_user)
    except HTTPException:
        create_log(
            db=db,
            user_id=current_user.id,
            file_id=file_record.id,
            action="UNAUTHORIZED_ACCESS",
            status="forbidden",
            ip_address=request.client.host if request.client else None,
            details="User attempted to view metadata of another user's file",
        )
        raise
    create_log(
        db=db,
        user_id=current_user.id,
        file_id=file_record.id,
        action="METADATA_VIEWED",
        status="success",
        ip_address=request.client.host if request.client else None,
        details=f"Viewed metadata for file: {file_record.original_filename}",
    )

    return file_record
