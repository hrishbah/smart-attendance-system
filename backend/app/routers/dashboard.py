from datetime import date, timedelta
from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional
import io
import csv
from app.database import get_db
from app.auth import get_current_user, require_roles
from app.models import (
    User, UserRole, Student, Faculty, Attendance, AttendanceStatus,
    FaceStatus, Subject, AttendanceSession,
)
from app.schemas import DashboardStats, ChartDataPoint, AttendanceRecord

router = APIRouter(tags=["dashboard"])


@router.get("/dashboard/stats", response_model=DashboardStats)
def dashboard_stats(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    today = date.today()
    total_students = db.query(Student).count()
    total_faculty = db.query(Faculty).count()
    registered_faces = db.query(Student).filter(Student.face_status == FaceStatus.REGISTERED).count()
    today_present = db.query(Attendance).filter(
        Attendance.date == today, Attendance.status == AttendanceStatus.PRESENT
    ).count()
    today_absent = max(0, total_students - today_present) if total_students else 0
    pct = round(today_present / total_students * 100, 1) if total_students else 0
    return DashboardStats(
        total_students=total_students,
        total_faculty=total_faculty,
        today_present=today_present,
        today_absent=today_absent,
        attendance_percentage=pct,
        registered_faces=registered_faces,
    )


@router.get("/dashboard/charts/daily", response_model=list[ChartDataPoint])
def daily_chart(days: int = Query(7, ge=1, le=30), db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    total_students = db.query(Student).count()
    result = []
    for i in range(days - 1, -1, -1):
        d = date.today() - timedelta(days=i)
        present = db.query(Attendance).filter(
            Attendance.date == d, Attendance.status == AttendanceStatus.PRESENT
        ).count()
        absent = max(0, total_students - present)
        pct = round(present / total_students * 100, 1) if total_students else 0
        result.append(ChartDataPoint(label=d.strftime("%a %d"), present=present, absent=absent, percentage=pct))
    return result


@router.get("/dashboard/charts/subject", response_model=list[ChartDataPoint])
def subject_chart(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    subjects = db.query(Subject).all()
    result = []
    for s in subjects:
        present = db.query(Attendance).filter(
            Attendance.subject_id == s.id, Attendance.status == AttendanceStatus.PRESENT
        ).count()
        result.append(ChartDataPoint(label=s.name, present=present, absent=0, percentage=0))
    return result


@router.get("/reports/attendance")
def attendance_report(
    report_type: str = Query("daily"),
    subject_id: Optional[int] = None,
    student_id: Optional[int] = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    query = db.query(Attendance)
    today = date.today()
    if report_type == "daily":
        query = query.filter(Attendance.date == today)
    elif report_type == "weekly":
        query = query.filter(Attendance.date >= today - timedelta(days=7))
    elif report_type == "monthly":
        query = query.filter(Attendance.date >= today - timedelta(days=30))
    if subject_id:
        query = query.filter(Attendance.subject_id == subject_id)
    if student_id:
        query = query.filter(Attendance.student_id == student_id)

    records = query.all()
    result = []
    for a in records:
        student = db.query(Student).filter(Student.id == a.student_id).first()
        subject = db.query(Subject).filter(Subject.id == a.subject_id).first()
        result.append({
            "id": a.id,
            "student_name": student.full_name if student else "",
            "roll_number": student.roll_number if student else "",
            "subject": subject.name if subject else "",
            "date": str(a.date),
            "time": a.time.strftime("%I:%M %p"),
            "status": a.status.value,
            "confidence": a.recognition_confidence,
        })
    return {"type": report_type, "count": len(result), "records": result}


@router.get("/reports/export/csv")
def export_csv(
    report_type: str = Query("daily"),
    subject_id: Optional[int] = None,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(UserRole.ADMIN, UserRole.FACULTY)),
):
    data = attendance_report(report_type=report_type, subject_id=subject_id, db=db, user=user)
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=["student_name", "roll_number", "subject", "date", "time", "status", "confidence"])
    writer.writeheader()
    for r in data["records"]:
        writer.writerow({k: r[k] for k in ["student_name", "roll_number", "subject", "date", "time", "status", "confidence"]})
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=attendance_{report_type}.csv"},
    )


@router.get("/reports/export/excel")
def export_excel(
    report_type: str = Query("daily"),
    subject_id: Optional[int] = None,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(UserRole.ADMIN, UserRole.FACULTY)),
):
    from openpyxl import Workbook
    data = attendance_report(report_type=report_type, subject_id=subject_id, db=db, user=user)
    wb = Workbook()
    ws = wb.active
    ws.title = "Attendance"
    headers = ["Student Name", "Roll Number", "Subject", "Date", "Time", "Status", "Confidence"]
    ws.append(headers)
    for r in data["records"]:
        ws.append([r["student_name"], r["roll_number"], r["subject"], r["date"], r["time"], r["status"], r["confidence"]])
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename=attendance_{report_type}.xlsx"},
    )


@router.get("/reports/export/pdf")
def export_pdf(
    report_type: str = Query("daily"),
    subject_id: Optional[int] = None,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(UserRole.ADMIN, UserRole.FACULTY)),
):
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas
    data = attendance_report(report_type=report_type, subject_id=subject_id, db=db, user=user)
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=letter)
    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, 750, f"Attendance Report - {report_type.title()}")
    c.setFont("Helvetica", 10)
    y = 720
    for r in data["records"][:50]:
        line = f"{r['student_name']} | {r['roll_number']} | {r['subject']} | {r['date']} | {r['status']}"
        c.drawString(50, y, line[:100])
        y -= 15
        if y < 50:
            c.showPage()
            y = 750
    c.save()
    buf.seek(0)
    return StreamingResponse(
        buf,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=attendance_{report_type}.pdf"},
    )
