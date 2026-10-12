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
A desktop prototype of the first wireframe set (dark navy and yellow) built with Python and [PySide6](https://doc.qt.io/qtforpython-6/). It has three screens: sign in (Face ID tab and password tab), the guest home page, and the signed-in home page. The Cart, Orders and Account tabs behind the signed-in nav bar are simple placeholders.

```bash
pip install -r requirements.txt
python -m gui                  # dark theme (wireframe set 1)
python -m gui --theme mint     # start in the light mint theme (wireframe set 2)
python -m unittest discover -s tests -v   # headless smoke tests
```

- **Theme switch:** `View > Mint theme` (Ctrl+T) in the menu bar, or the *Appearance* button on the Account tab once signed in. Colours live in `gui/theme.py`, so a third theme is one more `Palette`.
- **Placeholders to replace:** `gui/auth.py` accepts any well-formed email plus a non-empty password and always "recognises" a demo user (no real face or password check), and `gui/data.py` holds invented sample books and a sample order. The camera box is a drawn placeholder, not a live camera feed.
