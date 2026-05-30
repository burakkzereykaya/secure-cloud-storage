from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from slowapi.errors import RateLimitExceeded

from app.api.routes.admin import router as admin_router
from app.api.routes.auth import router as auth_router
from app.api.routes.files import router as files_router, share_router
from app.core.config import settings
from app.api.routes.users import router as users_router
from app.core.rate_limit import limiter, rate_limit_exceeded_handler

from app.db.base import Base
from app.db.session import engine
from app.db.models import User,File,AccessLog,FilePermission,ShareLink
from app.db.schema_migrations import ensure_sha256_hash_column

FRONTEND_DIR = Path(__file__).resolve().parents[1] / "frontend"

app = FastAPI(title="Secure Cloud Storage API")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition"],
)


@app.middleware("http")
async def add_no_cache_for_frontend(request, call_next):
    response = await call_next(request)
    if (
        request.url.path == "/"
        or request.url.path in {"/app.js", "/config.js", "/styles.css"}
        or request.url.path.startswith("/frontend/")
    ):
        response.headers["Cache-Control"] = "no-store"
    return response


Base.metadata.create_all(bind=engine)
ensure_sha256_hash_column(engine)

app.include_router(auth_router)
app.include_router(files_router)
app.include_router(share_router)
app.include_router(admin_router)
app.include_router(users_router)

if FRONTEND_DIR.exists():
    app.mount(
        "/frontend",
        StaticFiles(directory=FRONTEND_DIR),
        name="frontend",
    )


@app.get("/")
def root():
    if FRONTEND_DIR.exists():
        return FileResponse(FRONTEND_DIR / "index.html")
    return {"message": "API is running"}


@app.get("/{asset_name}", include_in_schema=False)
def frontend_asset(asset_name: str):
    if asset_name not in {"app.js", "config.js", "styles.css"}:
        raise HTTPException(status_code=404, detail="Not found")

    asset_path = FRONTEND_DIR / asset_name
    if not asset_path.exists():
        raise HTTPException(status_code=404, detail="Not found")
    return FileResponse(asset_path)


