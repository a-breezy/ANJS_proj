
from pathlib import Path
from urllib.request import urlretrieve

import cv2
from ultralytics import YOLO

MODEL_FILE = Path(__file__).resolve().parents[1] / ".data" / "models" / "yolov8n-face.pt"

MODEL_URL = (
    "https://github.com/akanametov/yolo-face/releases/download/1.0.0/"
    "yolov8n-face.pt"
)


def main():
    if not MODEL_FILE.exists():
        print("Downloading the face detection model...")
        MODEL_FILE.parent.mkdir(parents=True, exist_ok=True)
        urlretrieve(MODEL_URL, MODEL_FILE)

    model = YOLO(str(MODEL_FILE))
    camera = cv2.VideoCapture(0)

    if not camera.isOpened():
        print("Could not open the webcam. Check camera permission and try again.")
        return

    print("Camera started. Press Q in the camera window to close it.")

    try:
        while True:
            working, frame = camera.read()

            if not working:
                print("Could not read a frame from the webcam.")
                break

            result = model.predict(frame, conf=0.5, imgsz=640, verbose=False)[0]
            faces = result.boxes

            for face in faces:
                x1, y1, x2, y2 = map(int, face.xyxy[0].tolist())
                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)

            count = len(faces)
            cv2.putText(frame, f"Faces detected: {count}", (20, 35),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

            cv2.imshow("YOLO face test - press Q to quit", frame)

            if cv2.waitKey(1) & 0xFF == ord("q"):
                break

    finally:
        camera.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
