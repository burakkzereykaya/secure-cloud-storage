from fastapi import FastAPI

from app.api.routes.auth import router as auth_router
from app.api.routes.files import router as files_router
from app.api.routes.admin import router as admin_router

app = FastAPI(title="Secure Cloud Storage API")


@app.get("/")
def root():
    return {"message": "API is running"}


app.include_router(auth_router)
app.include_router(files_router)
app.include_router(admin_router)