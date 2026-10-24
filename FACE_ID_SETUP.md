# ANJS Face ID setup and testing

Face ID is a local class-project prototype. YOLO detects a face, YuNet locates facial landmarks, and SFace compares a 128-number face representation with scans enrolled in the bookstore's local account store.

## 1. Install dependencies

From the `ANJS_proj` folder in VS Code:

**Windows (PowerShell)**

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

**macOS (Terminal)**

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

If you already created `.venv`, activate it and run only the `pip install` command. Choose `.venv` with **Python: Select Interpreter** in VS Code if imports fail.

## 2. Download model files

Create `.data/models` in the project root, then put these **exact filenames** inside:

- `yolov8n-face.pt` — from [akanametov/yolo-face](https://github.com/akanametov/yolo-face) (find the `yolov8n-face.pt` model link in the README)
- `face_detection_yunet_2023mar.onnx` — [OpenCV YuNet](https://huggingface.co/opencv/face_detection_yunet/blob/main/face_detection_yunet_2023mar.onnx)
- `face_recognition_sface_2021dec.onnx` — [OpenCV SFace](https://huggingface.co/opencv/face_recognition_sface/blob/main/face_recognition_sface_2021dec.onnx)

Download the **real binary file**, not an HTML page or Git LFS pointer. The `.data/` folder is ignored by Git. Do **not** commit model files, photos, or biometric templates.

Expected structure:

```text
ANJS_proj/
  .data/
    models/
      yolov8n-face.pt
      face_detection_yunet_2023mar.onnx
      face_recognition_sface_2021dec.onnx
  gui/
  scripts/
  tests/
```

## 3. Create a local account

```bash
python -m gui
```

In the app, choose **Sign in > Create an account**, enter your name, email, and a password (at least eight characters), and submit. You'll be signed in. If you're already signed in, use **Account > Sign out** for the login screen.

The account lives only on your computer in `.data/store.json`. Teammates must make their own accounts; there is no shared account database yet.

## 4. Enroll a face

Close the app or leave it open, then run:

```bash
python scripts/enroll_face.py
```

Enter the email and password you registered. Read the data storage prompt and type `yes` only if you want to enroll. Look toward the webcam and press **E** to save one face template (or **Q** to cancel). The enrolled numeric representation is saved in `.data/store.json`; the raw photo is not saved by the script.

You may enroll up to four samples. For example, one with glasses and another without glasses. Run the enrollment script again for each sample.

**Privacy:** treat `.data/store.json` as sensitive biometric data. It is not encrypted. Do not email or upload the file. The store has a `remove_face_templates(email)` method to remove biometric templates.

## 5. Log in using your face

```bash
python -m gui
```

If you're signed in, go to **Account > Sign out**. Choose **Sign in > Face > Scan my face**.

A separate ANJS Face Login camera window opens. Keep **one face** in front of the camera and look straight ahead. After two matching scans, the dialog closes and the bookstore signs in to the recognized account. **Cancel / use password** closes the camera and leaves you on the login screen.

The scanning dialog times out after 25 seconds. Close it and retry if needed. Password login always remains an option.

## 6. Testing

Run everything from the project root with your virtual environment active:

```bash
python -m unittest discover -s tests -v
```

The automated tests check template storage, face matching and the mocked GUI sign-in path, without downloading models or using a webcam. For a real webcam test, also run:

```bash
python scripts/test_yolo_camera.py
python scripts/login_face.py
python -m gui
```

Test cases to try manually:

1. Your enrolled face should sign in to your own bookstore account.
2. No face or multiple faces should not sign in.
3. Another consenting person's unenrolled face should not sign in.
4. Canceling should leave the account signed out, and close the camera.
5. Password login should still work.
6. Missing models or blocked camera permissions should show an error, not crash the app.
7. Try different expressions/lighting, and glasses/no glasses if relevant.

Note: automatic GUI tests simulate successful scans, **not** real camera accuracy; live tests must be run on a machine with a webcam.

### Camera permission help

- **Windows 10/11:** Settings > Privacy & security > Camera. Allow camera access and enable **Let desktop apps access your camera**. Close other camera apps using the webcam.
- **macOS:** System Settings > Privacy & Security > Camera. Enable camera access for the app running Python (Terminal, VS Code, or the relevant application). Close and reopen the app after granting permission.
- If the wrong camera opens, change `cv2.VideoCapture(0)` in `gui/face_dialog.py`, `scripts/enroll_face.py`, and the camera test scripts to `cv2.VideoCapture(1)` or the correct local camera index.
- If imports fail, verify that the VS Code terminal uses your `.venv` interpreter.

## Files involved

- `gui/pages/login.py`: wires the existing Face ID button to a real camera dialog.
- `gui/face_dialog.py`: Qt camera preview and background scanning worker.
- `gui/face_camera.py`: shared YOLO/YuNet/SFace model paths and feature extraction.
- `gui/face_login.py`: numeric matching and rejection of ambiguous matches.
- `gui/auth.py`: password login and facial authentication entry points.
- `gui/store.py`: stores, reads, and removes enrolled templates.
- `scripts/enroll_face.py`, `scripts/login_face.py`: manual enrollment and verification.
- `scripts/test_yolo_camera.py`, `scripts/test_face_match.py`: experimental tests.
- `tests/test_face_templates.py`, `tests/test_face_login.py`, `tests/test_face_gui.py`: automated tests.
- `tests/test_gui_smoke.py`: existing GUI regression tests (updated Face ID placeholder assertion).
- `requirements.txt`: required packages.

## Important limitations

This is **not Apple Face ID** and is **not suitable for real production authentication**. The match cutoff is a provisional `0.60` cosine-similarity score with a `0.10` gap between competing accounts. We require two matching frames, but do not do validated liveness/anti-spoofing checks. Photos or videos may fool the system; scores are not probabilities. Templates are stored locally without encryption, and accuracy has not been calibrated across different people, lighting, cameras, and appearances. Use only consenting test volunteers.


## Removing your enrolled face

Face templates are stored locally in `.data/store.json`.

To remove your saved face scans, open a terminal in the
project folder and run:

```python
from gui.store import Store

store = Store()
store.remove_face_templates("your-email@example.com")
```

Replace the example email with your registered email.
You can run this code in a Python terminal.

This removes the account's facial templates, but keeps
the account and password login.

Face templates are not encrypted. Do not upload or
share `.data/store.json`.

