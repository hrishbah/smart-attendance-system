from datetime import datetime, date
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session, joinedload
from app.database import get_db
from app.auth import require_roles, get_current_user
from app.models import (
    User, UserRole, Student, Faculty, Subject, FaceEmbedding, FaceStatus,
    Attendance, AttendanceSession, AttendanceStatus, SessionStatus, UserStatus,
)
from app.schemas import SessionCreate, SessionResponse, RecognitionResponse, AttendanceRecord
from app.services.face_service import face_service
from app.config import get_settings

router = APIRouter(prefix="/attendance", tags=["attendance"])
settings = get_settings()


def _load_face_candidates(db: Session) -> list[tuple[int, list]]:
    students = (
        db.query(Student)
        .options(joinedload(Student.face_embeddings))
        .filter(Student.face_status == FaceStatus.REGISTERED)
        .all()
    )
    candidates = []
    for s in students:
        embeddings = [face_service.bytes_to_embedding(fe.embedding) for fe in s.face_embeddings]
        if embeddings:
            candidates.append((s.id, embeddings))
    return candidates


@router.post("/sessions", response_model=SessionResponse)
def start_session(
    data: SessionCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(UserRole.FACULTY, UserRole.ADMIN)),
):
    subject = db.query(Subject).filter(Subject.id == data.subject_id).first()
    if not subject:
        raise HTTPException(404, "Subject not found")

    faculty = db.query(Faculty).filter(Faculty.user_id == user.id).first()
    if not faculty and user.role == UserRole.FACULTY:
        raise HTTPException(403, "Faculty profile not found")
    faculty_id = faculty.id if faculty else (subject.faculty_id or 1)

    existing = db.query(AttendanceSession).filter(
        AttendanceSession.subject_id == data.subject_id,
        AttendanceSession.date == date.today(),
        AttendanceSession.status == SessionStatus.ACTIVE,
    ).first()
    if existing:
        return _session_response(db, existing)

    session = AttendanceSession(
        subject_id=data.subject_id,
        faculty_id=faculty_id,
        date=date.today(),
        status=SessionStatus.ACTIVE,
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return _session_response(db, session)


def _session_response(db: Session, session: AttendanceSession) -> SessionResponse:
    subject = db.query(Subject).filter(Subject.id == session.subject_id).first()
    faculty = db.query(Faculty).filter(Faculty.id == session.faculty_id).first()
    present = db.query(Attendance).filter(
        Attendance.session_id == session.id,
        Attendance.status == AttendanceStatus.PRESENT,
    ).count()
    total = db.query(Student).filter(Student.status == UserStatus.ACTIVE).count()
    return SessionResponse(
        id=session.id,
        subject_id=session.subject_id,
        subject_name=subject.name if subject else "",
        faculty_id=session.faculty_id,
        faculty_name=faculty.name if faculty else "",
        date=session.date,
        started_at=session.started_at,
        ended_at=session.ended_at,
        status=session.status,
        present_count=present,
        total_students=total,
    )


@router.post("/sessions/{session_id}/end", response_model=SessionResponse)
def end_session(
    session_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(UserRole.FACULTY, UserRole.ADMIN)),
):
    session = db.query(AttendanceSession).filter(AttendanceSession.id == session_id).first()
    if not session:
        raise HTTPException(404, "Session not found")
    session.status = SessionStatus.ENDED
    session.ended_at = datetime.utcnow()
    db.commit()
    db.refresh(session)
    return _session_response(db, session)


