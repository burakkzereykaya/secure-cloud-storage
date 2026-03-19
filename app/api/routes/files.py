from fastapi import APIRouter

router = APIRouter(prefix="/files", tags=["files"])


@router.post("/upload")
def upload_file():
    return {"message": "Upload endpoint placeholder"}


@router.get("/download")
def download_file():
    return {"message": "Download endpoint placeholder"}