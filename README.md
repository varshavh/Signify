# 👐 Signify

**Real-time sign-language recognition — a pure-Python desktop app.**

Signify reads American Sign Language gestures from your webcam, recognizes them
in real time, and lets you build, edit, speak, translate, and save sentences.
Built with a modern dark UI in CustomTkinter — camera stays on this machine.

---

## ✨ Features

- **Live webcam recognition** of ASL letters and words using a MediaPipe
  gesture model, with a hand-skeleton overlay.
- **Sentence builder** with temporal debouncing, fingerspelling, Space /
  Backspace / Clear, speak, copy, and save.
- **Profile** — name, email, location, bio stored on this device.
- **Dashboard** — screen time (today / week / month / year), usage charts,
  most-signed gestures, saved-sentence history, practice stats.
- **Practice Studio** — prompted-sign quiz with live camera scoring.
- **Translator** — type or paste, translate across languages, speak, copy.
- **About + Settings** — confidence, speak speed, auto-speak, autocorrect.
- **Local accounts** — sign up with your profile; sign in later to load it from
  a SQLite database on this computer.
- **Home translator** — translate the current sentence without leaving detection.

---

## 🖥️ Tech stack

| Purpose | Tool |
|---------|------|
| UI | CustomTkinter |
| Webcam / imaging | OpenCV + Pillow |
| Recognition | MediaPipe Tasks (Gesture Recognizer) |
| Text-to-speech | pyttsx3 (offline) |
| Accounts / stats | SQLite (`data/signify.db`) |

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

Same app on **Windows**: install Python **3.10–3.12** (not 3.13/3.14), allow the camera under Windows privacy settings, then `python -m venv .venv`, `.venv\Scripts\activate`, `pip install -r requirements.txt`, `python run.py`. Speak uses Windows SAPI; translation still needs internet. Accounts live in `data\signify.db` on that PC.

### First launch

If no account exists, Signify opens **Create account**. Fill username, password,
name, email, location, and bio. Next time, **Sign In** loads that profile,
screen time, saved sentences, and practice stats from `data/signify.db`.

---

## 🎬 Using the app

1. Create an account (or sign in if you already have one).
2. **Home** — camera, sentence builder, and translate the sentence in place.
3. **Dashboard** — screen time and your most-used signs.
4. **Profile** — edit your name and details (saved locally).
5. **Practice** — the app prompts a sign; hold it until it scores.
6. **Translate** — type a sentence, pick a language, speak or copy.
7. **Settings** — confidence, voice speed, auto-speak, autocorrect.

---

## 🧠 Recognized signs

**Letters:** A–Z
**Words:** Hello, Bye, Deaf, ILoveYou, Learn, Me, Meet, Name, No, NotOk, Ok,
Pen, Please, Tell, Thankyou, Yes
**Added words** (trained from a cropped YOLO dataset): Father, Fine, Friend,
Help, MyNameIs, Who, You

> Accuracy varies per sign and depends on lighting and hand position. The
> original 42 signs are the most reliable. Among the added words, **Fine** and
> **You** work best; others (built from fewer landmark-detectable images) are
> less reliable.

The model used by the app is `models/sign_language_recognizer.task` (42 classes).
An experimental 49-class file `models/signify_extended.task` may also be present.

---

## 📁 Project structure

```
Signify/
├── run.py                     # entry point
├── signify/
│   ├── app.py                 # sign in / sign up, nav, live detection
│   ├── pages.py               # dashboard, profile, practice, translator
│   ├── store.py               # local SQLite accounts + per-user data
│   ├── db.py                  # schema
│   ├── translate.py           # sentence translation helper
│   ├── recognizer.py          # MediaPipe gesture-model wrapper
│   ├── sentence_builder.py    # debouncing + sentence editing
│   └── config.py              # theme + practice signs
├── models/
│   ├── signify_extended.task           # 49-class model used by the app
│   └── sign_language_recognizer.task   # original 42-class model (kept)
├── sign_language_dataset/     # sample images per class
├── build_combined_dataset.py  # crops 7 YOLO word-signs + merges dataset
├── train_gesture_model.py     # trains the extended .task (MediaPipe Model Maker)
├── Code For Training the Model/        # original training notebook
└── requirements.txt
```

---

## 📄 License

MIT
