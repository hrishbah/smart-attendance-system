import os
import ssl
import urllib.request
from typing import Optional
from dataclasses import dataclass

import numpy as np
import cv2

from app.config import get_settings


settings = get_settings()


# =============================================================
# MODEL URLS
# =============================================================

MODEL_URLS = {
    "yunet": (
        "https://github.com/opencv/opencv_zoo/raw/main/"
        "models/face_detection_yunet/"
        "face_detection_yunet_2023mar.onnx"
    ),
    "sface": (
        "https://github.com/opencv/opencv_zoo/raw/main/"
        "models/face_recognition_sface/"
        "face_recognition_sface_2021dec.onnx"
    ),
}


# =============================================================
# DATA CLASSES
# =============================================================

@dataclass
class FaceDetectionResult:
    detected: bool
    bbox: Optional[tuple[int, int, int, int]]
    confidence: float
    message: str
    face_count: int
    quality_score: float = 0.0


@dataclass
class FaceQualityResult:
    acceptable: bool
    message: str
    score: float


@dataclass
class RecognitionMatch:
    student_id: int
    confidence: float
    distance: float


# =============================================================
# FACE SERVICE
# =============================================================

class FaceService:

    def __init__(self):

        self.models_dir = os.path.join(
            settings.upload_dir,
            "models",
        )

        os.makedirs(
            self.models_dir,
            exist_ok=True,
        )

        self.detector_path = os.path.join(
            self.models_dir,
            "face_detection_yunet_2023mar.onnx",
        )

        self.recognizer_path = os.path.join(
            self.models_dir,
            "face_recognition_sface_2021dec.onnx",
        )

        self._detector: Optional[cv2.FaceDetectorYN] = None
        self._recognizer: Optional[cv2.FaceRecognizerSF] = None

        self._ensure_models()


    # =========================================================
    # DOWNLOAD MODELS
    # =========================================================

    def _ensure_models(self):

        for key, url in MODEL_URLS.items():

            if key == "yunet":
                path = self.detector_path
            else:
                path = self.recognizer_path

            if os.path.exists(path):
                continue

            print(f"Downloading {key} face model...")

            ctx = ssl.create_default_context()

            try:
                import certifi

                ctx.load_verify_locations(
                    certifi.where()
                )

            except ImportError:

                ctx.check_hostname = False
                ctx.verify_mode = ssl.CERT_NONE

            try:

                with urllib.request.urlopen(
                    url,
                    context=ctx,
                ) as response:

                    with open(
                        path,
                        "wb",
                    ) as output:

                        output.write(
                            response.read()
                        )

                print(
                    f"{key} model downloaded successfully."
                )

            except Exception as e:

                print(
                    f"Failed to download {key} model: {e}"
                )

                raise


    # =========================================================
    # GET FACE DETECTOR
    # =========================================================

    def _get_detector(
        self,
        width: int,
        height: int,
    ) -> cv2.FaceDetectorYN:

        if self._detector is None:

            self._detector = cv2.FaceDetectorYN.create(
                self.detector_path,
                "",
                (width, height),
                score_threshold=0.6,
                nms_threshold=0.3,
                top_k=5000,
            )

        else:

            self._detector.setInputSize(
                (width, height)
            )

        return self._detector


    # =========================================================
    # GET FACE RECOGNIZER
    # =========================================================

    def _get_recognizer(self) -> cv2.FaceRecognizerSF:

        if self._recognizer is None:

            self._recognizer = cv2.FaceRecognizerSF.create(
                self.recognizer_path,
                "",
            )

        return self._recognizer


    # =========================================================
    # DECODE IMAGE
    # =========================================================

    def decode_image(
        self,
        image_bytes: bytes,
    ) -> np.ndarray:

        arr = np.frombuffer(
            image_bytes,
            dtype=np.uint8,
        )

        image = cv2.imdecode(
            arr,
            cv2.IMREAD_COLOR,
        )

        if image is None:

            raise ValueError(
                "Invalid image data"
            )

        return image


    # =========================================================
    # CLAMP BOUNDING BOX
    # =========================================================

    def _clamp_bbox(
        self,
        image: np.ndarray,
        bbox: tuple[int, int, int, int],
    ) -> tuple[int, int, int, int]:

        h, w = image.shape[:2]

        x, y, fw, fh = bbox

        x = max(
            0,
            min(x, w - 1),
        )

        y = max(
            0,
            min(y, h - 1),
        )

        fw = max(
            1,
            min(fw, w - x),
        )

        fh = max(
            1,
            min(fh, h - y),
        )

        return (
            x,
            y,
            fw,
            fh,
        )


    # =========================================================
    # QUALITY SCORE
    # =========================================================

    def _calculate_quality(
        self,
        image: np.ndarray,
        bbox: tuple[int, int, int, int],
    ) -> float:

        x, y, fw, fh = self._clamp_bbox(
            image,
            bbox,
        )

        h, w = image.shape[:2]

        gray = cv2.cvtColor(
            image,
            cv2.COLOR_BGR2GRAY,
        )

        face_roi = gray[
            y:y + fh,
            x:x + fw,
        ]

        if face_roi.size == 0:
            return 0.0


        # -----------------------------------------------------
        # FACE SIZE
        # -----------------------------------------------------

        face_area = fw * fh
        image_area = w * h

        size_ratio = face_area / image_area

        size_score = min(
            1.0,
            size_ratio / 0.05,
        )


        # -----------------------------------------------------
        # SHARPNESS
        # -----------------------------------------------------

        blur_value = cv2.Laplacian(
            face_roi,
            cv2.CV_64F,
        ).var()

        blur_score = min(
            1.0,
            blur_value / 80.0,
        )


        # -----------------------------------------------------
        # BRIGHTNESS
        # -----------------------------------------------------

        brightness = float(
            np.mean(face_roi)
        )

        brightness_score = max(
            0.0,
            1.0
            - abs(brightness - 128.0)
            / 128.0,
        )


        # -----------------------------------------------------
        # FINAL SCORE
        # -----------------------------------------------------

        score = (
            size_score * 0.30
            + blur_score * 0.45
            + brightness_score * 0.25
        )

        return float(
            max(
                0.0,
                min(
                    1.0,
                    score,
                ),
            )
        )


    # =========================================================
    # DETECT FACE
    # =========================================================

    def detect_faces(
        self,
        image: np.ndarray,
    ) -> FaceDetectionResult:

        h, w = image.shape[:2]

        detector = self._get_detector(
            w,
            h,
        )

        _, faces = detector.detect(
            image
        )


        # -----------------------------------------------------
        # NO FACE
        # -----------------------------------------------------

        if faces is None or len(faces) == 0:

            return FaceDetectionResult(
                detected=False,
                bbox=None,
                confidence=0.0,
                message="Face not detected",
                face_count=0,
                quality_score=0.0,
            )


        face_count = len(faces)


        # -----------------------------------------------------
        # MULTIPLE FACES
        # -----------------------------------------------------

        if face_count > 1:

            return FaceDetectionResult(
                detected=False,
                bbox=None,
                confidence=0.0,
                message="Only one face should be visible",
                face_count=face_count,
                quality_score=0.0,
            )


        # -----------------------------------------------------
        # FACE DATA
        # -----------------------------------------------------

        face = faces[0]

        x = int(face[0])
        y = int(face[1])
        fw = int(face[2])
        fh = int(face[3])

        confidence = float(
            face[-1]
        )


        # -----------------------------------------------------
        # FACE SIZE
        # -----------------------------------------------------

        min_face_size = min(
            w,
            h,
        ) * 0.10

        if fw < min_face_size or fh < min_face_size:

            return FaceDetectionResult(
                detected=False,
                bbox=(x, y, fw, fh),
                confidence=confidence,
                message="Move closer",
                face_count=1,
                quality_score=0.0,
            )


        # -----------------------------------------------------
        # VALID BBOX
        # -----------------------------------------------------

        bbox = self._clamp_bbox(
            image,
            (
                x,
                y,
                fw,
                fh,
            ),
        )

        x, y, fw, fh = bbox


        # -----------------------------------------------------
        # FACE REGION
        # -----------------------------------------------------

        gray = cv2.cvtColor(
            image,
            cv2.COLOR_BGR2GRAY,
        )

        face_roi = gray[
            y:y + fh,
            x:x + fw,
        ]

        if face_roi.size == 0:

            return FaceDetectionResult(
                detected=False,
                bbox=bbox,
                confidence=confidence,
                message="Invalid face region",
                face_count=1,
                quality_score=0.0,
            )


        # -----------------------------------------------------
        # BLUR CHECK
        # -----------------------------------------------------

        blur_value = cv2.Laplacian(
            face_roi,
            cv2.CV_64F,
        ).var()


        # MacBook webcam can sometimes give
        # lower Laplacian variance than expected.
        #
        # Therefore keep this threshold deliberately low.

        if blur_value < 8:

            quality_score = self._calculate_quality(
                image,
                bbox,
            )

            return FaceDetectionResult(
                detected=False,
                bbox=bbox,
                confidence=confidence,
                message="Image too blurry - hold still",
                face_count=1,
                quality_score=quality_score,
            )


        # -----------------------------------------------------
        # BRIGHTNESS
        # -----------------------------------------------------

        brightness = float(
            np.mean(face_roi)
        )


        if brightness < 30:

            quality_score = self._calculate_quality(
                image,
                bbox,
            )

            return FaceDetectionResult(
                detected=False,
                bbox=bbox,
                confidence=confidence,
                message="Improve lighting",
                face_count=1,
                quality_score=quality_score,
            )


        if brightness > 240:

            quality_score = self._calculate_quality(
                image,
                bbox,
            )

            return FaceDetectionResult(
                detected=False,
                bbox=bbox,
                confidence=confidence,
                message="Too much light - reduce glare",
                face_count=1,
                quality_score=quality_score,
            )


        # -----------------------------------------------------
        # QUALITY SCORE
        # -----------------------------------------------------

        quality_score = self._calculate_quality(
            image,
            bbox,
        )


        # -----------------------------------------------------
        # ACCEPTABLE QUALITY
        # -----------------------------------------------------

        if quality_score < 0.25:

            return FaceDetectionResult(
                detected=False,
                bbox=bbox,
                confidence=confidence,
                message="Poor quality - adjust position",
                face_count=1,
                quality_score=quality_score,
            )


        # -----------------------------------------------------
        # SUCCESS
        # -----------------------------------------------------

        return FaceDetectionResult(
            detected=True,
            bbox=bbox,
            confidence=confidence,
            message="Face detected",
            face_count=1,
            quality_score=quality_score,
        )


    # =========================================================
    # ASSESS QUALITY
    # =========================================================

    def assess_quality(
        self,
        image: np.ndarray,
        bbox: tuple[int, int, int, int],
    ) -> FaceQualityResult:

        detection = self.detect_faces(
            image
        )

        if not detection.detected:

            return FaceQualityResult(
                acceptable=False,
                message=detection.message,
                score=detection.quality_score,
            )

        score = self._calculate_quality(
            image,
            bbox,
        )

        if score < 0.25:

            return FaceQualityResult(
                acceptable=False,
                message="Poor quality - adjust position",
                score=score,
            )

        return FaceQualityResult(
            acceptable=True,
            message="Good quality",
            score=score,
        )


    # =========================================================
    # INTERNAL FACE DETECTION
    # =========================================================

    def _detect_face_row(
        self,
        image: np.ndarray,
    ) -> Optional[np.ndarray]:

        h, w = image.shape[:2]

        detector = self._get_detector(
            w,
            h,
        )

        _, faces = detector.detect(
            image
        )

        if faces is None or len(faces) == 0:
            return None

        if len(faces) > 1:
            return None

        return faces[0]


    # =========================================================
    # EXTRACT FACE EMBEDDING
    # =========================================================

    def extract_embedding(
        self,
        image: np.ndarray,
        bbox: Optional[
            tuple[int, int, int, int]
        ] = None,
    ) -> Optional[np.ndarray]:

        face_row = self._detect_face_row(
            image
        )

        if face_row is None:
            return None


        # -----------------------------------------------------
        # USE PROVIDED BBOX
        # -----------------------------------------------------

        if bbox is not None:

            x, y, fw, fh = self._clamp_bbox(
                image,
                bbox,
            )

            face_row[0] = x
            face_row[1] = y
            face_row[2] = fw
            face_row[3] = fh


        # -----------------------------------------------------
        # FACE RECOGNIZER
        # -----------------------------------------------------

        recognizer = self._get_recognizer()


        # Align face before generating embedding.

        face_align = recognizer.alignCrop(
            image,
            face_row,
        )


        feature = recognizer.feature(
            face_align
        )


        return feature.flatten()


    # =========================================================
    # EMBEDDING -> BYTES
    # =========================================================

    def embedding_to_bytes(
        self,
        embedding: np.ndarray,
    ) -> bytes:

        return embedding.astype(
            np.float32
        ).tobytes()


    # =========================================================
    # BYTES -> EMBEDDING
    # =========================================================

    def bytes_to_embedding(
        self,
        data: bytes,
    ) -> np.ndarray:

        return np.frombuffer(
            data,
            dtype=np.float32,
        )


    # =========================================================
    # COMPARE TWO EMBEDDINGS
    # =========================================================

    def compare_embeddings(
        self,
        query: np.ndarray,
        stored: np.ndarray,
    ) -> float:

        recognizer = self._get_recognizer()


        q = query.reshape(
            1,
            -1,
        ).astype(
            np.float32
        )

        s = stored.reshape(
            1,
            -1,
        ).astype(
            np.float32
        )


        # IMPORTANT:
        #
        # FR_COSINE returns COSINE SIMILARITY.
        #
        # Higher value = MORE similar.
        #
        # This is NOT a distance.
        #
        # Therefore:
        #
        # 0.90 -> very similar
        # 0.70 -> reasonably similar
        # 0.40 -> weak
        #
        # The previous code treated this value as a distance,
        # which reversed the matching logic.

        similarity = recognizer.match(
            q,
            s,
            cv2.FaceRecognizerSF_FR_COSINE,
        )


        return float(
            similarity
        )


    # =========================================================
    # FIND BEST MATCH
    # =========================================================

    def find_best_match(
        self,
        query_embedding: np.ndarray,
        candidates: list[
            tuple[int, list[np.ndarray]]
        ],
        threshold: Optional[float] = None,
    ) -> Optional[RecognitionMatch]:

        if not candidates:
            return None


        # -----------------------------------------------------
        # COSINE SIMILARITY THRESHOLD
        # -----------------------------------------------------
        #
        # IMPORTANT:
        #
        # SFace cosine similarity:
        #
        # HIGHER = BETTER
        #
        # So we look for the HIGHEST similarity.
        #

        if threshold is None:

            threshold = getattr(
                settings,
                "face_recognition_threshold",
                0.40,
            )


        # Make sure threshold is a float.

        threshold = float(
            threshold
        )


        # -----------------------------------------------------
        # SAFETY
        # -----------------------------------------------------
        #
        # Cosine similarity is normally between -1 and 1.
        #

        threshold = max(
            -1.0,
            min(
                1.0,
                threshold,
            ),
        )


        best_student_id: Optional[int] = None

        best_similarity = -1.0


        # -----------------------------------------------------
        # CHECK EVERY REGISTERED EMBEDDING
        # -----------------------------------------------------

        for student_id, embeddings in candidates:

            if not embeddings:
                continue


            for embedding in embeddings:

                if embedding is None:
                    continue


                try:

                    similarity = self.compare_embeddings(
                        query_embedding,
                        embedding,
                    )

                except Exception as e:

                    print(
                        f"Embedding comparison error "
                        f"for student {student_id}: {e}"
                    )

                    continue


                print(
                    f"Face comparison -> "
                    f"student={student_id}, "
                    f"similarity={similarity:.4f}"
                )


                # HIGHER similarity is better.

                if similarity > best_similarity:

                    best_similarity = similarity

                    best_student_id = student_id


        # -----------------------------------------------------
        # NO VALID MATCH
        # -----------------------------------------------------

        if best_student_id is None:

            print(
                "Face recognition: no valid candidate match"
            )

            return None


        # -----------------------------------------------------
        # BELOW THRESHOLD
        # -----------------------------------------------------

        if best_similarity < threshold:

            print(
                f"Face recognition rejected: "
                f"best_similarity={best_similarity:.4f}, "
                f"threshold={threshold:.4f}"
            )

            return None


        # -----------------------------------------------------
        # CONFIDENCE
        # -----------------------------------------------------

        confidence = (
            best_similarity * 100.0
        )

        confidence = max(
            0.0,
            min(
                100.0,
                confidence,
            ),
        )


        print(
            f"FACE MATCH FOUND -> "
            f"student={best_student_id}, "
            f"similarity={best_similarity:.4f}, "
            f"confidence={confidence:.2f}%"
        )


        # -----------------------------------------------------
        # RETURN MATCH
        # -----------------------------------------------------
        #
        # The existing RecognitionMatch class calls the
        # third field "distance", but for SFace COSINE
        # we are actually storing similarity here.
        #
        # We keep the field name so the rest of your
        # application does not break.

        return RecognitionMatch(
            student_id=best_student_id,
            confidence=confidence,
            distance=best_similarity,
        )


    # =========================================================
    # DRAW FACE BOX
    # =========================================================

    def draw_face_box(
        self,
        image: np.ndarray,
        bbox: tuple[int, int, int, int],
        color=(0, 255, 0),
    ) -> np.ndarray:

        result = image.copy()

        x, y, width, height = bbox


        cv2.rectangle(
            result,
            (x, y),
            (
                x + width,
                y + height,
            ),
            color,
            2,
        )


        return result


# =============================================================
# SINGLETON SERVICE
# =============================================================

_service: Optional["FaceService"] = None


def get_face_service() -> "FaceService":

    global _service

    if _service is None:

        _service = FaceService()

    return _service


# =============================================================
# PROXY
# =============================================================

class _FaceServiceProxy:

    def __getattr__(
        self,
        name,
    ):

        return getattr(
            get_face_service(),
            name,
        )


face_service = _FaceServiceProxy()