from sqlalchemy.orm import Session
from app.database import SessionLocal, engine, Base
from app.auth import hash_password
from app.models import (
    User,
    UserRole,
    UserStatus,
    Department,
    Class,
    Student,
    Faculty,
    Subject,
    FaceStatus,
)


FIRST_NAMES = [
    "Aarav", "Vivaan", "Aditya", "Arjun", "Sai", "Arnav", "Ayaan", "Krishna",
    "Ishaan", "Shaurya", "Atharv", "Advik", "Pranav", "Advaith", "Dhruv",
    "Kabir", "Ritvik", "Aarush", "Kian", "Darsh", "Vihaan", "Ananya", "Diya",
    "Myra", "Sara", "Ira", "Pari", "Anika", "Navya", "Aadhya", "Kiara",
    "Riya", "Avni", "Saanvi", "Ishita", "Kavya", "Priya", "Neha", "Pooja",
    "Sneha", "Divya", "Meera", "Tanvi", "Shreya", "Nisha", "Kiran", "Rahul",
    "Amit", "Vikram", "Suresh", "Rajesh", "Manoj", "Deepak", "Sanjay",
]

LAST_NAMES = [
    "Sharma", "Verma", "Gupta", "Singh", "Kumar", "Patel", "Reddy", "Nair",
    "Iyer", "Joshi", "Mehta", "Shah", "Agarwal", "Mishra", "Pandey",
    "Yadav", "Chauhan", "Thakur", "Bhat", "Rao", "Desai", "Kulkarni",
]

DEPARTMENTS = [
    ("Computer Science & AI", "CSE-AI"),
    ("Electronics", "ECE"),
    ("Mechanical", "ME"),
    ("Civil", "CE"),
]

SUBJECTS = [
    ("Mathematics 2", "MATH201"),
    ("Physics", "PHY101"),
    ("Programming for Problem Solving", "PPS101"),
    ("Electrical Engineering", "EE101"),
    ("Environmental Studies", "EVS101"),
]

FACULTY_NAMES = [
    ("Dr. Rajesh Kumar", "rajesh.kumar@college.edu", "CSE AI"),
    ("Dr. Priya Sharma", "priya.sharma@college.edu", "CSE AI"),
    ("Prof. Amit Verma", "amit.verma@college.edu", "Physics"),
    ("Dr. Sneha Patel", "sneha.patel@college.edu", "Mathematics"),
    ("Prof. Vikram Singh", "vikram.singh@college.edu", "Electrical"),
]


