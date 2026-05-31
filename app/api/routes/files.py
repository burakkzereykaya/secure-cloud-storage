from datetime import datetime, timedelta, timezone
import logging
import secrets
import uuid
from urllib.parse import quote

from fastapi import APIRouter, Depends, File as FastAPIFile, HTTPException, Request, UploadFile
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.core.rate_limit import limiter
from app.db.models.file import File
from app.db.models.file_permission import FilePermission
from app.db.models.share_link import ShareLink
from app.db.models.user import User
from app.db.session import get_db
from app.schemas.file import (
    FileMetadata,
    FileShareResponse,
    FileUploadResponse,
    RevokeShareRequest,
    ShareFileRequest,
    ShareLinkCreateRequest,
    ShareLinkResponse,
)
from app.services.crypto_service import decrypt_file, encrypt_file, generate_dek
from app.services.file_access_service import ensure_file_access, ensure_file_owner_or_admin
from app.services.hash_service import calculate_sha256
from app.services.log_service import create_log
from app.services.storage_service import download_encrypted_file, upload_encrypted_file

router = APIRouter(prefix="/files", tags=["files"])
share_router = APIRouter(prefix="/share", tags=["share-links"])
logger = logging.getLogger(__name__)

# max file size: 10MB
MAX_FILE_SIZE = 10 * 1024 * 1024

# allowed content types
ALLOWED_TYPES = {"image/png", "image/jpeg", "application/pdf", "text/plain"}
SUPPORTED_PERMISSION_TYPES = {"read"}


def _client_ip(request: Request) -> str | None:
    return request.client.host if request.client else None


def _is_expired(expires_at: datetime) -> bool:
    now = datetime.now(timezone.utc)
    if expires_at.tzinfo is None:
        now = now.replace(tzinfo=None)
    return expires_at <= now


def _download_response(file_record: File, decrypted_data: bytes) -> Response:
    safe_download_name = quote(file_record.original_filename or "download", safe="")
    return Response(
        content=decrypted_data,
        media_type=file_record.content_type or "application/octet-stream",
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{safe_download_name}"
        },
    )


def _decrypt_and_verify_file(
    db: Session,
    request: Request,
    file_record: File,
    user_id: int | None,
) -> bytes:
    if not file_record.sha256_hash:
        create_log(
            db=db,
            user_id=user_id,
            file_id=file_record.id,
            action="INTEGRITY_CHECK_FAILED",
            status="failure",
            ip_address=_client_ip(request),
            details="File integrity hash is missing",
        )
        raise HTTPException(status_code=409, detail="INTEGRITY_CHECK_FAILED")

    try:
        encrypted_data = download_encrypted_file(file_record.blob_path)
        decrypted_data = decrypt_file(
            encrypted_data,
            bytes(file_record.encrypted_dek),
            bytes(file_record.iv_or_nonce),
        )
    except Exception:
        create_log(
            db=db,
            user_id=user_id,
            file_id=file_record.id,
            action="INTEGRITY_CHECK_FAILED",
            status="failure",
            ip_address=_client_ip(request),
            details="Encrypted blob could not be decrypted or verified",
        )
        raise HTTPException(status_code=409, detail="INTEGRITY_CHECK_FAILED")

    if calculate_sha256(decrypted_data) != file_record.sha256_hash:
        create_log(
            db=db,
            user_id=user_id,
            file_id=file_record.id,
            action="INTEGRITY_CHECK_FAILED",
            status="failure",
            ip_address=_client_ip(request),
            details="Decrypted file hash does not match stored hash",
        )
        raise HTTPException(status_code=409, detail="INTEGRITY_CHECK_FAILED")

    create_log(
        db=db,
        user_id=user_id,
        file_id=file_record.id,
        action="INTEGRITY_CHECK_SUCCESS",
        status="success",
        ip_address=_client_ip(request),
        details="Decrypted file hash matches stored hash",
    )
    return decrypted_data


