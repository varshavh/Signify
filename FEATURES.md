# Signify — new features and where to look

This is the feature map for **Signify 2.0** (`b5c2700` on `main`). Older pieces (webcam recognition, sentence debounce, Space, offline autocorrect) are listed at the end so you know they are still there.

Repo: https://github.com/varshavh/Signify

---

## Pull and run

Requires **Python 3.10–3.12** (MediaPipe has no 3.13/3.14 wheels). Camera permission on macOS/Windows. Translation needs internet; accounts and speech are local.

```bash
git clone https://github.com/varshavh/Signify.git
cd Signify
git pull origin main

python3.12 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python run.py
```

If you already cloned this folder (`SignLanguageDetection`):

```bash
git pull signify main              # remote `signify` → varshavh/Signify
# or: git pull origin main         # only if origin is varshavh/Signify
```

First launch: **Create account** (username, password, name, email, location, bio). Next time use **Sign In**. Data is stored in `data/signify.db` (gitignored).

---

## In the UI

| Nav | What it is |
|-----|------------|
| **Home** | Live camera, sentence builder, dual subtitles, in-place translate |
| **Dashboard** | Screen time, charts, top signs, saved sentences |
| **Profile** | Name / email / location / bio |
| **Practice** | Hold the prompted sign until it scores |
| **Translate** | Type/paste → other language → speak/copy |
| **About** | App description |
| **Settings** | Confidence, speak speed, auto-speak, autocorrect, dual subs, Home language |

---

## New features (where to look)

### Local accounts (sign up / sign in)

No more hardcoded `admin`. PBKDF2 passwords, last username remembered. Empty DB opens **Create account**.

| Look here | Why |
|-----------|-----|
| `signify/app.py` → `AuthScreen`, `SignifyApp.show_login` | Login / signup UI |
| `signify/store.py` → `LocalAuth` | Username rules, hash/verify, signup/login |
| `signify/db.py` → `users` table | Schema |

### Per-user SQLite store

Profile, settings, usage seconds, detection log, saved sentences, practice scores — all keyed by username.

| Look here | Why |
|-----------|-----|
| `signify/db.py` | Tables + `dual_subs` / `translate_lang` migrations |
| `signify/store.py` → `AppStore` | Read/write API used by every page |
| `data/signify.db` | Runtime file (not in git) |

### Multi-page shell

Top nav, logout, 15s usage tick while logged in.

| Look here | Why |
|-----------|-----|
| `signify/app.py` → `NAV`, `MainShell` | Routing and camera teardown when you leave Home |
| `signify/pages.py` | Every screen except Home and auth |

### Dashboard (screen time + history)

Today / week / month / year, bar charts, most-signed gestures, sentence history, practice totals.

| Look here | Why |
|-----------|-----|
| `signify/pages.py` → `DashboardPage` | Layout |
| `signify/charts.py` | Duration labels + bar drawing |
| `signify/store.py` | `today_seconds`, `last_n_days`, detections, sentences |

### Profile editor

Edit name, email, location, bio; initials avatar.

| Look here | Why |
|-----------|-----|
| `signify/pages.py` → `ProfilePage` | Form |
| `signify/store.py` → `update_profile` | Persist |

### Practice Studio

Random prompt from a reliable sign list; live camera; streak / accuracy saved per user.

| Look here | Why |
|-----------|-----|
| `signify/pages.py` → `PracticePage` | Quiz + camera |
| `signify/config.py` → `PRACTICE_SIGNS` | Which signs can be prompted |
| `signify/db.py` → `practice` table | Scores |

### Translator page

Source/target language, quick phrases, speak + copy.

| Look here | Why |
|-----------|-----|
| `signify/pages.py` → `TranslatorPage` | UI |
| `signify/translate.py` | Google clients5 → gtx → MyMemory, in-memory cache |
| `signify/translate.py` → `LANGS` | Language list |

### Home translator + live dual subtitles

Translate the current sentence without leaving detection. EN + target language under the camera (~900ms debounce). Toggle **Live dual subtitles under camera**. Language picker does **not** freeze the app.

| Look here | Why |
|-----------|-----|
| `signify/app.py` → `DetectScreen` | Subtitle bar, translate box, `_pump_ui` applies worker results |
| `signify/widgets.py` → `LanguagePicker` | Expand-in-place list (avoids CTk `grab_set` freeze) |
| `signify/pages.py` → `SettingsPage` | Same dual-subs + Home language switches |

### Sentence “. Stop”

Finishes the current spelled word and appends a period.

| Look here | Why |
|-----------|-----|
| `signify/app.py` → `DetectScreen._period` | Button |
| `signify/sentence_builder.py` → `add_period` | Logic |

### Camera off the UI thread (Windows-friendly)

Capture + MediaPipe on a worker; UI thread only paints. Windows uses DirectShow. Cover-crop fill for the video panel. DPI awareness on Windows.

| Look here | Why |
|-----------|-----|
| `signify/camera.py` → `open_webcam` | `CAP_DSHOW` on Windows |
| `signify/app.py` → `_cam_loop`, `_pump_ui` | Thread + UI pump |
| `signify/app.py` → `main()` | Windows DPI |
| `signify/tts.py` | `sapi5` on Windows, `pyttsx3` elsewhere |

### Settings that stick per user

Confidence, TTS rate, auto-speak, autocorrect, dual subtitles, default translate language.

| Look here | Why |
|-----------|-----|
| `signify/pages.py` → `SettingsPage` | Form |
| `signify/store.py` → `update_settings` | Persist |
| `signify/app.py` → `DetectScreen` | Home reads those settings |

### About

Short product copy + jumps to Home / Translate.

| Look here | Why |
|-----------|-----|
| `signify/pages.py` → `AboutPage` | Copy and buttons |

---

## Already in the app (not new this round)

| Feature | Where |
|---------|--------|
| MediaPipe live recognition + skeleton | `signify/recognizer.py`, Home `_cam_loop` |
| Letter vs word sentence builder, Space, debounce | `signify/sentence_builder.py` |
| Offline autocorrect for fingerspelling | `signify/autocorrect.py` |
| Speak / copy / save sentence | `DetectScreen` + `signify/tts.py` + `saved_sentences.txt` |
| 42-class model | `models/sign_language_recognizer.task` |
| Training helpers | `train_gesture_model.py`, `build_combined_dataset.py`, `Code For Training the Model/` |

---

## File map

```
run.py                      # python run.py
signify/app.py              # auth, Home, nav shell
signify/pages.py            # Dashboard, Profile, Practice, Translate, About, Settings
signify/store.py            # accounts + per-user data
signify/db.py               # SQLite schema
signify/camera.py           # webcam open
signify/translate.py        # translation backends
signify/tts.py              # speak
signify/widgets.py          # LanguagePicker
signify/sentence_builder.py # sentence state
signify/autocorrect.py      # spelled-word fixup
signify/recognizer.py       # MediaPipe wrapper
signify/charts.py           # dashboard bars
signify/config.py           # theme + practice signs
requirements.txt
```
