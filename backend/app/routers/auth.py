from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session
from app.database import get_db
from app.auth import verify_password, create_access_token, get_current_user, hash_password
from app.models import User, UserRole, Faculty, Student
from app.schemas import LoginRequest, TokenResponse
from app.config import get_settings

router = APIRouter(prefix="/auth", tags=["auth"])
settings = get_settings()


@router.post("/login", response_model=TokenResponse)
def login(data: LoginRequest, response: Response, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == data.email).first()
    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    name = data.email
    if user.role == UserRole.FACULTY:
        faculty = db.query(Faculty).filter(Faculty.user_id == user.id).first()
        if faculty:
            name = faculty.name
    elif user.role == UserRole.STUDENT:
        student = db.query(Student).filter(Student.user_id == user.id).first()
        if student:
            name = student.full_name
    elif user.role == UserRole.ADMIN:
        name = "Admin User"

    token = create_access_token({"sub": str(user.id), "role": user.role.value})
    same_site = "none" if settings.cookie_secure else "lax"
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        secure=settings.cookie_secure,
        samesite=same_site,
        max_age=settings.access_token_expire_minutes * 60,
    )
    return TokenResponse(access_token=token, role=user.role, name=name, email=user.email)


@router.post("/logout")
def logout(response: Response):
    same_site = "none" if settings.cookie_secure else "lax"
    response.delete_cookie("access_token", samesite=same_site, secure=settings.cookie_secure)
    return {"message": "Logged out"}


@router.get("/me", response_model=TokenResponse)
def get_me(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    name = user.email
    if user.role == UserRole.FACULTY:
        faculty = db.query(Faculty).filter(Faculty.user_id == user.id).first()
        if faculty:
            name = faculty.name
    elif user.role == UserRole.STUDENT:
        student = db.query(Student).filter(Student.user_id == user.id).first()
        if student:
            name = student.full_name
    elif user.role == UserRole.ADMIN:
        name = "Admin User"
    return TokenResponse(access_token="", role=user.role, name=name, email=user.email)
