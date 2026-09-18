from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import Optional
from app.database import get_db
from app.auth import require_roles, hash_password
from app.models import User, UserRole, Faculty, UserStatus
from app.schemas import FacultyCreate, FacultyUpdate, FacultyResponse

router = APIRouter(prefix="/faculty", tags=["faculty"])


@router.get("", response_model=dict)
def list_faculty(
    search: Optional[str] = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(UserRole.ADMIN, UserRole.FACULTY)),
):
    query = db.query(Faculty)
    if search:
        term = f"%{search}%"
        query = query.filter(or_(Faculty.name.ilike(term), Faculty.email.ilike(term)))
    total = query.count()
    items = query.order_by(Faculty.name).offset((page - 1) * per_page).limit(per_page).all()
    return {
        "items": [FacultyResponse.model_validate(f) for f in items],
        "total": total, "page": page, "per_page": per_page,
        "pages": (total + per_page - 1) // per_page,
    }


@router.post("", response_model=FacultyResponse)
def create_faculty(data: FacultyCreate, db: Session = Depends(get_db), user: User = Depends(require_roles(UserRole.ADMIN))):
    if db.query(User).filter(User.email == data.email).first():
        raise HTTPException(400, "Email already registered")
    u = User(email=data.email, password_hash=hash_password(data.password), role=UserRole.FACULTY)
    db.add(u)
    db.flush()
    faculty = Faculty(user_id=u.id, name=data.name, email=data.email, department=data.department)
    db.add(faculty)
    db.commit()
    db.refresh(faculty)
    return FacultyResponse.model_validate(faculty)


@router.put("/{faculty_id}", response_model=FacultyResponse)
def update_faculty(faculty_id: int, data: FacultyUpdate, db: Session = Depends(get_db), user: User = Depends(require_roles(UserRole.ADMIN))):
    faculty = db.query(Faculty).filter(Faculty.id == faculty_id).first()
    if not faculty:
        raise HTTPException(404, "Faculty not found")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(faculty, k, v)
    db.commit()
    db.refresh(faculty)
    return FacultyResponse.model_validate(faculty)


@router.delete("/{faculty_id}")
def delete_faculty(faculty_id: int, db: Session = Depends(get_db), user: User = Depends(require_roles(UserRole.ADMIN))):
    faculty = db.query(Faculty).filter(Faculty.id == faculty_id).first()
    if not faculty:
        raise HTTPException(404, "Faculty not found")
    user_obj = db.query(User).filter(User.id == faculty.user_id).first()
    db.delete(faculty)
    if user_obj:
        db.delete(user_obj)
    db.commit()
    return {"message": "Faculty deleted"}
