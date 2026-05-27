from sqlalchemy.orm import Session

from app.db.models.file import File


def upload_file(
    db: Session,
    owner_id: int,
    original_filename: str,
    blob_path: str,
    size: int,
    content_type: str,
    sha256_hash: str,
    encrypted_dek: bytes,
    iv_or_nonce: bytes,
) -> File:
    file_record = File(
        owner_id=owner_id,
        original_filename=original_filename,
        blob_path=blob_path,
        size=size,
        content_type=content_type,
        sha256_hash=sha256_hash,
        encrypted_dek=encrypted_dek,
        iv_or_nonce=iv_or_nonce,
        status="uploaded",
    )
    db.add(file_record)
    db.commit()
    db.refresh(file_record)
    return file_record


def download_file(db: Session, file_id: int) -> File | None:
    return db.query(File).filter(File.id == file_id).first()
