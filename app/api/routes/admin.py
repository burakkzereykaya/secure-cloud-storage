from fastapi import APIRouter,Depends,Request
from sqlalchemy.orm import Session
from sqlalchemy.sql.functions import current_user

from app.core.dependencies import get_current_admin
from app.db.models.file import File
from app.db.models.user import User
from app.db.models.access_log import AccessLog
from app.db.session import get_db
from app.schemas.file import FileMetadata
from app.schemas.user import UserResponse
from app.services.log_service import create_log
from app.schemas.log import AccessLogResponse

router = APIRouter(prefix="/admin", tags=["admin"])

@router.get("/files",response_model=list[FileMetadata])
def get_all_files(
        request: Request,
        db: Session = Depends(get_db),
        current_admin: User = Depends(get_current_admin),
):
        create_log(
            db=db,
            user_id=current_admin.id,
            action="ADMIN_VIEWED_FILES",
            status="success",
            ip_address=request.client.host if request.client.host else None,
            details="Admin viewed all files",
        )
        files = db.query(File).order_by(File.id.desc()).all()
        return files


@router.get("/users",response_model=list[UserResponse])
def get_users(
        request: Request,
        db: Session = Depends(get_db),
        current_admin: User = Depends(get_current_admin),
):
    create_log(
        db=db,
        user_id=current_admin.id,
        action="ADMIN_VIEWED_USERS",
        status="success",
        ip_address=request.client.host if request.client.host else None,
        details="Admin viewed users",
    )

    users=db.query(User).order_by(User.id.asc()).all()
    return users


@router.get("/logs",response_model=list[AccessLogResponse])
def get_logs(
        request: Request,
        db: Session = Depends(get_db),
        current_admin: User = Depends(get_current_admin),
        action: str | None = None,
        status: str | None = None,
        user_id: int | None = None,
        file_id: int | None = None,
):
    create_log(
        db=db,
        user_id=current_admin.id,
        action="ADMIN_VIEWED_LOGS",
        status="success",
        ip_address=request.client.host if request.client.host else None,
        details="Admin viewed access logs",
    )

    query = db.query(AccessLog)

    if action:
        query = query.filter(AccessLog.action == action)

    if status:
        query = query.filter(AccessLog.status == status)

    if user_id:
        query = query.filter(AccessLog.user_id == user_id)

    if file_id:
        query = query.filter(AccessLog.file_id == file_id)

    logs = query.order_by(AccessLog.id.desc()).all()

    return logs





@router.get("/test")
def admin_test(current_admin: User = Depends(get_current_admin)):
    return {
        "message": "Admin access required",
        "email": current_admin.email,
        "role": current_admin.role,
    }