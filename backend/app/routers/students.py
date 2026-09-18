from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Form
from sqlalchemy.orm import Session
from sqlalchemy import or_, func
from typing import Optional
import os
import uuid
from app.database import get_db
from app.auth import require_roles, get_current_user
from app.models import User, UserRole, Student, FaceStatus, FaceEmbedding, UserStatus
from app.schemas import StudentCreate, StudentUpdate, StudentResponse, StudentProfile, AttendanceRecord
from app.config import get_settings
from app.models import Attendance, AttendanceStatus, Subject

router = APIRouter(prefix="/students", tags=["students"])
settings = get_settings()


def student_to_response(s: Student) -> StudentResponse:
    return StudentResponse.model_validate(s)


@router.get("", response_model=dict)
def list_students(
    search: Optional[str] = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    face_status: Optional[str] = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    query = db.query(Student)
    if search:
        term = f"%{search}%"
        query = query.filter(or_(Student.full_name.ilike(term), Student.roll_number.ilike(term), Student.email.ilike(term)))
    if face_status:
        query = query.filter(Student.face_status == FaceStatus(face_status))
    total = query.count()
    students = query.order_by(Student.full_name).offset((page - 1) * per_page).limit(per_page).all()
    items = []
    for s in students:
        data = student_to_response(s).model_dump()
        present = db.query(Attendance).filter(
            Attendance.student_id == s.id, Attendance.status == AttendanceStatus.PRESENT
        ).count()
        total = db.query(Attendance).filter(Attendance.student_id == s.id).count()
        data["attendance_percentage"] = round(present / total * 100, 1) if total else 0.0
        items.append(data)
    return {
        "items": items,
        "total": total,
        "page": page,
        "per_page": per_page,
        "pages": (total + per_page - 1) // per_page,
    }


@router.post("", response_model=StudentResponse)
def create_student(
    data: StudentCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(UserRole.ADMIN)),
):
    if db.query(Student).filter(Student.roll_number == data.roll_number).first():
        raise HTTPException(400, "Roll number already exists")
    student = Student(**data.model_dump())
    db.add(student)
    db.commit()
    db.refresh(student)
    return student_to_response(student)


@router.get("/{student_id}", response_model=StudentResponse)
def get_student(student_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(404, "Student not found")
    return student_to_response(student)


@router.put("/{student_id}", response_model=StudentResponse)
def update_student(
    student_id: int,
    data: StudentUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(UserRole.ADMIN)),
):
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(404, "Student not found")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(student, k, v)
    db.commit()
    db.refresh(student)
    return student_to_response(student)


@router.delete("/{student_id}")
def delete_student(
    student_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(UserRole.ADMIN)),
):
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(404, "Student not found")
    if student.profile_photo:
        path = os.path.join(settings.upload_dir, student.profile_photo)
        if os.path.exists(path):
            os.remove(path)
    db.delete(student)
    db.commit()
    return {"message": "Student deleted"}


@router.get("/{student_id}/profile", response_model=StudentProfile)
def get_student_profile(student_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(404, "Student not found")
    attendances = db.query(Attendance).filter(Attendance.student_id == student_id).all()
    present = sum(1 for a in attendances if a.status == AttendanceStatus.PRESENT)
    absent = sum(1 for a in attendances if a.status == AttendanceStatus.ABSENT)
    total = len(attendances)
    subjects = list({a.subject.name for a in attendances if a.subject})
    history = []
    for a in sorted(attendances, key=lambda x: (x.date, x.time), reverse=True)[:50]:
        history.append(AttendanceRecord(
            id=a.id, student_id=a.student_id, student_name=student.full_name,
            roll_number=student.roll_number, subject_id=a.subject_id,
            subject_name=a.subject.name if a.subject else "", date=a.date,
            time=a.time, status=a.status, recognition_confidence=a.recognition_confidence,
        ))
    return StudentProfile(
        student=student_to_response(student),
        subjects=subjects,
        total_classes=total,
        present=present,
        absent=absent,
        attendance_percentage=round(present / total * 100, 1) if total else 0,
        attendance_history=history,
    )


@router.get("/{student_id}/photo")
def get_student_photo(student_id: int, db: Session = Depends(get_db)):
    from fastapi.responses import FileResponse
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student or not student.profile_photo:
        raise HTTPException(404, "Photo not found")
    path = os.path.join(settings.upload_dir, student.profile_photo)
    if not os.path.exists(path):
        raise HTTPException(404, "Photo file not found")
    return FileResponse(path)
