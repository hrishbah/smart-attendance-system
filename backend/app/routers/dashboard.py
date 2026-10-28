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
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    data = attendance_report(report_type=report_type, subject_id=subject_id, db=db, user=user)
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=letter,
                            rightMargin=0.5*inch, leftMargin=0.5*inch,
                            topMargin=0.6*inch, bottomMargin=0.6*inch)
    styles = getSampleStyleSheet()
    story = []
    story.append(Paragraph(f"<b>Attendance Report - {report_type.title()}</b>", styles['Title']))
    story.append(Spacer(1, 0.15*inch))
    headers = [Paragraph("<b>Student Name</b>", styles['Normal']), Paragraph("<b>Roll No</b>", styles['Normal']), Paragraph("<b>Subject</b>", styles['Normal']), Paragraph("<b>Date</b>", styles['Normal']), Paragraph("<b>Time</b>", styles['Normal']), Paragraph("<b>Status</b>", styles['Normal']), Paragraph("<b>Confidence</b>", styles['Normal'])]
    rows = [headers]
    for r in data["records"][:50]:
        rows.append([
            Paragraph(str(r.get("student_name") or ""), styles['Normal']),
            Paragraph(str(r.get("roll_number") or ""), styles['Normal']),
            Paragraph(str(r.get("subject") or ""), styles['Normal']),
            Paragraph(str(r.get("date") or ""), styles['Normal']),
            Paragraph(str(r.get("time") or ""), styles['Normal']),
            Paragraph(str(r.get("status") or ""), styles['Normal']),
            Paragraph(str(r.get("confidence") if r.get("confidence") is not None else "-"), styles['Normal']),
        ])
    col_widths = [140, 70, 110, 60, 60, 55, 45]
    table = Table(rows, repeatRows=1, colWidths=col_widths)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.darkblue),
        ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,0), 9),
        ('BOTTOMPADDING', (0,0), (-1,0), 8),
        ('BACKGROUND', (0,1), (-1,-1), colors.whitesmoke),
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
        ('FONTNAME', (0,1), (-1,-1), 'Helvetica'),
        ('FONTSIZE', (0,1), (-1,-1), 7),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('LEFTPADDING', (0,0), (-1,-1), 4),
        ('RIGHTPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,1), (-1,-1), 4),
    ]))
    story.append(table)
    doc.build(story)
    buf.seek(0)
    return StreamingResponse(
        buf,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=attendance_{report_type}.pdf"},
    )