@router.post("/upload", response_model=FileUploadResponse)
@limiter.limit("10/minute")
async def upload_file(
    request: Request,
    file: UploadFile = FastAPIFile(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not file.filename:
        raise HTTPException(status_code=400, detail="File name is required")

    if file.content_type not in ALLOWED_TYPES:
        create_log(
            db=db,
            user_id=current_user.id,
            action="INVALID_FILE_TYPE",
            status="failure",
            ip_address=_client_ip(request),
            details=f"Rejected upload with content type: {file.content_type}",
        )
        raise HTTPException(status_code=400, detail="Invalid file type")

    contents = await file.read(MAX_FILE_SIZE + 1)

    if not contents:
        raise HTTPException(status_code=400, detail="File is empty")

    if len(contents) > MAX_FILE_SIZE:
        create_log(
            db=db,
            user_id=current_user.id,
            action="FILE_TOO_LARGE",
            status="failure",
            ip_address=_client_ip(request),
            details=f"Rejected upload larger than {MAX_FILE_SIZE} bytes",
        )
        raise HTTPException(status_code=413, detail="Payload too large")

    filename = file.filename
    size = len(contents)
    content_type = file.content_type
    sha256_hash = calculate_sha256(contents)

    dek = generate_dek()
    encrypted_data, iv_or_nonce = encrypt_file(contents, dek)

    uuid_filename = f"{uuid.uuid4()}.enc"
    blob_path = f"uploads/{current_user.id}/{uuid_filename}"

    try:
        upload_encrypted_file(encrypted_data, blob_path)
    except Exception:
        logger.exception("Azure Blob upload failed for blob_path=%s", blob_path)
        create_log(
            db=db,
            user_id=current_user.id,
            action="UPLOAD_FAILED",
            status="failure",
            ip_address=_client_ip(request),
            details="Azure Blob upload failed",
        )
        raise HTTPException(status_code=502, detail="Azure Blob upload failed")

    new_file = File(
        owner_id=current_user.id,
        original_filename=filename,
        size=size,
        content_type=content_type,
        sha256_hash=sha256_hash,
        blob_path=blob_path,
        encrypted_dek=dek,
        iv_or_nonce=iv_or_nonce,
        status="encrypted",
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
        ip_address=_client_ip(request),
        details=f"Uploaded file: {new_file.original_filename}",
    )

    return FileUploadResponse(
        id=new_file.id,
        filename=file.filename,
        size=new_file.size,
        uploaded_at=new_file.uploaded_at,
        message=f"Authenticated upload request accepted for user {current_user.email}",
    )


@router.get("/my-files", response_model=list[FileMetadata])
def list_my_files(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return (
        db.query(File)
        .filter(File.owner_id == current_user.id)
        .order_by(File.id.desc())
        .all()
    )


@router.get("/shared-with-me", response_model=list[FileMetadata])
def list_shared_with_me(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return (
        db.query(File)
        .join(FilePermission, FilePermission.file_id == File.id)
        .filter(
            FilePermission.shared_with_user_id == current_user.id,
            FilePermission.is_active.is_(True),
        )
        .order_by(FilePermission.id.desc())
        .all()
    )


@router.post("/{file_id}/share", response_model=FileShareResponse)
def share_file(
    request: Request,
    file_id: int,
    payload: ShareFileRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if payload.permission_type not in SUPPORTED_PERMISSION_TYPES:
        raise HTTPException(status_code=400, detail="Unsupported permission type")

    file_record = db.query(File).filter(File.id == file_id).first()
    if not file_record:
        raise HTTPException(status_code=404, detail="File not found")

    ensure_file_owner_or_admin(file_record, current_user)

    shared_user = db.query(User).filter(User.email == payload.shared_with_email).first()
    if not shared_user:
        raise HTTPException(status_code=404, detail="User not found")

    if shared_user.id == file_record.owner_id:
        raise HTTPException(status_code=400, detail="File owner already has access")

    existing_permission = (
        db.query(FilePermission)
        .filter(
            FilePermission.file_id == file_record.id,
            FilePermission.shared_with_user_id == shared_user.id,
            FilePermission.is_active.is_(True),
        )
        .first()
    )
    if existing_permission:
        raise HTTPException(status_code=400, detail="File is already shared with this user")

    permission = FilePermission(
        file_id=file_record.id,
        owner_id=file_record.owner_id,
        shared_with_user_id=shared_user.id,
        permission_type=payload.permission_type,
        is_active=True,
    )
    db.add(permission)
    db.commit()
    db.refresh(permission)

    create_log(
        db=db,
        user_id=current_user.id,
        file_id=file_record.id,
        action="FILE_SHARED",
        status="success",
        ip_address=_client_ip(request),
        details=f"Shared file with user_id={shared_user.id}",
    )

    return permission


def _revoke_file_share_for_user(
    request: Request,
    file_record: File,
    shared_with_user_id: int,
    db: Session,
    current_user: User,
):
    permission = (
        db.query(FilePermission)
        .filter(
            FilePermission.file_id == file_record.id,
            FilePermission.shared_with_user_id == shared_with_user_id,
            FilePermission.is_active.is_(True),
        )
        .first()
    )
    if not permission:
        raise HTTPException(status_code=404, detail="Active file share not found")

    permission.is_active = False
    db.commit()

    create_log(
        db=db,
        user_id=current_user.id,
        file_id=file_record.id,
        action="FILE_SHARE_REVOKED",
        status="success",
        ip_address=_client_ip(request),
        details=f"Revoked file share for user_id={shared_with_user_id}",
    )

    return {"message": "File share revoked"}


@router.delete("/{file_id}/share")
def revoke_file_share_by_email(
    request: Request,
    file_id: int,
    payload: RevokeShareRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    file_record = db.query(File).filter(File.id == file_id).first()
    if not file_record:
        raise HTTPException(status_code=404, detail="File not found")

    ensure_file_owner_or_admin(file_record, current_user)

    shared_user = db.query(User).filter(User.email == payload.shared_with_email).first()
    if not shared_user:
        raise HTTPException(status_code=404, detail="User not found")

    return _revoke_file_share_for_user(
        request,
        file_record,
        shared_user.id,
        db,
        current_user,
    )


@router.delete("/{file_id}/share/{user_id}")
def revoke_file_share(
    request: Request,
    file_id: int,
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    file_record = db.query(File).filter(File.id == file_id).first()
    if not file_record:
        raise HTTPException(status_code=404, detail="File not found")

    ensure_file_owner_or_admin(file_record, current_user)

    return _revoke_file_share_for_user(
        request,
        file_record,
        user_id,
        db,
        current_user,
    )


@router.post("/{file_id}/share-link", response_model=ShareLinkResponse)
def create_share_link(
    request: Request,
    file_id: int,
    payload: ShareLinkCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    file_record = db.query(File).filter(File.id == file_id).first()
    if not file_record:
        raise HTTPException(status_code=404, detail="File not found")

    ensure_file_owner_or_admin(file_record, current_user)

    share_link = ShareLink(
        file_id=file_record.id,
        created_by_user_id=current_user.id,
        token=secrets.token_urlsafe(32),
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=payload.expires_in_minutes),
        is_active=True,
    )
    db.add(share_link)
    db.commit()
    db.refresh(share_link)

    create_log(
        db=db,
        user_id=current_user.id,
        file_id=file_record.id,
        action="SHARE_LINK_CREATED",
        status="success",
        ip_address=_client_ip(request),
        details=f"Created expiring download link id={share_link.id}",
    )

    return share_link


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
            ip_address=_client_ip(request),
            details="File not found during download attempt",
        )
        raise HTTPException(status_code=404, detail="File not found")

    try:
        ensure_file_access(file_record, current_user, db)
    except HTTPException:
        create_log(
            db=db,
            user_id=current_user.id,
            file_id=file_record.id,
            action="UNAUTHORIZED_ACCESS",
            status="forbidden",
            ip_address=_client_ip(request),
            details="User attempted to download a file without access",
        )
        raise

    decrypted_data = _decrypt_and_verify_file(db, request, file_record, current_user.id)

    create_log(
        db=db,
        user_id=current_user.id,
        file_id=file_record.id,
        action="DOWNLOAD_SUCCESS",
        status="success",
        ip_address=_client_ip(request),
        details=f"Downloaded file: {file_record.original_filename}",
    )

    return _download_response(file_record, decrypted_data)


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
            ip_address=_client_ip(request),
            details="File metadata requested but file was not found",
        )
        raise HTTPException(status_code=404, detail="File not found")

    try:
        ensure_file_access(file_record, current_user, db)
    except HTTPException:
        create_log(
            db=db,
            user_id=current_user.id,
            file_id=file_record.id,
            action="UNAUTHORIZED_ACCESS",
            status="forbidden",
            ip_address=_client_ip(request),
            details="User attempted to view metadata for a file without access",
        )
        raise

    create_log(
        db=db,
        user_id=current_user.id,
        file_id=file_record.id,
        action="METADATA_VIEWED",
        status="success",
        ip_address=_client_ip(request),
        details=f"Viewed metadata for file: {file_record.original_filename}",
    )

    return file_record


@share_router.get("/{token}/download")
def download_file_with_share_link(
    request: Request,
    token: str,
    db: Session = Depends(get_db),
):
    share_link = db.query(ShareLink).filter(ShareLink.token == token).first()
    if not share_link:
        raise HTTPException(status_code=404, detail="Share link not found")

    if not share_link.is_active:
        raise HTTPException(status_code=404, detail="Share link not found")

    if _is_expired(share_link.expires_at):
        share_link.is_active = False
        db.commit()
        create_log(
            db=db,
            user_id=share_link.created_by_user_id,
            file_id=share_link.file_id,
            action="SHARE_LINK_EXPIRED",
            status="failure",
            ip_address=_client_ip(request),
            details=f"Expired share link id={share_link.id} was used",
        )
        raise HTTPException(status_code=410, detail="Share link expired")

    file_record = db.query(File).filter(File.id == share_link.file_id).first()
    if not file_record:
        raise HTTPException(status_code=404, detail="File not found")

    decrypted_data = _decrypt_and_verify_file(
        db,
        request,
        file_record,
        share_link.created_by_user_id,
    )

    create_log(
        db=db,
        user_id=share_link.created_by_user_id,
        file_id=file_record.id,
        action="SHARE_LINK_USED",
        status="success",
        ip_address=_client_ip(request),
        details=f"Share link id={share_link.id} used",
    )

    return _download_response(file_record, decrypted_data)
