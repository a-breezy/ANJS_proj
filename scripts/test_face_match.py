"""Temporary webcam test for YOLO face detection and SFace recognition."""
from pathlib import Path

import cv2
from ultralytics import YOLO

MODELS = Path(__file__).resolve().parents[1] / ".data" / "models"
YOLO_FILE = MODELS / "yolov8n-face.pt"
YUNET_FILE = MODELS / "face_detection_yunet_2023mar.onnx"
SFACE_FILE = MODELS / "face_recognition_sface_2021dec.onnx"


def get_features(frame, box, landmarks, recognizer):
    """Find facial landmarks and turn one detected face into numbers."""
    height, width = frame.shape[:2]
    x1, y1, x2, y2 = (int(n) for n in box.xyxy[0].tolist())
    padding = int(max(x2 - x1, y2 - y1) * 0.2)
    x1, y1 = max(0, x1 - padding), max(0, y1 - padding)
    x2, y2 = min(width, x2 + padding), min(height, y2 + padding)
    crop = frame[y1:y2, x1:x2]
    if crop.size == 0:
        return None

    crop = cv2.resize(crop, (320, 320))
    landmarks.setInputSize((320, 320))
    _, faces = landmarks.detect(crop)
    if faces is None:
        return None

    face = max(faces, key=lambda f: f[-1])
    aligned_face = recognizer.alignCrop(crop, face)
    return recognizer.feature(aligned_face)


def main():
    for filename in (YOLO_FILE, YUNET_FILE, SFACE_FILE):
        if not filename.exists():
            print(f"Missing model: {filename}")
            return

    yolo = YOLO(str(YOLO_FILE))
    landmarks = cv2.FaceDetectorYN.create(str(YUNET_FILE), "", (320, 320))
    recognizer = cv2.FaceRecognizerSF.create(str(SFACE_FILE), "")
    camera = cv2.VideoCapture(0)
    if not camera.isOpened():
        print("Camera could not open.")
        return

    saved_features = None
    print("E = remember the face in front of the camera")
    print("V = compare a new scan with that face")
    print("Q = quit")

    try:
        while True:
            ok, frame = camera.read()
            if not ok:
                print("Couldn't read from the camera.")
                break

            result = yolo.predict(frame, conf=0.5, imgsz=640, verbose=False)[0]
            boxes = result.boxes
            display = frame.copy()
            for box in boxes:
                x1, y1, x2, y2 = (int(n) for n in box.xyxy[0].tolist())
                cv2.rectangle(display, (x1, y1), (x2, y2), (0, 255, 0), 2)

            cv2.putText(display, "E = enroll  V = verify  Q = quit",
                        (15, 35), cv2.FONT_HERSHEY_SIMPLEX,
                        0.65, (0, 255, 0), 2)
            cv2.imshow("Face recognition test", display)
            key = cv2.waitKey(1) & 0xFF

            if key == ord("q"):
                break
            if key not in (ord("e"), ord("v")):
                continue
            if len(boxes) != 1:
                print("Please make sure exactly one face is visible.")
                continue

            features = get_features(frame, boxes[0], landmarks, recognizer)
            if features is None:
                print("Face wasn't clear enough. Look at the camera and try again.")
            elif key == ord("e"):
                saved_features = features
                print("Face recorded temporarily. Press V to compare.")
            elif saved_features is None:
                print("Press E first to record a face.")
            else:
                score = recognizer.match(saved_features, features,
                                         cv2.FaceRecognizerSF_FR_COSINE)
                print(f"Similarity score: {score:.3f} (higher = more similar)")

    finally:
        camera.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
