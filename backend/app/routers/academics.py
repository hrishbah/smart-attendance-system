from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.auth import require_roles, get_current_user
from app.models import User, UserRole, Subject, Class, Department, Faculty
from app.schemas import SubjectCreate, SubjectResponse, ClassCreate, ClassResponse, DepartmentResponse

router = APIRouter(tags=["academics"])


@router.get("/departments", response_model=list[DepartmentResponse])
def list_departments(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return [DepartmentResponse.model_validate(d) for d in db.query(Department).all()]


@router.get("/classes", response_model=list[ClassResponse])
def list_classes(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    items = db.query(Class).all()
    result = []
    for c in items:
        dept = db.query(Department).filter(Department.id == c.department_id).first()
        result.append(ClassResponse(
            id=c.id, name=c.name, section=c.section,
            department_id=c.department_id, semester=c.semester,
            department_name=dept.name if dept else None,
        ))
    return result


@router.post("/classes", response_model=ClassResponse)
def create_class(data: ClassCreate, db: Session = Depends(get_db), user: User = Depends(require_roles(UserRole.ADMIN))):
    c = Class(**data.model_dump())
    db.add(c)
    db.commit()
    db.refresh(c)
    dept = db.query(Department).filter(Department.id == c.department_id).first()
    return ClassResponse(id=c.id, name=c.name, section=c.section, department_id=c.department_id, semester=c.semester, department_name=dept.name if dept else None)


@router.get("/subjects", response_model=list[SubjectResponse])
def list_subjects(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    items = db.query(Subject).all()
    result = []
    for s in items:
        faculty = db.query(Faculty).filter(Faculty.id == s.faculty_id).first() if s.faculty_id else None
        cls = db.query(Class).filter(Class.id == s.class_id).first()
        result.append(SubjectResponse(
            id=s.id, name=s.name, code=s.code, branch=s.branch,
            class_id=s.class_id, faculty_id=s.faculty_id,
            faculty_name=faculty.name if faculty else None,
            class_name=cls.name if cls else None,
        ))
    return result


@router.post("/subjects", response_model=SubjectResponse)
def create_subject(data: SubjectCreate, db: Session = Depends(get_db), user: User = Depends(require_roles(UserRole.ADMIN))):
    if db.query(Subject).filter(Subject.code == data.code).first():
        raise HTTPException(400, "Subject code already exists")
    s = Subject(**data.model_dump())
    db.add(s)
    db.commit()
    db.refresh(s)
    faculty = db.query(Faculty).filter(Faculty.id == s.faculty_id).first() if s.faculty_id else None
    cls = db.query(Class).filter(Class.id == s.class_id).first()
    return SubjectResponse(
        id=s.id, name=s.name, code=s.code, branch=s.branch,
        class_id=s.class_id, faculty_id=s.faculty_id,
        faculty_name=faculty.name if faculty else None,
        class_name=cls.name if cls else None,
    )


@router.put("/subjects/{subject_id}", response_model=SubjectResponse)
def update_subject(subject_id: int, data: SubjectCreate, db: Session = Depends(get_db), user: User = Depends(require_roles(UserRole.ADMIN))):
    s = db.query(Subject).filter(Subject.id == subject_id).first()
    if not s:
        raise HTTPException(404, "Subject not found")
    for k, v in data.model_dump().items():
        setattr(s, k, v)
    db.commit()
    db.refresh(s)
    faculty = db.query(Faculty).filter(Faculty.id == s.faculty_id).first() if s.faculty_id else None
    cls = db.query(Class).filter(Class.id == s.class_id).first()
    return SubjectResponse(
        id=s.id, name=s.name, code=s.code, branch=s.branch,
        class_id=s.class_id, faculty_id=s.faculty_id,
        faculty_name=faculty.name if faculty else None,
        class_name=cls.name if cls else None,
    )


@router.delete("/subjects/{subject_id}")
def delete_subject(subject_id: int, db: Session = Depends(get_db), user: User = Depends(require_roles(UserRole.ADMIN))):
    s = db.query(Subject).filter(Subject.id == subject_id).first()
    if not s:
        raise HTTPException(404, "Subject not found")
    db.delete(s)
    db.commit()
    return {"message": "Subject deleted"}
