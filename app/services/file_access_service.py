from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.db.models.file import File
from app.db.models.file_permission import FilePermission
from app.db.models.user import User


def has_file_access(file_record: File, current_user: User, db: Session) -> bool:
    if current_user.role == "admin":
        return True

    if file_record.owner_id == current_user.id:
        return True

    permission = (
        db.query(FilePermission)
        .filter(
            FilePermission.file_id == file_record.id,
            FilePermission.shared_with_user_id == current_user.id,
            FilePermission.is_active.is_(True),
        )
        .first()
    )
    return permission is not None


def ensure_file_access(file_record: File, current_user: User, db: Session) -> None:
    if has_file_access(file_record, current_user, db):
        return

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Not Authorized",
    )


def ensure_file_owner_or_admin(file_record: File, current_user: User) -> None:
    if current_user.role == "admin" or file_record.owner_id == current_user.id:
        return

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Only file owner or admin can perform this action",
    )
