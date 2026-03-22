from fastapi import FastAPI

from app.api.routes.admin import router as admin_router
from app.api.routes.auth import router as auth_router
from app.api.routes.files import router as files_router
from app.api.routes.users import router as users_router
from app.db.base import Base
from app.db.session import engine
from app.db.models import User,File,AccessLog

app = FastAPI(title="Secure Cloud Storage API")

Base.metadata.create_all(bind=engine)

app.include_router(auth_router)
app.include_router(files_router)
app.include_router(admin_router)
app.include_router(users_router)

@app.get("/")
def root():
    return {"message": "API is running"}