def seed_database(db: Session):

    # =========================================================
    # ADMIN
    # =========================================================

    admin = (
        db.query(User)
        .filter(User.email == "admin@attendance.edu")
        .first()
    )

    if not admin:
        admin = User(
            email="admin@attendance.edu",
            password_hash=hash_password("admin123"),
            role=UserRole.ADMIN,
        )
        db.add(admin)
        db.flush()

    # =========================================================
    # DEPARTMENTS
    # =========================================================

    departments = {}

    for name, code in DEPARTMENTS:

        department = (
            db.query(Department)
            .filter(Department.code == code)
            .first()
        )

        if not department:
            department = Department(
                name=name,
                code=code,
            )
            db.add(department)
            db.flush()

        departments[code] = department

    # =========================================================
    # CSE AI CLASS
    # =========================================================

    cse_class = (
        db.query(Class)
        .filter(
            Class.name == "CSE AI",
            Class.section == "A",
            Class.department_id == departments["CSE-AI"].id,
        )
        .first()
    )

    if not cse_class:

        cse_class = Class(
            name="CSE AI",
            section="A",
            department_id=departments["CSE-AI"].id,
            semester="1st Semester",
        )

        db.add(cse_class)
        db.flush()

    # =========================================================
    # FACULTY
    # =========================================================

    faculty_records = []

    # First 5 faculty
    for name, email, dept in FACULTY_NAMES:

        user = (
            db.query(User)
            .filter(User.email == email)
            .first()
        )

        if not user:

            user = User(
                email=email,
                password_hash=hash_password("faculty123"),
                role=UserRole.FACULTY,
            )

            db.add(user)
            db.flush()

        faculty = (
            db.query(Faculty)
            .filter(Faculty.email == email)
            .first()
        )

        if not faculty:

            faculty = Faculty(
                user_id=user.id,
                name=name,
                email=email,
                department=dept,
            )

            db.add(faculty)
            db.flush()

        faculty_records.append(faculty)

    # Additional 45 faculty
    for i in range(45):

        idx = i + len(FACULTY_NAMES)

        name = (
            f"Prof. "
            f"{FIRST_NAMES[i % len(FIRST_NAMES)]} "
            f"{LAST_NAMES[i % len(LAST_NAMES)]}"
        )

        email = f"faculty{idx + 1}@college.edu"

        dept = DEPARTMENTS[i % len(DEPARTMENTS)][0]

        user = (
            db.query(User)
            .filter(User.email == email)
            .first()
        )

        if not user:

            user = User(
                email=email,
                password_hash=hash_password("faculty123"),
                role=UserRole.FACULTY,
            )

            db.add(user)
            db.flush()

        faculty = (
            db.query(Faculty)
            .filter(Faculty.email == email)
            .first()
        )

        if not faculty:

            faculty = Faculty(
                user_id=user.id,
                name=name,
                email=email,
                department=dept,
            )

            db.add(faculty)
            db.flush()

        faculty_records.append(faculty)

    # =========================================================
    # SUBJECTS
    # =========================================================

    subjects = []

    for i, (subject_name, subject_code) in enumerate(SUBJECTS):

        subject = (
            db.query(Subject)
            .filter(Subject.code == subject_code)
            .first()
        )

        if not subject:

            subject = Subject(
                name=subject_name,
                code=subject_code,
                branch="CSE AI",
                class_id=cse_class.id,
                faculty_id=faculty_records[
                    i % len(faculty_records)
                ].id,
            )

            db.add(subject)
            db.flush()

        subjects.append(subject)

    # =========================================================
    # HRISHABH BAJPAI
    # =========================================================

    hrishabh = (
        db.query(Student)
        .filter(
            Student.roll_number == "2500971520093"
        )
        .first()
    )

    if not hrishabh:

        hrishabh = Student(
            full_name="Hrishabh Bajpai",
            roll_number="2500971520093",
            branch="CSE AI",
            class_section="CSE AI",
            semester="1st Semester",
            email="hrishabh.bajpai@student.edu",
            phone="9876543210",
            face_status=FaceStatus.NOT_REGISTERED,
            class_id=cse_class.id,
        )

        db.add(hrishabh)
        db.flush()

    # =========================================================
    # HRISHABH STUDENT LOGIN
    # =========================================================

    student_user = (
        db.query(User)
        .filter(
            User.email == "hrishabh.bajpai@student.edu"
        )
        .first()
    )

    if not student_user:

        student_user = User(
            email="hrishabh.bajpai@student.edu",
            password_hash=hash_password("student123"),
            role=UserRole.STUDENT,
        )

        db.add(student_user)
        db.flush()

    # Only connect user if currently missing
    if hrishabh.user_id is None:

        hrishabh.user_id = student_user.id

    # =========================================================
    # OTHER 99 STUDENTS
    # =========================================================

    for i in range(100):

        first_name = FIRST_NAMES[
            i % len(FIRST_NAMES)
        ]

        last_name = LAST_NAMES[
            i % len(LAST_NAMES)
        ]

        roll_number = (
            f"25009715{20000 + i:05d}"
        )
        if roll_number == "2500971520093":
         continue

        existing_student = (
            db.query(Student)
            .filter(
                Student.roll_number == roll_number
            )
            .first()
        )

        # Student already exists → do nothing
        if existing_student:
            continue

        student = Student(
            full_name=f"{first_name} {last_name}",
            roll_number=roll_number,
            branch="CSE AI",
            class_section="CSE AI",
            semester="1st Semester",
            email=(
                f"{first_name.lower()}."
                f"{last_name.lower()}"
                f"{i}@student.edu"
            ),
            face_status=FaceStatus.NOT_REGISTERED,
            class_id=cse_class.id,
        )

        db.add(student)

    # =========================================================
    # SAVE
    # =========================================================

    db.commit()

    print("Database seed completed successfully.")


def init_db():

    # Create tables if they don't exist
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()

    try:
        seed_database(db)

    finally:
        db.close()


if __name__ == "__main__":
    init_db()