"""Enroll a face for a registered account. Run from the project root."""
from getpass import getpass
from pathlib import Path
import sys

import cv2
from ultralytics import YOLO

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from gui import auth
from gui.store import Store
from gui.face_camera import get_features

MODELS = Path(__file__).resolve().parents[1] / ".data" / "models"


def main():
    store = Store()
    email = input("Account email: ").strip().lower()
    password = getpass("Account password: ")
    user = auth.authenticate_password(store, email, password)
    if user is None:
        print("Wrong email or password. No face data saved.")
        return

    print("This will save a numerical face template in .data/store.json.")
    answer = input("Do you want to save it? Type yes to continue: ")
    if answer.strip().lower() != "yes":
        print("Canceled. No face data saved.")
        return

    files = [
        MODELS / "yolov8n-face.pt",
        MODELS / "face_detection_yunet_2023mar.onnx",
        MODELS / "face_recognition_sface_2021dec.onnx",
    ]
    for file in files:
        if not file.is_file():
            print("Missing model:", file)
            return

    yolo = YOLO(str(files[0]))
    detector = cv2.FaceDetectorYN.create(str(files[1]), "", (320, 320))
    recognizer = cv2.FaceRecognizerSF.create(str(files[2]), "")
    camera = cv2.VideoCapture(0)
    if not camera.isOpened():
        print("Could not open the camera.")
        return

    print("Look into the camera. Press E to save one scan, or Q to quit.")
    try:
        while True:
            ok, frame = camera.read()
            if not ok:
                print("Could not read the camera.")
                return

            faces = yolo.predict(frame, conf=0.5, imgsz=640, verbose=False)[0].boxes
            display = frame.copy()
            for face in faces:
                x1, y1, x2, y2 = map(int, face.xyxy[0].tolist())
                cv2.rectangle(display, (x1, y1), (x2, y2), (0, 255, 0), 2)
            cv2.putText(display, "E = save face   Q = quit", (15, 35),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            cv2.imshow("Enroll face", display)
            key = cv2.waitKey(1) & 0xFF

            if key == ord("q"):
                print("Canceled. No face data saved.")
                break
            if key != ord("e"):
                continue
            if len(faces) != 1:
                print("Make sure exactly one face is visible.")
                continue
            features = get_features(frame, faces[0], detector, recognizer)
            if features is None:
                print("Face was not clear. Try again.")
                continue

            try:
                store.add_face_template(user.email, features.flatten().tolist())
            except ValueError as error:
                print(error)
                break
            print("Saved one face scan to your account.")
            break
    finally:
        camera.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
