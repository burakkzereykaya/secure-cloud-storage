from fastapi import APIRouter,Depends
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_admin
from app.db.models.file import File
from app.db.models.user import User
from app.db.models.access_log import AccessLog
from app.db.session import get_db
from app.schemas.file import FileMetadata
from app.schemas.user import UserResponse

router = APIRouter(prefix="/admin", tags=["admin"])

@router.get("/files",response_model=list[FileMetadata])
def get_all_files(
        db: Session = Depends(get_db),
        current_admin: User = Depends(get_current_admin),
):
        files = db.query(File).order_by(File.id.desc()).all()
        return files


@router.get("/users",response_model=list[UserResponse])
def get_users(
        db: Session = Depends(get_db),
        current_admin: User = Depends(get_current_admin),
):
    users=db.query(User).order_by(User.id.asc()).all()
    return users


@router.get("/logs")
def get_logs(
        db: Session = Depends(get_db),
        current_admin: User = Depends(get_current_admin),
):
    logs =db.query(AccessLog).order_by(AccessLog.id.desc()).all()

    return [
        {
            "id": log.id,
            "user_id": log.user_id,
            "file_id": log.file_id,
            "action": log.action,
            "status": log.status,
            "ip_address": log.ip_address,
            "timestamp": log.timestamp,
        }
        for log in logs
    ]





@router.get("/test")
def admin_test(current_admin: User = Depends(get_current_admin)):
    return {
        "message": "Admin access required",
        "email": current_admin.email,
        "role": current_admin.role,
    }