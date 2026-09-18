import enum
from datetime import datetime, date, time
from sqlalchemy import (
    String, Integer, Float, Boolean, DateTime, Date, Time, Text,
    ForeignKey, Enum, UniqueConstraint, Index, LargeBinary
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class UserRole(str, enum.Enum):
    ADMIN = "admin"
    FACULTY = "faculty"
    STUDENT = "student"


class UserStatus(str, enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"


class FaceStatus(str, enum.Enum):
    REGISTERED = "registered"
    NOT_REGISTERED = "not_registered"


class AttendanceStatus(str, enum.Enum):
    PRESENT = "present"
    ABSENT = "absent"


class SessionStatus(str, enum.Enum):
    ACTIVE = "active"
    ENDED = "ended"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), nullable=False)
    status: Mapped[UserStatus] = mapped_column(Enum(UserStatus), default=UserStatus.ACTIVE)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    student: Mapped["Student"] = relationship(back_populates="user", uselist=False)
    faculty: Mapped["Faculty"] = relationship(back_populates="user", uselist=False)


class Department(Base):
    __tablename__ = "departments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)

    classes: Mapped[list["Class"]] = relationship(back_populates="department")


class Class(Base):
    __tablename__ = "classes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    section: Mapped[str | None] = mapped_column(String(50), nullable=True)
    department_id: Mapped[int] = mapped_column(ForeignKey("departments.id"), nullable=False)
    semester: Mapped[str] = mapped_column(String(50), nullable=False)

    department: Mapped["Department"] = relationship(back_populates="classes")
    students: Mapped[list["Student"]] = relationship(back_populates="class_ref")
    subjects: Mapped[list["Subject"]] = relationship(back_populates="class_ref")


class Student(Base):
    __tablename__ = "students"
    __table_args__ = (
        Index("ix_students_roll_number", "roll_number"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    full_name: Mapped[str] = mapped_column(String(200), nullable=False)
    roll_number: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    branch: Mapped[str] = mapped_column(String(100), nullable=False)
    class_section: Mapped[str] = mapped_column(String(100), nullable=False)
    semester: Mapped[str] = mapped_column(String(50), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    profile_photo: Mapped[str | None] = mapped_column(String(500), nullable=True)
    face_status: Mapped[FaceStatus] = mapped_column(Enum(FaceStatus), default=FaceStatus.NOT_REGISTERED)
    registration_date: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    status: Mapped[UserStatus] = mapped_column(Enum(UserStatus), default=UserStatus.ACTIVE)
    class_id: Mapped[int | None] = mapped_column(ForeignKey("classes.id"), nullable=True)

    user: Mapped["User"] = relationship(back_populates="student")
    class_ref: Mapped["Class"] = relationship(back_populates="students")
    face_embeddings: Mapped[list["FaceEmbedding"]] = relationship(back_populates="student", cascade="all, delete-orphan")
    attendances: Mapped[list["Attendance"]] = relationship(back_populates="student")


class Faculty(Base):
    __tablename__ = "faculty"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    department: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[UserStatus] = mapped_column(Enum(UserStatus), default=UserStatus.ACTIVE)

    user: Mapped["User"] = relationship(back_populates="faculty")
    subjects: Mapped[list["Subject"]] = relationship(back_populates="faculty")
    attendance_sessions: Mapped[list["AttendanceSession"]] = relationship(back_populates="faculty")


class Subject(Base):
    __tablename__ = "subjects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    branch: Mapped[str] = mapped_column(String(100), nullable=False)
    class_id: Mapped[int] = mapped_column(ForeignKey("classes.id"), nullable=False)
    faculty_id: Mapped[int | None] = mapped_column(ForeignKey("faculty.id"), nullable=True)

    class_ref: Mapped["Class"] = relationship(back_populates="subjects")
    faculty: Mapped["Faculty"] = relationship(back_populates="subjects")
    attendances: Mapped[list["Attendance"]] = relationship(back_populates="subject")
    sessions: Mapped[list["AttendanceSession"]] = relationship(back_populates="subject")


class FaceEmbedding(Base):
    __tablename__ = "face_embeddings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id", ondelete="CASCADE"), index=True)
    embedding: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    sample_index: Mapped[int] = mapped_column(Integer, nullable=False)
    quality_score: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    student: Mapped["Student"] = relationship(back_populates="face_embeddings")


class AttendanceSession(Base):
    __tablename__ = "attendance_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    subject_id: Mapped[int] = mapped_column(ForeignKey("subjects.id"), index=True)
    faculty_id: Mapped[int] = mapped_column(ForeignKey("faculty.id"))
    date: Mapped[date] = mapped_column(Date, index=True)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    status: Mapped[SessionStatus] = mapped_column(Enum(SessionStatus), default=SessionStatus.ACTIVE)

    subject: Mapped["Subject"] = relationship(back_populates="sessions")
    faculty: Mapped["Faculty"] = relationship(back_populates="attendance_sessions")
    attendances: Mapped[list["Attendance"]] = relationship(back_populates="session")


class Attendance(Base):
    __tablename__ = "attendance"
    __table_args__ = (
        UniqueConstraint("student_id", "subject_id", "date", "session_id", name="uq_attendance_student_subject_date_session"),
        Index("ix_attendance_date", "date"),
        Index("ix_attendance_subject_id", "subject_id"),
        Index("ix_attendance_session_id", "session_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id"), index=True)
    faculty_id: Mapped[int] = mapped_column(ForeignKey("faculty.id"))
    subject_id: Mapped[int] = mapped_column(ForeignKey("subjects.id"))
    session_id: Mapped[int] = mapped_column(ForeignKey("attendance_sessions.id"))
    date: Mapped[date] = mapped_column(Date)
    time: Mapped[time] = mapped_column(Time)
    status: Mapped[AttendanceStatus] = mapped_column(Enum(AttendanceStatus), default=AttendanceStatus.PRESENT)
    recognition_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)

    student: Mapped["Student"] = relationship(back_populates="attendances")
    subject: Mapped["Subject"] = relationship(back_populates="attendances")
    session: Mapped["AttendanceSession"] = relationship(back_populates="attendances")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False)
    entity_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    details: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
