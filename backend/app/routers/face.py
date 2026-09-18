import os
import uuid
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from app.database import get_db
from app.auth import require_roles
from app.models import User, UserRole, Student, FaceStatus, FaceEmbedding
from app.schemas import FaceDetectResponse, FaceRegisterResponse
from app.services.face_service import face_service
from app.config import get_settings

router = APIRouter(prefix="/face", tags=["face"])
settings = get_settings()


@router.post("/detect", response_model=FaceDetectResponse)
async def detect_face(
    image: UploadFile = File(...),
    user: User = Depends(require_roles(UserRole.ADMIN, UserRole.FACULTY)),
):
    try:
        contents = await image.read()
        img = face_service.decode_image(contents)
        result = face_service.detect_faces(img)
        quality_score = None
        if result.bbox:
            quality = face_service.assess_quality(img, result.bbox)
            quality_score = quality.score
        bbox_dict = None
        if result.bbox:
            x, y, w, h = result.bbox
            bbox_dict = {"x": x, "y": y, "width": w, "height": h}
        return FaceDetectResponse(
            detected=result.detected,
            face_count=result.face_count,
            message=result.message,
            bbox=bbox_dict,
            quality_score=quality_score,
        )
    except Exception as e:
        raise HTTPException(400, f"Face detection failed: {str(e)}")


@router.post("/register/{student_id}", response_model=FaceRegisterResponse)
async def register_face(
    student_id: int,
    images: list[UploadFile] = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(UserRole.ADMIN)),
):
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(404, "Student not found")

    db.query(FaceEmbedding).filter(FaceEmbedding.student_id == student_id).delete()

    embeddings_saved = 0
    profile_saved = False
    profile_path = None

    for idx, upload in enumerate(images):
        contents = await upload.read()
        try:
            img = face_service.decode_image(contents)
        except ValueError:
            continue

        detection = face_service.detect_faces(img)
        if not detection.detected:
            continue

        quality = face_service.assess_quality(img, detection.bbox)
        if not quality.acceptable:
            continue

        embedding = face_service.extract_embedding(img, detection.bbox)
        if embedding is None:
            continue

        fe = FaceEmbedding(
            student_id=student_id,
            embedding=face_service.embedding_to_bytes(embedding),
            sample_index=embeddings_saved,
            quality_score=quality.score,
        )
        db.add(fe)
        embeddings_saved += 1

        if not profile_saved:
            photo_name = f"photos/{student_id}_{uuid.uuid4().hex[:8]}.jpg"
            photo_full = os.path.join(settings.upload_dir, photo_name)
            import cv2
            cv2.imwrite(photo_full, img)
            profile_path = photo_name
            profile_saved = True

    if embeddings_saved < settings.face_min_samples:
        db.rollback()
        raise HTTPException(
            400,
            f"Insufficient quality samples. Got {embeddings_saved}, need at least {settings.face_min_samples}. "
            "Ensure good lighting, one face visible, and hold still.",
        )

    student.face_status = FaceStatus.REGISTERED
    if profile_path:
        if student.profile_photo:
            old = os.path.join(settings.upload_dir, student.profile_photo)
            if os.path.exists(old):
                os.remove(old)
        student.profile_photo = profile_path

    db.commit()
    return FaceRegisterResponse(
        success=True,
        message="Face successfully registered.",
        samples_collected=embeddings_saved,
        profile_photo=profile_path,
    )


@router.delete("/register/{student_id}")
def delete_face_registration(
    student_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(UserRole.ADMIN)),
):
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(404, "Student not found")
    db.query(FaceEmbedding).filter(FaceEmbedding.student_id == student_id).delete()
    student.face_status = FaceStatus.NOT_REGISTERED
    db.commit()
    return {"message": "Face registration removed"}
