# ANJS Bookstore

CCNY Fall 2026 (CSC 322, Software Engineering) team project: an AI-enabled desktop bookstore built with Python and [PySide6](https://doc.qt.io/qtforpython-6/). Browse a 100-book catalogue, buy books, review them, chat with a local AI bookseller, and sign in with a password or your face.

## Contents

- [What it does](#what-it-does)
- [Technologies](#technologies)
- [How to use this app](#how-to-use-this-app)
- [Roles](#roles)
- [Review and moderation rules](#review-and-moderation-rules)
- [How user data is stored](#how-user-data-is-stored)
- [Book catalogue](#book-catalogue)
- [Running tests](#running-tests)
- [Team Requirements](#team-requirements)

## What it does

- Home page with search, categories and bestsellers; guests can browse and search.
- Accounts (sign up, password sign-in, optional Face ID sign-in) with three roles: RC, VC and SU.
- Cart and checkout (no payment step yet), order tracking and order history with *Buy again*.
- Book reviews and star ratings with taboo-word moderation, warnings, suspensions and verified-buyer weighting.
- Super-user tools: To-Order / No-Order lists, taboo-word list, suspended accounts.
- **Ask:** chat with a local LLM (through Ollama) that knows the catalogue and, for signed-in users, their purchases and billing totals. For a super-user it also gets a bookstore financial summary (orders, sales, discounts, books sold).
- Two colour themes (dark navy/yellow and light mint), phone-sized or full desktop window.
- Search over titles, authors, subjects and descriptions that ranks title hits first and corrects misspellings.

Not built yet: payment, real shipping (order status stays at "processing"), a real backend database. The Terms, Privacy and Help links on the sign-up page are text only.

## Technologies

- **Python** and **PySide6** (Qt) for the desktop GUI.
- A **local JSON file** (`.data/store.json`) for accounts, orders and reviews. It stands in for a real backend; see [How user data is stored](#how-user-data-is-stored).
- **Ollama** running a local LLM (default `llama3.2:3b`) for the Ask tab. No cloud API.
- **OpenCV and YOLO** (via `ultralytics`) for Face ID login: YOLO detects the face, OpenCV's YuNet and SFace models produce a 128-number face template.
- **SQLite FTS5** (in memory) for catalogue search.
- Catalogue data from Project Gutenberg and Open Library.

## How to use this app

### 1. Prerequisites

- **Python 3.10 or newer** (the code uses modern type syntax such as `X | None`; development used 3.13). Check with `python3 --version`.
- **Git**.
- Optional: [Ollama](https://ollama.com) for the Ask tab, and a webcam plus three model files for Face ID.

### 2. Clone and install

```bash
git clone https://github.com/a-breezy/ANJS_proj.git
cd ANJS_proj

python3 -m venv .venv
source .venv/bin/activate          # Windows PowerShell: .\.venv\Scripts\Activate.ps1

pip install -r requirements.txt
```

`requirements.txt` has three packages:

| Package | Needed for |
| --- | --- |
| `PySide6-Essentials` | The whole app (required) |
| `opencv-python` | Face ID only |
| `ultralytics` | Face ID only (YOLO face detector; it pulls in PyTorch, so it is a large download) |

They are installed together, and the GUI imports `cv2` and `ultralytics` only when you use Face ID, so password sign-in does not need a working camera setup. If you never use Face ID, you could install just `PySide6-Essentials` to save space.

### 3. Optional settings (`.env`)

Defaults work without any setup. To change them, copy the example file and edit it (`.env` is git-ignored). A value already set in your shell wins over `.env`.

```bash
cp .env.example .env
```

| Variable | Default | Meaning |
| --- | --- | --- |
| `ANJS_DATA_DIR` | `.data` | Folder that holds `store.json` (accounts, orders, reviews). Point it somewhere else for a throwaway test store. |
| `ANJS_CATALOG` | (unset) | Set to `sample` to use 8 invented test books instead of the 100-book catalogue. Also used automatically if `catalog/catalog.json` is missing. Not listed in `.env.example`; set it in your shell. |
| `ANJS_LLM_HOST` | `http://localhost:11434` | Where the Ollama server is. |
| `ANJS_LLM_MODEL` | `llama3.2:3b` | Which Ollama model the Ask tab uses. |
| `ANJS_MODELS_DIR` | `.data/models` | Folder with the three Face ID model files (relative paths start at the project root). |
| `ANJS_YOLO_MODEL` | `yolov8n-face.pt` | YOLO face detector file name. |
| `ANJS_YUNET_MODEL` | `face_detection_yunet_2023mar.onnx` | YuNet landmark model file name. |
| `ANJS_SFACE_MODEL` | `face_recognition_sface_2021dec.onnx` | SFace recognition model file name. |
| `ANJS_CAMERA_INDEX` | `0` | Which webcam to open. Try 1, 2, ... if the wrong one opens. |
| `ANJS_FACE_MIN_SCORE` | `0.60` | Minimum cosine similarity for a face match. |
| `ANJS_FACE_MIN_GAP` | `0.10` | Best match must beat the runner-up by this much, otherwise the scan is rejected. |
| `ANJS_FACE_SCAN_SECONDS` | `25` | How long the scan dialog waits for a face. |

### 4. Start the app

```bash
python -m gui                  # dark theme (navy and yellow)
python -m gui --theme mint     # start in the light mint theme
```

### 5. Tour

1. **Browse and search as a guest.** The home page shows search, categories and bestsellers. Click a book to see its description, price and rating. Guests see *Sign in to buy* instead of *Add to cart*, and the cart, Orders and Account tabs ask you to sign in.
2. **Sign up.** Choose *Sign in > Create an account*, enter a name, an email and a password of at least 8 characters. Every new account is a Registered Customer (RC), and you are signed in straight away.
3. **Sign in.** Use the **Password** tab with your email and password, or the **Face** tab for Face ID. Face ID needs model files, a webcam and a one-time enrollment: follow [FACE_ID_SETUP.md](FACE_ID_SETUP.md) (it enrolls with `python scripts/enroll_face.py`). A suspended account cannot sign in.
4. **Add to cart and check out.** Use *Add to cart* on a book card or book page, open the **Cart** tab and press *Checkout*. The order is recorded immediately (there is no payment step). VC accounts get 10% off.
5. **Orders.** The **Orders** tab has *Tracking* (orders on the way) and *History* (every book you bought, with *Buy again*). The home page shows an order tracker when you have one in progress.
6. **Reviews and ratings.** On a book card, press *Reviews & Ratings* to read reviews and post your own (1 to 5 stars plus a comment). The [rules below](#review-and-moderation-rules) apply.
7. **Ask (AI).** Open the **Ask** tab (signed-in users) and chat with the bookseller. It needs Ollama running:
   ```bash
   ollama pull llama3.2:3b     # or the model you set in ANJS_LLM_MODEL
   ollama serve                # or just open the Ollama app
   ```
   If Ollama is not running, or the model is not installed, the chat shows the exact command to run.
8. **Account page and theme.** The **Account** tab shows who you are, an *Appearance* switch, and *Sign out*. You can also switch theme any time with `View > Mint theme` (Ctrl+T). Colours live in `gui/theme.py`.
9. **Sign out.** *Account > Sign out* returns you to the guest home page. Your cart and Ask history are cleared.

## Roles

| Role | Who | What they can do |
| --- | --- | --- |
| Visitor (guest) | Not signed in | Browse and search. |
| **RC** (Registered Customer) | Everyone who signs up | Buy, order history, review books, Ask tab. |
| **VC** (VIP Customer) | An RC who has made **more than 3 purchases** or spent **more than $200** | Everything an RC can, plus **10% off** every order. Promotion happens automatically at checkout. |
| **SU** (Super-User) | Created from the command line | Everything above, plus the moderation tools below and the financial summary in the Ask tab. |

### Making a super-user

Public sign-up only ever creates RC accounts. To create an SU, run this from the project root:

```bash
python scripts/create_su.py
```

It prompts for a name, an email and a password, refuses an email that already exists, and creates the account with role SU. Sign in with it as usual. (This script is being added on a separate branch; if it is not in your checkout yet, pull the latest `dev`.)

### What the SU sees

On the **Account** tab, an SU gets an extra button, **SU: Order Lists & Taboo Words**, which opens a dialog with three tabs:

- **Order Lists:** the **To-Order** list (books with more than 3 reviews and a weighted average above 4.0) and the **No-Order** list (more than 3 reviews and a weighted average below 2.0).
- **Taboo Words:** add or remove words from the moderation list.
- **Suspended Users:** reactivate a suspended account (this also resets its warnings to 0).

In the **Ask** tab, an SU is given a bookstore financial summary (total orders, total sales, total discounts and books sold, computed from every stored order) and the assistant is told to use only those figures for business analysis. Remember it is a small local model, so double-check any numbers it quotes against the Orders data.

## Review and moderation rules

These are the project spec rules the review code implements:

- **Taboo words:** a comment with 1 to 3 taboo words is accepted and each taboo word is replaced by `*` characters. A comment with **more than 3** taboo words is blocked and the author gets a warning. Repeats of the same word each count.
- **Warnings and suspension:** an **RC** who gets more than 2 warnings (the 3rd) is **suspended** and must be reactivated by an SU. A **VC** who would go past 2 warnings is instead **demoted to RC** and their warnings reset to 0. SU authors are never warned. A demoted VC has to earn VIP status again: only purchases and spending *after* the demotion count toward the next promotion (more than 3 purchases or more than $200).
- **One review per user per book:** each signed-in user has one review per book. Posting again replaces the old one.
- **Verified buyers:** if you have ordered the book, your review is marked as a verified buyer and its stars count **double** in the weighted average. Verified reviews are listed first.
- **To-Order / No-Order:** a book with more than 3 reviews and a weighted average **below 2** goes on the SU **No-Order** list; **above 4** goes on the **To-Order** list. Exactly 2.0 or 4.0 is on neither list.
- The default taboo words are `spam`, `scam`, `trash` and `idiot`; an SU can edit the list.

## How user data is stored

This is a **local prototype store, not production security.**

- **One JSON file:** `.data/store.json` in the project root, or `$ANJS_DATA_DIR/store.json` if you set `ANJS_DATA_DIR`. The `.data/` folder is git-ignored, so accounts never get committed. It does not exist until the app first saves something.
- **What it holds:**
  - `users`: per account (keyed by lower-case email) the name, email, role (`RC`, `VC` or `SU`), a **salted PBKDF2-SHA256 password hash plus its salt** (never the plain password), `shipping_address` (currently always empty), `purchase_count`, `total_spent`, `warnings`, `suspended`, and optionally `face_templates`.
  - `orders`: a list of orders per user email (order number, date, status, book ids, total, and the discount applied). Only signed-in customers can check out.
  - `reviews`: a list of reviews per book id (author name and email, stars, the masked comment, verified-buyer flag, weight, date).
  - `taboo_words`: the moderation word list.
  - `next_order`: the next order number (starts at 1001).
- **Face templates** are up to 4 scans per account, each a vector of 128 numbers saved as plain JSON. They are biometric data stored **unencrypted**, so treat `store.json` as private, never commit it, and delete your template if you do not want it kept (see FACE_ID_SETUP.md). Matching compares a new scan with each template by cosine similarity (`gui/face_login.py`).
- **Writes** go to a temporary file (`store.tmp`) that is then renamed over `store.json`, so a crash mid-save cannot leave a half-written file.
- **The catalogue is separate:** `catalog/catalog.json` and `catalog/covers/` are committed to the repo and read-only at runtime. See [Book catalogue](#book-catalogue).
- **Reset:** close the app and delete `.data/store.json`. All accounts, orders, reviews and face scans are gone (the model files in `.data/models` are separate).
- **Throwaway store:** run with another folder, for example `ANJS_DATA_DIR=/tmp/anjs-test python -m gui` (PowerShell: `$env:ANJS_DATA_DIR="C:\temp\anjs-test"; python -m gui`).

## Book catalogue

The store sells 100 public-domain books from [Project Gutenberg](https://www.gutenberg.org), picked by hand across 12 shelves, with descriptions and star ratings from [Open Library](https://openlibrary.org).

- `catalog/selection.toml`: the list of books (Gutenberg number, shelf, display title, author). Edit this to change the catalogue.
- `catalog/catalog.json` and `catalog/covers/`: built by the import script and committed, so you do not need to run it.
- `python scripts/build_catalog.py`: fetches any books new to the list (`--refresh` fetches everything again).
- Search (`gui/search.py`) covers titles, authors, subjects and descriptions, ranks title matches highest, and corrects misspellings.
- Without `catalog.json` (or with `ANJS_CATALOG=sample`) the app uses 8 invented sample books, which is what the tests use.
- On a phone-sized window the book grid shows 2 cards per row, 3 from 540 px and 4 from 760 px (`BREAKPOINTS` in `gui/pages/catalog.py`).
- Design diagrams (collaboration and sequence) are in `assets/`.

## Running tests

No Ollama, camera or model files are needed.

```bash
QT_QPA_PLATFORM=offscreen ANJS_CATALOG=sample python -m unittest discover -s tests -v
```

On Windows PowerShell:

```powershell
$env:QT_QPA_PLATFORM="offscreen"; $env:ANJS_CATALOG="sample"; python -m unittest discover -s tests -v
```

## Team Requirements

- Everyone should be proficient with Git and GitHub. If you are not, ask the rest of the team and we can help get you up to speed.
- Each feature goes on its own branch, is merged into `dev`, reviewed by another team member, and then merged into `main`.
- We meet at least bi-weekly to discuss what we plan to implement and weigh the pros and cons of each decision.
