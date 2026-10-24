"""Test login with the face saved in the local bookstore account."""
from pathlib import Path
import sys

import cv2
from ultralytics import YOLO

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT))

from gui.face_login import find_user_by_face
from gui.store import Store
from gui.face_camera import get_features

MODELS = PROJECT / ".data" / "models"


def main():
    names = ["yolov8n-face.pt", "face_detection_yunet_2023mar.onnx",
             "face_recognition_sface_2021dec.onnx"]
    files = [MODELS / name for name in names]
    for file in files:
        if not file.is_file():
            print("Missing model:", file)
            return

    store = Store()
    if not store.enrolled_face_accounts():
        print("No face has been enrolled yet. Run enroll_face.py first.")
        return

    yolo = YOLO(str(files[0]))
    detector = cv2.FaceDetectorYN.create(str(files[1]), "", (320, 320))
    recognizer = cv2.FaceRecognizerSF.create(str(files[2]), "")
    camera = cv2.VideoCapture(0)
    if not camera.isOpened():
        print("Could not open the webcam.")
        return

    print("Look at the camera. Press V to verify, or Q to quit.")
    try:
        while True:
            ok, frame = camera.read()
            if not ok:
                print("Could not read the webcam.")
                break

            boxes = yolo.predict(frame, conf=0.5, imgsz=640, verbose=False)[0].boxes
            display = frame.copy()
            for box in boxes:
                x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
                cv2.rectangle(display, (x1, y1), (x2, y2), (0, 255, 0), 2)

            cv2.putText(display, "V = verify   Q = quit", (15, 35),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.75, (0, 255, 0), 2)
            cv2.imshow("ANJS Face Login Test", display)
            key = cv2.waitKey(1) & 0xFF

            if key == ord("q"):
                break
            if key != ord("v"):
                continue
            if len(boxes) != 1:
                print("Make sure exactly one face is visible.")
                continue

            features = get_features(frame, boxes[0], detector, recognizer)
            if features is None:
                print("Face was not clear. Try again.")
                continue

            user = find_user_by_face(store, features.flatten().tolist())
            if user is None:
                print("Face not recognized. Try again or use your password.")
            else:
                print(f"Face recognized: {user.name} ({user.email})")
                print("Test passed. Next step: connect this to the GUI login button.")
                break
    finally:
        camera.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
