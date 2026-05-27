from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi.errors import RateLimitExceeded

from app.api.routes.admin import router as admin_router
from app.api.routes.auth import router as auth_router
from app.api.routes.files import router as files_router, share_router
from app.api.routes.users import router as users_router
from app.core.rate_limit import limiter, rate_limit_exceeded_handler

from app.db.base import Base
from app.db.session import engine
from app.db.models import User,File,AccessLog,FilePermission,ShareLink
from app.db.schema_migrations import ensure_sha256_hash_column

app = FastAPI(title="Secure Cloud Storage API")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

Base.metadata.create_all(bind=engine)
ensure_sha256_hash_column(engine)

app.include_router(auth_router)
app.include_router(files_router)
app.include_router(share_router)
app.include_router(admin_router)
app.include_router(users_router)

@app.get("/")
def root():
    return {"message": "API is running"}


