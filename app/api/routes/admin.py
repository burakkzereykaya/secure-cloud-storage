from fastapi import APIRouter

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/logs")
def get_logs():
    return {"message": "Logs endpoint placeholder"}


@router.get("/users")
def get_users():
    return {"message": "Users endpoint placeholder"}