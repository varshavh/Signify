# 👐 Signify

**Real-time sign-language recognition — a pure-Python desktop app.**

Signify reads American Sign Language gestures from your webcam, recognizes them
in real time, and lets you build, edit, speak, and save whole sentences. Built
with a modern dark UI in CustomTkinter — no browser, no cloud, no database.

---

## ✨ Features

- **Live webcam recognition** of 42 ASL signs (A–Z + 16 common words) using a
  pretrained MediaPipe gesture model.
- **Hand-skeleton overlay** drawn on the video feed.
- **Sentence builder** with temporal debouncing — flickery detections are
  smoothed into clean, committed words.
- **Full editing:** space, backspace, clear, plus a live "committed words" log.
- **🔊 Speak** the sentence aloud (offline text-to-speech).
- **📋 Copy** to clipboard and **💾 Save** sentences to `saved_sentences.txt`.
- **Adjustable sensitivity** (confidence slider) and **pause/resume** detection.
- **Login screen** with fixed admin credentials (no database).

---

## 🖥️ Tech stack

| Purpose | Tool |
|---------|------|
| UI | CustomTkinter |
| Webcam / imaging | OpenCV + Pillow |
| Recognition | MediaPipe Tasks (Gesture Recognizer) |
| Text-to-speech | pyttsx3 (offline) |

Everything is **Python** — the old React/Firebase web stack has been removed.

---

## 🚀 Getting started

Requires **Python 3.10–3.12** (MediaPipe has no 3.13/3.14 wheels yet).

```bash
# 1. Clone
git clone https://github.com/varshavh/Signify.git
cd Signify

# 2. Create a virtual environment
python3.12 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run
python run.py
```

### Login
```
username:  admin
password:  admin123
```
(Change these in `signify/config.py`.)

---

## 🎬 Using the app

1. Sign in with the demo credentials.
2. Allow camera access when prompted.
3. Make a sign and hold it steady — once it's stable, the word is added to your
   sentence on the right.
4. Use **Space / Backspace / Clear** to edit, **Speak** to hear it, **Copy** or
   **Save** to keep it.

---

## 🧠 Recognized signs

**Letters:** A–Z
**Words:** Hello, Bye, Deaf, ILoveYou, Learn, Me, Meet, Name, No, NotOk, Ok,
Pen, Please, Tell, Thankyou, Yes

> Accuracy varies per sign and depends on lighting and hand position. Some signs
> (e.g. Ok, Name) are recognized less reliably than others.

---

## 📁 Project structure

```
Signify/
├── run.py                     # entry point
├── signify/
│   ├── app.py                 # CustomTkinter UI (login + detection)
│   ├── recognizer.py          # MediaPipe gesture-model wrapper
│   ├── sentence_builder.py    # debouncing + sentence editing
│   └── config.py              # theme + fixed credentials
├── models/
│   └── sign_language_recognizer.task   # pretrained MediaPipe model
├── sign_language_dataset/     # sample images per class
├── Code For Training the Model/        # original training notebook
└── requirements.txt
```

---

## 📄 License

MIT
