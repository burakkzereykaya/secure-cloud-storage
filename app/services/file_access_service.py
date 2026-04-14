from fastapi import HTTPException, status

from app.db.models.file import File
from app.db.models.user import User

def ensure_file_access(file_record: File, current_user: User) -> None:
    if current_user.role == "admin":
        return

    if file_record.owner_id != current_user.id:
        raise HTTPException(
            status_code =status.HTTP_403_FORBIDDEN,
            detail="Not Authorized",
        )