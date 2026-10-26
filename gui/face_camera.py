"""Shared face feature extraction for enrollment and login."""
from pathlib import Path

MODELS = Path(__file__).resolve().parents[1] / ".data" / "models"
YOLO_FILE = MODELS / "yolov8n-face.pt"
YUNET_FILE = MODELS / "face_detection_yunet_2023mar.onnx"
SFACE_FILE = MODELS / "face_recognition_sface_2021dec.onnx"


def missing_model():
    """Return the first missing model filename, if any."""
    for file in (YOLO_FILE, YUNET_FILE, SFACE_FILE):
        if not file.is_file():
            return file.name
    return None


def get_features(frame, box, detector, recognizer):
    """Use facial landmarks to turn a YOLO face detection into 128 numbers."""
    import cv2

    height, width = frame.shape[:2]
    x1, y1, x2, y2 = (int(number) for number in box.xyxy[0].tolist())
    padding = int(max(x2 - x1, y2 - y1) * 0.2)
    x1, y1 = max(0, x1 - padding), max(0, y1 - padding)
    x2, y2 = min(width, x2 + padding), min(height, y2 + padding)
    crop = frame[y1:y2, x1:x2]
    if crop.size == 0:
        return None

    crop = cv2.resize(crop, (320, 320))
    detector.setInputSize((320, 320))
    _, faces = detector.detect(crop)
    if faces is None:
        return None

    face = max(faces, key=lambda face: face[-1])
    aligned = recognizer.alignCrop(crop, face)
    return recognizer.feature(aligned)
