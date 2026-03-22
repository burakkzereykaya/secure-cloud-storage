from fastapi import APIRouter,Depends

from app.core.dependencies import get_current_admin
from app.db.models.user import User

router = APIRouter(prefix="/admin", tags=["admin"])

@router.get("/test")
def admin_test(current_admin: User = Depends(get_current_admin)):
    return {
        "message": "Admin access required",
        "email": current_admin.email,
        "role": current_admin.role,
    }

@router.get("/logs")
def get_logs():
    return {"message": "Logs endpoint placeholder"}


@router.get("/users")
def get_users():
    return {"message": "Users endpoint placeholder"}