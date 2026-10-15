# ANJS_proj
CCNY Fall 2026 Software Engineering Project

## Team Members
- Zeferino Franco Salgado
- Nadim Saddique
- Jigmi Sherpa
- Sarinda Shrestha
- Ambrose Wilkinson

## Introduction
The goal is to create an AI enabled project building out a multimodal bookstore that can facilitate a wide range of functions.

## Technologies
We will predominantly rely on Python (I think) unless anyone on the team prefers another language. The project has to be full stack so we've got to decide whether we want to go SQL or NoSQL for data storage and how we render the front-end (I'm all for react with Tailwind for design). The front-end isn't a big concern since we can just use AI to wireframe and build it out without much interference.

We, the team, need to architect, design, and build solutions with some testing throughout. We should meet at least bi-weekly to discuss various things that we plan to implement and weigh the pros and cons of each decision. Perhaps we will have to break up into smaller groups in order to accomplish the tasks.

## Team Requirements
-Everyone should be proficient with Git and github. If you're not ask the rest of the team and we an help get you up to speed. Each feature should be separated into a different branch before being merged into dev, reviewed by another team member, and merged into the main branch.

## Features
Let's brainstorm a list of possible features to add to the project
- AI Recommendations: You input what books you've read recently or what authors you like and the AI is able to recommend some books for you.
- Reading list: a list of books you want to read, but aren't ready to put down your card to buy. We need to implement an easy was to move those items into the cart so that they can be purchased.

## GUI (prototype)
A desktop prototype of the first wireframe set (dark navy and yellow) built with Python and [PySide6](https://doc.qt.io/qtforpython-6/). It works on a phone-sized window or a full desktop window.

```bash
pip install -r requirements.txt
python -m gui                  # dark theme (wireframe set 1)
python -m gui --theme mint     # start in the light mint theme (wireframe set 2)
python -m unittest discover -s tests -v   # headless smoke tests (no Ollama needed)
```

- **Landing page:** everyone lands on the same home page (search, categories, bestsellers). The greeting, cart button, order tracker and "Recommended for you" only appear once someone signs in, and the tracker only shows when that user has an order on the way.
- **Accounts:** there are no users until someone signs up (*Sign in > Create an account*). Accounts and orders are saved to `.data/store.json` (git-ignored; set `ANJS_DATA_DIR` to move it). Passwords are salted and hashed, but this is a local stand-in for the real backend (`gui/store.py`, `gui/auth.py`). Face ID doesn't recognize anyone yet because no account has a face enrolled.
- **Desktop layout:** the book grid shows 2 cards per row on a phone-sized window, 3 from 540 px and 4 from 760 px (`BREAKPOINTS` in `gui/pages/catalog.py`). Text-heavy pages are capped in width and centred.
- **Orders:** *Checkout* places the order straight away (no payment yet). The Orders tab has **Tracking** (orders on the way) and **History** (every book you've bought, with *Buy again*).
- **Ask (AI book chat):** chat with a local LLM through [Ollama](https://ollama.com). It knows the catalog and, when you're signed in, what you've already bought.
  ```bash
  ollama pull llama3.2:3b
  ollama serve        # or just open the Ollama app
  ```
  Use another model with `ANJS_LLM_MODEL=<name>`, or another server with `ANJS_LLM_HOST=http://host:11434`.
- **Theme switch:** `View > Mint theme` (Ctrl+T) in the menu bar, or the *Appearance* button on the Account tab once signed in. Colours live in `gui/theme.py`, so a third theme is one more `Palette`.
- **Placeholders to replace:** `gui/data.py` holds invented sample books. The camera box is a drawn placeholder, not a live camera feed. Order status never moves past "processing" because there is no shipping backend yet.
