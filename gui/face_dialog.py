"""Webcam dialog for ANJS facial login."""
import time
from threading import Event

from PySide6.QtCore import QThread, Qt, Signal
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import QDialog, QLabel, QPushButton, QVBoxLayout

from .auth import authenticate_face

SCAN_SECONDS = 25


class FaceScanWorker(QThread):
    preview = Signal(QImage)
    status = Signal(str)
    matched = Signal(object)

    def __init__(self, store):
        super().__init__()
        self.store = store
        self._stop = Event()

    def stop(self):
        self._stop.set()

    def run(self):
        camera = None
        try:
            # Import the AI tools here so password login still works without them.
            import cv2
            from ultralytics import YOLO
            from .face_camera import (YOLO_FILE, YUNET_FILE, SFACE_FILE,
                                      get_features, missing_model)

            missing = missing_model()
            if missing:
                self.status.emit(f"Missing model: {missing}. See FACE_ID_SETUP.md.")
                return

            self.status.emit("Loading face models...")
            yolo = YOLO(str(YOLO_FILE))
            detector = cv2.FaceDetectorYN.create(str(YUNET_FILE), "", (320, 320))
            recognizer = cv2.FaceRecognizerSF.create(str(SFACE_FILE), "")

            if self._stop.is_set():
                return
            camera = cv2.VideoCapture(0)
            if not camera.isOpened():
                self.status.emit("Camera unavailable. Check permissions or use your password.")
                return

            self.status.emit("Look at the camera. Keep only your face in view.")
            start = time.monotonic()
            last_user = None
            matching_frames = 0
            frame_number = 0

            while not self._stop.is_set() and time.monotonic() - start < SCAN_SECONDS:
                ok, frame = camera.read()
                if not ok:
                    self.status.emit("Could not read the camera. Try password login.")
                    return

                # Show the live camera without using an extra OpenCV window.
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                h, w = rgb.shape[:2]
                picture = QImage(rgb.data, w, h, rgb.strides[0],
                                 QImage.Format.Format_RGB888).copy()
                self.preview.emit(picture)

                frame_number += 1
                if frame_number % 3 != 0:
                    continue

                boxes = yolo.predict(frame, conf=0.5, imgsz=640, verbose=False)[0].boxes
                if len(boxes) != 1:
                    matching_frames = 0
                    self.status.emit("Keep exactly one face in view.")
                    continue

                features = get_features(frame, boxes[0], detector, recognizer)
                if features is None:
                    matching_frames = 0
                    self.status.emit("Face not clear. Look toward the camera.")
                    continue

                user = authenticate_face(self.store, features.flatten().tolist())
                if user is None:
                    matching_frames = 0
                    self.status.emit("Face not recognized. Keep looking or use password.")
                    continue

                # Require two matching scans, not just one lucky frame.
                matching_frames = matching_frames + 1 if user.email == last_user else 1
                last_user = user.email
                if matching_frames >= 2 and not self._stop.is_set():
                    self.matched.emit(user)
                    return

                self.status.emit("Face found. Hold still for one more scan...")

            if not self._stop.is_set():
                self.status.emit("Scan timed out. Close this window and try again.")

        except Exception as error:
            # Keep the GUI open if camera/AI libraries fail.
            self.status.emit(f"Face scan failed: {error}")
        finally:
            if camera is not None:
                camera.release()


class FaceScanDialog(QDialog):
    def __init__(self, store, parent=None):
        super().__init__(parent)
        self.setWindowTitle("ANJS Face Login")
        self.resize(470, 430)
        self.user = None

        layout = QVBoxLayout(self)
        self.video = QLabel("Starting camera...")
        self.video.setMinimumSize(400, 300)
        self.video.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.video.setStyleSheet("background: #141923; color: white;")
        layout.addWidget(self.video)
        self.message = QLabel("Loading camera...")
        self.message.setWordWrap(True)
        layout.addWidget(self.message)
        close_button = QPushButton("Cancel / use password")
        close_button.clicked.connect(self.reject)
        layout.addWidget(close_button)

        self.worker = FaceScanWorker(store)
        self.worker.preview.connect(self.show_frame)
        self.worker.status.connect(self.message.setText)
        self.worker.matched.connect(self.face_found)
        self.worker.start()

    def show_frame(self, image):
        self.video.setPixmap(QPixmap.fromImage(image).scaled(
            self.video.size(), Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation))

    def face_found(self, user):
        self.user = user
        self.accept()

    def done(self, result):
        # Release the webcam when the user logs in or closes the window.
        self.worker.stop()
        self.worker.wait()
        super().done(result)
