# Smart Attendance System Using Face Recognition

A complete web application for automated attendance using real face recognition. Built with React, FastAPI, PostgreSQL, and OpenCV SFace.

## Features

- **Real face recognition** using OpenCV YuNet (detection) + SFace (embeddings)
- **Webcam-based** face registration with quality checks (10–20 samples)
- **Live attendance** with automatic student recognition
- **Duplicate prevention** via database unique constraints
- **Role-based access**: Admin, Faculty, Student
- **100 students + 50 faculty** seeded for testing
- **Reports** with CSV, Excel, and PDF export
- **Dark/light mode** modern SaaS UI

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 18, TypeScript, Tailwind CSS, Recharts |
| Backend | Python FastAPI, SQLAlchemy |
| Database | PostgreSQL 16 |
| Face Recognition | OpenCV (YuNet + SFace ONNX models) |
| Auth | JWT in HttpOnly cookies, bcrypt passwords |

## Prerequisites

| Tool | Required | Notes |
|------|----------|-------|
| Python 3.12+ | Yes | Tested on 3.14 (Apple Silicon) |
| Node.js 18+ | Yes | `brew install node` |
| Docker Desktop | Yes | For PostgreSQL |
| Webcam | Yes | For face registration/attendance |

Run `./check-env.sh` to verify your environment before starting.

## Quick Start

```bash
cd ~/Coding/smart-attendance-system

# 1. Install prerequisites (if missing)
brew install node
# Install Docker Desktop from https://docker.com/products/docker-desktop/

# 2. Full setup
./setup.sh

# 3. Start services (3 terminals)
docker compose up -d          # Terminal 1 (once)
./start-backend.sh            # Terminal 2 → http://localhost:8000
./start-frontend.sh           # Terminal 3 → http://localhost:5173

# 4. Verify API
./test-api.sh
```

## Demo Credentials

| Role | Email | Password |
|------|-------|----------|
| Admin | admin@attendance.edu | admin123 |
| Faculty | rajesh.kumar@college.edu | faculty123 |
| Student | hrishabh.bajpai@student.edu | student123 |

## End-to-End Demo Workflow

1. **Login as Admin** → `admin@attendance.edu` / `admin123`
2. **Students** → Find **Hrishabh Bajpai** (Roll: 2500971520093)
3. **Face Registration** → Select Hrishabh → Start Camera → Start Capture → Register Face
4. **Logout** → Login as Faculty → `rajesh.kumar@college.edu` / `faculty123`
5. **Attendance** → Select **Mathematics 2** → Start Attendance → Start Camera → Start Scanning
6. Stand in front of camera → System recognizes Hrishabh → Attendance marked
7. Scan again → Shows **Already Present**
8. Unregistered person → Shows **Unknown Face** (no attendance marked)
9. **Reports** → View/export attendance data

## API Documentation

With backend running: **http://localhost:8000/docs**

## Project Structure

```
smart-attendance-system/
├── backend/
│   ├── app/
│   │   ├── main.py           # FastAPI entry
│   │   ├── models.py         # SQLAlchemy models
│   │   ├── auth.py           # JWT + bcrypt
│   │   ├── seed.py           # Sample data (100 students, 50 faculty)
│   │   ├── routers/          # API endpoints
│   │   └── services/
│   │       └── face_service.py  # OpenCV face recognition
│   └── requirements.txt
├── frontend/
│   └── src/
│       ├── pages/            # Dashboard, Attendance, Face Registration, etc.
│       ├── hooks/useWebcam.ts
│       └── api/client.ts
├── docker-compose.yml
└── .env.example
```

## Face Recognition Details

- **Detection**: YuNet ONNX model (face bounding box + landmarks)
- **Embedding**: SFace 128-dimensional feature vector
- **Matching**: Cosine distance, threshold 0.363 (configurable via `FACE_RECOGNITION_THRESHOLD`)
- **Quality checks**: Face size, blur (Laplacian variance), lighting, single-face enforcement
- **No fake embeddings**: Only students with webcam-registered faces can be recognized

## Security

- Passwords hashed with bcrypt
- JWT stored in HttpOnly cookies
- Face embeddings never exposed via public API
- Role-based route protection
- Parameterized ORM queries
- Unique constraint prevents duplicate attendance

## Environment Variables

See `.env.example` for all configuration options.

## License

MIT
