from datetime import datetime, date, time
from typing import Optional
from pydantic import BaseModel, EmailStr, Field
from app.models import UserRole, FaceStatus, AttendanceStatus, SessionStatus, UserStatus


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: UserRole
    name: str
    email: str


class LoginRequest(BaseModel):
    email: str
    password: str


class StudentCreate(BaseModel):
    full_name: str
    roll_number: str
    branch: str
    class_section: str
    semester: str
    email: EmailStr
    phone: Optional[str] = None
    class_id: Optional[int] = None


class StudentUpdate(BaseModel):
    full_name: Optional[str] = None
    roll_number: Optional[str] = None
    branch: Optional[str] = None
    class_section: Optional[str] = None
    semester: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    class_id: Optional[int] = None
    status: Optional[UserStatus] = None


class StudentResponse(BaseModel):
    id: int
    full_name: str
    roll_number: str
    branch: str
    class_section: str
    semester: str
    email: str
    phone: Optional[str]
    profile_photo: Optional[str]
    face_status: FaceStatus
    registration_date: datetime
    status: UserStatus
    class_id: Optional[int]

    class Config:
        from_attributes = True


class FacultyCreate(BaseModel):
    name: str
    email: EmailStr
    department: str
    password: str = Field(min_length=6)


class FacultyUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    department: Optional[str] = None
    status: Optional[UserStatus] = None


class FacultyResponse(BaseModel):
    id: int
    name: str
    email: str
    department: str
    status: UserStatus

    class Config:
        from_attributes = True


class SubjectCreate(BaseModel):
    name: str
    code: str
    branch: str
    class_id: int
    faculty_id: Optional[int] = None


class SubjectResponse(BaseModel):
    id: int
    name: str
    code: str
    branch: str
    class_id: int
    faculty_id: Optional[int]
    faculty_name: Optional[str] = None
    class_name: Optional[str] = None

    class Config:
        from_attributes = True


class ClassCreate(BaseModel):
    name: str
    section: Optional[str] = None
    department_id: int
    semester: str


class ClassResponse(BaseModel):
    id: int
    name: str
    section: Optional[str]
    department_id: int
    semester: str
    department_name: Optional[str] = None

    class Config:
        from_attributes = True


class DepartmentResponse(BaseModel):
    id: int
    name: str
    code: str

    class Config:
        from_attributes = True


class FaceDetectResponse(BaseModel):
    detected: bool
    face_count: int
    message: str
    bbox: Optional[dict] = None
    quality_score: Optional[float] = None


class FaceRegisterResponse(BaseModel):
    success: bool
    message: str
    samples_collected: int
    profile_photo: Optional[str] = None


class RecognitionResponse(BaseModel):
    recognized: bool
    student_id: Optional[int] = None
    full_name: Optional[str] = None
    roll_number: Optional[str] = None
    branch: Optional[str] = None
    confidence: Optional[float] = None
    message: str
    attendance_marked: bool = False
    already_present: bool = False
    attendance_time: Optional[str] = None
    bbox: Optional[dict] = None


class SessionCreate(BaseModel):
    subject_id: int


class SessionResponse(BaseModel):
    id: int
    subject_id: int
    subject_name: str
    faculty_id: int
    faculty_name: str
    date: date
    started_at: datetime
    ended_at: Optional[datetime]
    status: SessionStatus
    present_count: int = 0
    total_students: int = 0

    class Config:
        from_attributes = True


class AttendanceRecord(BaseModel):
    id: int
    student_id: int
    student_name: str
    roll_number: str
    subject_id: int
    subject_name: str
    date: date
    time: time
    status: AttendanceStatus
    recognition_confidence: Optional[float]

    class Config:
        from_attributes = True


class DashboardStats(BaseModel):
    total_students: int
    total_faculty: int
    today_present: int
    today_absent: int
    attendance_percentage: float
    registered_faces: int


class ChartDataPoint(BaseModel):
    label: str
    present: int
    absent: int
    percentage: float


class StudentProfile(BaseModel):
    student: StudentResponse
    subjects: list[str]
    total_classes: int
    present: int
    absent: int
    attendance_percentage: float
    attendance_history: list[AttendanceRecord]