@router.get("/sessions/{session_id}", response_model=SessionResponse)
def get_session(session_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    session = db.query(AttendanceSession).filter(AttendanceSession.id == session_id).first()
    if not session:
        raise HTTPException(404, "Session not found")
    return _session_response(db, session)


@router.get("/sessions/{session_id}/records", response_model=list[AttendanceRecord])
def get_session_records(session_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    records = db.query(Attendance).filter(Attendance.session_id == session_id).all()
    result = []
    for a in records:
        student = db.query(Student).filter(Student.id == a.student_id).first()
        subject = db.query(Subject).filter(Subject.id == a.subject_id).first()
        result.append(AttendanceRecord(
            id=a.id, student_id=a.student_id,
            student_name=student.full_name if student else "",
            roll_number=student.roll_number if student else "",
            subject_id=a.subject_id,
            subject_name=subject.name if subject else "",
            date=a.date, time=a.time, status=a.status,
            recognition_confidence=a.recognition_confidence,
        ))
    return result


@router.post("/sessions/{session_id}/recognize", response_model=RecognitionResponse)
async def recognize_and_mark(
    session_id: int,
    image: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(UserRole.FACULTY, UserRole.ADMIN)),
):
    session = db.query(AttendanceSession).filter(AttendanceSession.id == session_id).first()
    if not session:
        raise HTTPException(404, "Session not found")
    if session.status != SessionStatus.ACTIVE:
        raise HTTPException(400, "Attendance session has ended")

    contents = await image.read()
    try:
        img = face_service.decode_image(contents)
    except ValueError:
        raise HTTPException(400, "Invalid image")

    detection = face_service.detect_faces(img)
    bbox_dict = None
    if detection.bbox:
        x, y, w, h = detection.bbox
        bbox_dict = {"x": x, "y": y, "width": w, "height": h}

    if not detection.detected:
        return RecognitionResponse(
            recognized=False, message=detection.message or "No face detected",
            bbox=bbox_dict,
        )

    embedding = face_service.extract_embedding(img, detection.bbox)
    if embedding is None:
        return RecognitionResponse(recognized=False, message="Could not extract face embedding", bbox=bbox_dict)

    candidates = _load_face_candidates(db)
    match = face_service.find_best_match(embedding, candidates)

    if not match:
        return RecognitionResponse(
            recognized=False,
            message="Unknown Face - Attendance Not Marked",
            bbox=bbox_dict,
        )

    student = db.query(Student).filter(Student.id == match.student_id).first()
    if not student:
        return RecognitionResponse(recognized=False, message="Unknown Student", bbox=bbox_dict)

    existing = db.query(Attendance).filter(
        Attendance.student_id == student.id,
        Attendance.session_id == session_id,
        Attendance.subject_id == session.subject_id,
        Attendance.date == session.date,
    ).first()

    if existing:
        return RecognitionResponse(
            recognized=True,
            student_id=student.id,
            full_name=student.full_name,
            roll_number=student.roll_number,
            branch=student.branch,
            confidence=round(match.confidence, 1),
            message="Already Present",
            already_present=True,
            attendance_time=existing.time.strftime("%I:%M %p"),
            bbox=bbox_dict,
        )

    faculty = db.query(Faculty).filter(Faculty.user_id == user.id).first()
    faculty_id = faculty.id if faculty else session.faculty_id
    now = datetime.utcnow()

    attendance = Attendance(
        student_id=student.id,
        faculty_id=faculty_id,
        subject_id=session.subject_id,
        session_id=session_id,
        date=session.date,
        time=now.time(),
        status=AttendanceStatus.PRESENT,
        recognition_confidence=round(match.confidence, 2),
    )
    db.add(attendance)
    db.commit()

    return RecognitionResponse(
        recognized=True,
        student_id=student.id,
        full_name=student.full_name,
        roll_number=student.roll_number,
        branch=student.branch,
        confidence=round(match.confidence, 1),
        message="Attendance Marked",
        attendance_marked=True,
        attendance_time=now.strftime("%I:%M %p"),
        bbox=bbox_dict,
    )


@router.get("/today")
def today_attendance(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    today = date.today()
    records = db.query(Attendance).filter(Attendance.date == today).all()
    return {"count": len(records), "records": [
        {"student_id": r.student_id, "subject_id": r.subject_id, "time": r.time.strftime("%I:%M %p")}
        for r in records
    ]}
