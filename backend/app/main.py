from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os
from app.config import get_settings, ensure_dirs
from app.seed import init_db
from app.routers import auth, students, face, attendance, faculty, academics, dashboard

settings = get_settings()
ensure_dirs(settings)

app = FastAPI(
    title="Smart Attendance System",
    description="Face Recognition Based Attendance Management",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url, "http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

upload_path = settings.upload_dir
os.makedirs(upload_path, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=upload_path), name="uploads")

app.include_router(auth.router, prefix="/api")
app.include_router(students.router, prefix="/api")
app.include_router(face.router, prefix="/api")
app.include_router(attendance.router, prefix="/api")
app.include_router(faculty.router, prefix="/api")
app.include_router(academics.router, prefix="/api")
app.include_router(dashboard.router, prefix="/api")


@app.on_event("startup")
def startup():
    init_db()


@app.get("/api/health")
def health():
    return {"status": "ok", "service": "Smart Attendance System"}
