
from fastapi import APIRouter,Depends,File as FastAPIFile, UploadFile, HTTPException
from sqlalchemy.orm import sessionmaker,Session

from app.core.dependencies import get_current_user
from app.db.models.file import File
from app.db.models.user import User
from app.db.session import get_db
from app.schemas.file import  FileUploadResponse

router = APIRouter(prefix="/files", tags=["files"])

#max file size (örnek: 5MB)
MAX_FILE_SIZE = 1024 * 1024 * 5

#allowed content types
ALLOWED_TYPES = ["image/png","img/jpeg","application/pdf"]

@router.post("/upload",response_model=FileUploadResponse)
def upload_file(
    file: UploadFile = FastAPIFile(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not file.filename:
        raise HTTPException(status_code=400,detail="File name is required")

    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(status_code=400,detail=f"File type is not supported {file.content_type}")

    #read
    contents= await file.read()

    if not contents:
        raise HTTPException(status_code=400,details="File is empty")

    #size
    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400,detail="File is too big to upload")

    #METADATA
    filename = file.filename
    size = len(contents)
    content_type = file.content_type

    #placeholders for now
    blob_path = f"uploads/{current_user.id}/{filename}"
    encrypted_dek = "placeholder_dek"
    iv_or_nonce = "placeholder_iv"

    new_file = file(
        owner_id=current_user.id,
        original_filename=filename,
        size=size,
        content_type=content_type,
        blob_path=blob_path,
        encrypted_dek=encrypted_dek,
        iv_or_nonce=iv_or_nonce,
        status="uploaded"
    )

    db.add_file(new_file)
    db.commit()
    db.refresh(new_file)

    return FileUploadResponse(
        id=new_file.id,
        filename=file.filename,
        size=new_file.size,
        uploaded_at=new_file.uploaded_at,
        message=f"Authenticated upload request accepted for user {current_user.email}"
    )

@router.get("/download")
def download_file():
    return {"message": "Download endpoint placeholder"}