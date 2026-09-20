"""Secondary screens: dashboard, profile, practice, translator, about, settings."""

from __future__ import annotations

import random
from tkinter import filedialog

import cv2
import customtkinter as ctk
from PIL import Image

from .charts import draw_bars, format_duration
from .config import APP_NAME, APP_TAGLINE, COLORS, NUM_HANDS, PRACTICE_SIGNS, SIDEBAR_WIDTH
from .camera import open_webcam
from .custom_signs import best_match
from .recognizer import SignRecognizer
from .sentence_builder import SentenceBuilder, display_name, is_letter
from .translate import LANG_NAMES, translate_text
from .tts import speak, pop_status
from .widgets import LanguagePicker

PHRASES = [
    "Hello, my name is",
    "Thank you so much",
    "Please help me",
    "Nice to meet you",
    "I love you",
    "How are you",
]


def _card(parent, **kwargs):
    opts = dict(fg_color=COLORS["surface"], corner_radius=16)
    opts.update(kwargs)
    return ctk.CTkFrame(parent, **opts)


class DashboardPage(ctk.CTkScrollableFrame):
    def __init__(self, master, store):
        super().__init__(master, fg_color=COLORS["bg"])
        self.store = store

        head = ctk.CTkFrame(self, fg_color="transparent")
        head.pack(fill="x", padx=8, pady=(8, 4))
        ctk.CTkLabel(head, text="Screen Time", font=("Arial", 28, "bold"),
                     text_color=COLORS["text"]).pack(anchor="w")
        ctk.CTkLabel(head, text="Your Signify usage over time — tracked only on this device.",
                     font=("Arial", 13), text_color=COLORS["muted"]).pack(anchor="w")

        stats = ctk.CTkFrame(self, fg_color="transparent")
        stats.pack(fill="x", padx=8, pady=12)
        items = [
            ("TODAY", store.today_seconds(), COLORS["info"]),
            ("THIS WEEK", store.week_seconds(), COLORS["info"]),
            ("THIS MONTH", store.month_seconds(), COLORS["info"]),
            ("THIS YEAR", store.year_seconds(), COLORS["accent"]),
        ]
        for i, (label, secs, color) in enumerate(items):
            stats.grid_columnconfigure(i, weight=1)
            card = _card(stats)
            card.grid(row=0, column=i, padx=6, sticky="nsew")
            ctk.CTkLabel(card, text=label, font=("Arial", 11),
                         text_color=COLORS["muted"]).pack(pady=(14, 0))
            ctk.CTkLabel(card, text=format_duration(secs), font=("Arial", 26, "bold"),
                         text_color=color).pack(pady=(2, 14))

        charts = ctk.CTkFrame(self, fg_color="transparent")
        charts.pack(fill="x", padx=8, pady=4)
        series = [
            ("Daily usage", store.last_n_days(7), COLORS["info"]),
            ("Weekly usage", store.last_n_weeks(8), COLORS["info"]),
            ("Monthly usage", store.last_n_months(6), COLORS["info"]),
            ("Yearly usage", store.last_n_years(4), COLORS["accent"]),
        ]
        self._canvases = []
        for i, (title, data, color) in enumerate(series):
            r, c = divmod(i, 2)
            charts.grid_columnconfigure(c, weight=1)
            box = _card(charts)
            box.grid(row=r, column=c, padx=6, pady=6, sticky="nsew")
            ctk.CTkLabel(box, text=title, font=("Arial", 14, "bold"),
                         text_color=COLORS["text"]).pack(anchor="w", padx=14, pady=(12, 0))
            cv = ctk.CTkCanvas(box, height=150, bg=COLORS["surface"],
                               highlightthickness=0, bd=0)
            cv.pack(fill="x", padx=10, pady=(4, 12))
            self._canvases.append((cv, data, color))

        lower = ctk.CTkFrame(self, fg_color="transparent")
        lower.pack(fill="both", expand=True, padx=8, pady=8)
        lower.grid_columnconfigure((0, 1), weight=1)

        signs = _card(lower)
        signs.grid(row=0, column=0, padx=6, sticky="nsew")
        ctk.CTkLabel(signs, text="Most signed", font=("Arial", 15, "bold"),
                     text_color=COLORS["text"]).pack(anchor="w", padx=16, pady=(14, 8))
        top = store.top_signs(8)
        if not top:
            ctk.CTkLabel(signs, text="Start detecting to fill this chart.",
                         text_color=COLORS["muted"]).pack(padx=16, pady=(0, 16), anchor="w")
        else:
            peak = top[0][1]
            for label, count in top:
                row = ctk.CTkFrame(signs, fg_color="transparent")
                row.pack(fill="x", padx=16, pady=3)
                ctk.CTkLabel(row, text=display_name(label), width=110, anchor="w",
                             text_color=COLORS["text"]).pack(side="left")
                bar = ctk.CTkProgressBar(row, height=10, progress_color=COLORS["primary"])
                bar.pack(side="left", fill="x", expand=True, padx=8)
                bar.set(count / peak)
                ctk.CTkLabel(row, text=str(count), text_color=COLORS["muted"],
                             width=36).pack(side="right")
            ctk.CTkLabel(signs, text="").pack(pady=6)

        hist = _card(lower)
        hist.grid(row=0, column=1, padx=6, sticky="nsew")
        ctk.CTkLabel(hist, text="Saved sentences", font=("Arial", 15, "bold"),
                     text_color=COLORS["text"]).pack(anchor="w", padx=16, pady=(14, 8))
        recent = store.recent_sentences(8)
        if not recent:
            ctk.CTkLabel(hist, text="Save a sentence from Home to see it here.",
                         text_color=COLORS["muted"]).pack(padx=16, pady=(0, 16), anchor="w")
        else:
            for item in recent:
                ts = item.get("ts", "")[:16].replace("T", "  ")
                line = ctk.CTkFrame(hist, fg_color=COLORS["surface_2"], corner_radius=8)
                line.pack(fill="x", padx=14, pady=3)
                ctk.CTkLabel(line, text=ts, font=("Arial", 11),
                             text_color=COLORS["muted"]).pack(anchor="w", padx=10, pady=(6, 0))
                ctk.CTkLabel(line, text=item.get("text", ""), wraplength=360,
                             justify="left", text_color=COLORS["text"]).pack(
                                 anchor="w", padx=10, pady=(0, 8))

        prac = store.practice
        attempts = int(prac.get("attempts", 0))
        correct = int(prac.get("correct", 0))
        acc = f"{(100 * correct / attempts):.0f}%" if attempts else "—"
        badge = _card(self)
        badge.pack(fill="x", padx=14, pady=(4, 18))
        ctk.CTkLabel(
            badge,
            text=f"Practice studio   ·   {correct}/{attempts} correct   ·   "
                 f"accuracy {acc}   ·   best streak {prac.get('best_streak', 0)}",
            text_color=COLORS["text"], font=("Arial", 14),
        ).pack(pady=16)

        self.after(80, self._paint_charts)

    def _paint_charts(self):
        for cv, data, color in self._canvases:
            draw_bars(cv, data, color=color)


class ProfilePage(ctk.CTkFrame):
    def __init__(self, master, store):
        super().__init__(master, fg_color=COLORS["bg"])
        self.store = store
        p = store.profile

        wrap = ctk.CTkFrame(self, fg_color="transparent")
        wrap.place(relx=0.5, rely=0.46, anchor="center")

        card = _card(wrap, width=460)
        card.pack()
        card.pack_propagate(False)
        card.configure(height=460)

        initials = "".join(part[0] for part in p.get("name", "U").split()[:2]).upper() or "U"
        avatar = ctk.CTkFrame(card, width=88, height=88, corner_radius=44,
                              fg_color=COLORS["primary"])
        avatar.pack(pady=(22, 8))
        avatar.pack_propagate(False)
        ctk.CTkLabel(avatar, text=initials, font=("Arial", 28, "bold"),
                     text_color="#fff").place(relx=0.5, rely=0.5, anchor="center")

        ctk.CTkLabel(card, text=f"@{p.get('username', '')}", font=("Arial", 13),
                     text_color=COLORS["muted"]).pack()

        self.name = ctk.CTkEntry(card, width=320, height=40, placeholder_text="Name")
        self.name.insert(0, p.get("name", ""))
        self.name.pack(pady=6)
        self.email = ctk.CTkEntry(card, width=320, height=40, placeholder_text="Email")
        self.email.insert(0, p.get("email", ""))
        self.email.pack(pady=6)
        self.location = ctk.CTkEntry(card, width=320, height=40, placeholder_text="Location")
        self.location.insert(0, p.get("location", ""))
        self.location.pack(pady=6)
        self.bio = ctk.CTkEntry(card, width=320, height=40, placeholder_text="Short bio")
        self.bio.insert(0, p.get("bio", ""))
        self.bio.pack(pady=6)

        pill = ctk.CTkLabel(card, text="●  Online", text_color=COLORS["ok"],
                            font=("Arial", 13))
        pill.pack(pady=(8, 4))

        self.msg = ctk.CTkLabel(card, text="", text_color=COLORS["accent"])
        self.msg.pack()
        ctk.CTkButton(card, text="Save profile", width=320, height=42,
                      fg_color=COLORS["info"], hover_color=COLORS["primary"],
                      command=self._save).pack(pady=(4, 18))

        extras = _card(wrap, width=460)
        extras.pack(pady=14)
        ctk.CTkLabel(extras, text="Shortcuts", font=("Arial", 14, "bold"),
                     text_color=COLORS["text"]).pack(anchor="w", padx=18, pady=(14, 6))
        ctk.CTkLabel(extras,
                     text="Home — live detection\nDashboard — screen time & top signs\n"
                          "Practice — quiz yourself on signs\nTranslate — text, speech, languages",
                     justify="left", text_color=COLORS["muted"]).pack(anchor="w", padx=18, pady=(0, 16))

    def _save(self):
        self.store.update_profile(
            name=self.name.get().strip() or "User",
            email=self.email.get().strip(),
            location=self.location.get().strip(),
            bio=self.bio.get().strip(),
        )
        self.msg.configure(text="Saved on this device")


class PracticePage(ctk.CTkFrame):
    """Hold the prompted sign until it commits — a local quiz, no internet."""

    def __init__(self, master, store, on_done=None):
        super().__init__(master, fg_color=COLORS["bg"])
        self.store = store
        self.on_done = on_done
        self.recognizer = SignRecognizer(num_hands=NUM_HANDS)
        self.builder = SentenceBuilder(stability=8, min_confidence=store.settings.get("min_confidence", 0.45))
        self.cap = None
        self.running = False
        self.target = random.choice(PRACTICE_SIGNS)
        self.locked = False

        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=0, minsize=SIDEBAR_WIDTH)
        self.grid_rowconfigure(0, weight=1)

        left = _card(self)
        left.grid(row=0, column=0, sticky="nsew", padx=(16, 8), pady=16)
        left.grid_rowconfigure(0, weight=1)
        left.grid_columnconfigure(0, weight=1)

        self.video_host = ctk.CTkFrame(left, fg_color="#0a0c12", corner_radius=12)
        self.video_host.grid(row=0, column=0, sticky="nsew", padx=12, pady=12)
        self.video_host.grid_propagate(False)
        self.video = ctk.CTkLabel(self.video_host, text="Starting camera…", text_color=COLORS["muted"])
        self.video.place(relx=0, rely=0, relwidth=1, relheight=1)
        self.live = ctk.CTkLabel(left, text="Detecting…", font=("Arial", 18, "bold"),
                                 text_color=COLORS["accent"])
        self.live.grid(row=1, column=0, pady=(0, 14))

        right = _card(self, width=SIDEBAR_WIDTH)
        right.grid(row=0, column=1, sticky="nsew", padx=(8, 16), pady=16)
        right.grid_propagate(False)
        right.configure(width=SIDEBAR_WIDTH)

        ctk.CTkLabel(right, text="Practice Studio", font=("Arial", 22, "bold"),
                     text_color=COLORS["text"]).pack(anchor="w", padx=20, pady=(22, 4))
        ctk.CTkLabel(right, text="Hold the sign below until it locks in.",
                     text_color=COLORS["muted"]).pack(anchor="w", padx=20)

        self.target_lbl = ctk.CTkLabel(right, text=display_name(self.target),
                                       font=("Arial", 36, "bold"),
                                       text_color=COLORS["info"])
        self.target_lbl.pack(pady=28)

        self.kind = ctk.CTkLabel(right, text="", text_color=COLORS["muted"])
        self.kind.pack()
        self._refresh_kind()

        self.feedback = ctk.CTkLabel(right, text="Waiting for your sign…",
                                     font=("Arial", 15), text_color=COLORS["muted"])
        self.feedback.pack(pady=12)

        p = store.practice
        self.score = ctk.CTkLabel(
            right,
            text=self._score_text(),
            text_color=COLORS["text"], font=("Arial", 14),
        )
        self.score.pack(pady=(8, 4))

        ctk.CTkButton(right, text="Skip this sign", height=40, corner_radius=10,
                      fg_color=COLORS["surface_2"], command=self._skip).pack(
                          fill="x", padx=20, pady=(18, 8))
        ctk.CTkButton(right, text="Speak the prompt", height=40, corner_radius=10,
                      fg_color=COLORS["primary"], command=self._speak_prompt).pack(
                          fill="x", padx=20, pady=(0, 20))

        self.start_camera()

    def _score_text(self):
        p = self.store.practice
        return (f"{p.get('correct', 0)} correct   ·   "
                f"streak {p.get('streak', 0)}   ·   best {p.get('best_streak', 0)}")

    def _refresh_kind(self):
        kind = "fingerspell this letter" if is_letter(self.target) else "whole-word sign"
        self.kind.configure(text=kind)

    def _next_target(self):
        choices = [s for s in PRACTICE_SIGNS if s != self.target] or PRACTICE_SIGNS
        self.target = random.choice(choices)
        self.target_lbl.configure(text=display_name(self.target), text_color=COLORS["info"])
        self._refresh_kind()
        self.builder.clear()
        self.locked = False
        self.feedback.configure(text="Waiting for your sign…", text_color=COLORS["muted"])

    def _skip(self):
        self._next_target()

    def _speak_prompt(self):
        speak(display_name(self.target), rate=int(self.store.settings.get("tts_rate", 160)))

    def start_camera(self):
        self.cap = open_webcam(0)
        if not self.cap.isOpened():
            self.video.configure(text="⚠ Could not open webcam")
            return
        self.running = True
        self._tick()

    def _tick(self):
        if not self.running or self.cap is None:
            return
        ok, frame = self.cap.read()
        if ok:
            frame = cv2.flip(frame, 1)
            annotated, preds, _hand = self.recognizer.process(frame)
            label, score = (preds[0] if preds else (None, 0.0))
            if label and label != "none":
                self.live.configure(text=f"{display_name(label)}   {score:.0%}")
            else:
                self.live.configure(text="Detecting…")

            committed = self.builder.update(label, score)
            if committed and not self.locked:
                stray_letter = (not is_letter(self.target)) and is_letter(committed)
                if not stray_letter:
                    self._judge(committed, score)

            rgb = cv2.cvtColor(annotated, cv2.COLOR_BGR2RGB)
            img = Image.fromarray(rgb)
            host = getattr(self, "video_host", self.video)
            lw = host.winfo_width()
            lh = host.winfo_height()
            if lw < 80 or lh < 80:
                lw, lh = 480, 360
            img.thumbnail((lw, lh))
            ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=img.size)
            self.video.configure(image=ctk_img, text="")
            self.video.image = ctk_img
        self.after(15, self._tick)

    def _judge(self, committed, score):
        got = str(committed).replace(" ", "").lower()
        want = display_name(self.target).replace(" ", "").lower()
        raw = str(self.target).replace(" ", "").lower()
        ok = got == want or got == raw
        self.locked = True
        self.store.record_practice(ok)
        self.score.configure(text=self._score_text())
        if ok:
            self.feedback.configure(text=f"Nice — {display_name(self.target)}",
                                    text_color=COLORS["ok"])
            self.target_lbl.configure(text_color=COLORS["ok"])
            self.after(1100, self._next_target)
        else:
            self.feedback.configure(
                text=f"Got {committed} — need {display_name(self.target)}",
                text_color=COLORS["danger"])
            self.after(1400, self._unlock)

    def _unlock(self):
        self.locked = False
        self.builder.clear()
        self.feedback.configure(text="Try again…", text_color=COLORS["muted"])
        self.target_lbl.configure(text_color=COLORS["info"])

    def stop(self):
        self.running = False
        if self.cap is not None:
            self.cap.release()
            self.cap = None
        self.recognizer.close()


class TeachSignsPage(ctk.CTkFrame):
    """Teach personal gestures from a photo; match them live by hand shape."""

    def __init__(self, master, store):
        super().__init__(master, fg_color=COLORS["bg"])
        self.store = store
        self.recognizer = SignRecognizer(num_hands=1)
        self.cap = None
        self.running = False
        self._last_frame = None
        self._frozen_vec = None
        self._templates = store.list_custom_sign_vectors()

        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=0, minsize=SIDEBAR_WIDTH)
        self.grid_rowconfigure(0, weight=1)

        left = _card(self)
        left.grid(row=0, column=0, sticky="nsew", padx=(16, 8), pady=16)
        left.grid_rowconfigure(0, weight=1)
        left.grid_columnconfigure(0, weight=1)

        self.video_host = ctk.CTkFrame(left, fg_color="#0a0c12", corner_radius=12)
        self.video_host.grid(row=0, column=0, sticky="nsew", padx=12, pady=12)
        self.video_host.grid_propagate(False)
        self.video = ctk.CTkLabel(self.video_host, text="Starting camera…",
                                  text_color=COLORS["muted"])
        self.video.place(relx=0, rely=0, relwidth=1, relheight=1)

        self.live = ctk.CTkLabel(left, text="Hold your taught sign to test it",
                                 font=("Arial", 16, "bold"), text_color=COLORS["accent"])
        self.live.grid(row=1, column=0, pady=(0, 12))

        right = ctk.CTkScrollableFrame(self, fg_color=COLORS["surface"],
                                       corner_radius=16, width=SIDEBAR_WIDTH)
        right.grid(row=0, column=1, sticky="nsew", padx=(8, 16), pady=16)

        ctk.CTkLabel(right, text="My Signs", font=("Arial", 22, "bold"),
                     text_color=COLORS["text"]).pack(anchor="w", padx=16, pady=(16, 4))
        ctk.CTkLabel(
            right,
            text="Capture your hand, name the gesture, save. "
                 "Next time that pose is recognized on Home too.",
            text_color=COLORS["muted"], wraplength=SIDEBAR_WIDTH - 32, justify="left",
        ).pack(anchor="w", padx=16, pady=(0, 12))

        self.name_entry = ctk.CTkEntry(right, placeholder_text="Gesture name (e.g. Water)",
                                       height=40)
        self.name_entry.pack(fill="x", padx=16, pady=6)

        ctk.CTkButton(right, text="📷 Capture from camera", height=40,
                      fg_color=COLORS["info"], command=self._capture).pack(
                          fill="x", padx=16, pady=4)
        ctk.CTkButton(right, text="🖼 Pick a photo", height=40,
                      fg_color=COLORS["surface_2"], command=self._pick_photo).pack(
                          fill="x", padx=16, pady=4)
        ctk.CTkButton(right, text="💾 Save gesture", height=42,
                      fg_color=COLORS["primary"], command=self._save).pack(
                          fill="x", padx=16, pady=(8, 4))

        self.status = ctk.CTkLabel(right, text="", text_color=COLORS["accent"],
                                   wraplength=SIDEBAR_WIDTH - 32, justify="left")
        self.status.pack(anchor="w", padx=16, pady=(4, 8))

        ctk.CTkLabel(right, text="Saved gestures", font=("Arial", 14, "bold"),
                     text_color=COLORS["text"]).pack(anchor="w", padx=16, pady=(8, 4))
        self.list_box = ctk.CTkTextbox(right, height=180, font=("Arial", 13),
                                       fg_color=COLORS["surface_2"], text_color=COLORS["text"])
        self.list_box.pack(fill="x", padx=16, pady=(0, 16))
        self.list_box.configure(state="disabled")
        self._refresh_list()

        self.start_camera()

    def _refresh_list(self):
        signs = self.store.list_custom_signs()
        self.list_box.configure(state="normal")
        self.list_box.delete("1.0", "end")
        if not signs:
            self.list_box.insert("1.0", "No gestures yet — capture one above.")
        else:
            for s in signs:
                self.list_box.insert("end", f"• {s['label']}\n")
        self.list_box.configure(state="disabled")

    def start_camera(self):
        self.cap = open_webcam(0)
        if not self.cap.isOpened():
            self.video.configure(text="⚠ Could not open webcam")
            return
        self.running = True
        self._tick()

    def _tick(self):
        if not self.running or self.cap is None:
            return
        ok, frame = self.cap.read()
        if ok:
            frame = cv2.flip(frame, 1)
            self._last_frame = frame.copy()
            annotated, preds, hand_vec = self.recognizer.process(frame)
            label, conf = best_match(hand_vec, self._templates)
            if label:
                self.live.configure(
                    text=f"✓ {label}   {conf:.0%}  ·  my sign",
                    text_color=COLORS["ok"],
                )
            else:
                self.live.configure(
                    text="Hold a taught sign in view to test",
                    text_color=COLORS["accent"],
                )
            self._show_frame(annotated)
        self.after(33, self._tick)

    def _show_frame(self, frame_bgr):
        rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        img = Image.fromarray(rgb)
        lw = max(self.video_host.winfo_width(), 320)
        lh = max(self.video_host.winfo_height(), 240)
        img.thumbnail((lw, lh))
        ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=img.size)
        self.video.configure(image=ctk_img, text="")
        self.video.image = ctk_img

    def _capture_from_frame(self, frame):
        annotated, _, hand_vec = self.recognizer.process(frame)
        if not hand_vec:
            self.status.configure(
                text="No hand detected. Show one clear hand and try again.")
            return False
        self._frozen_vec = hand_vec
        self._show_frame(annotated)
        self.status.configure(text="Captured — enter a name and press Save.")
        return True

    def _capture(self):
        if self._last_frame is None:
            self.status.configure(text="Camera not ready yet.")
            return
        self._capture_from_frame(self._last_frame.copy())

    def _pick_photo(self):
        path = filedialog.askopenfilename(
            title="Choose a hand photo",
            filetypes=[
                ("Images", "*.png *.jpg *.jpeg *.webp *.bmp"),
                ("All files", "*.*"),
            ],
        )
        if not path:
            return
        frame = cv2.imread(path)
        if frame is None:
            self.status.configure(text="Could not read that image.")
            return
        self._capture_from_frame(frame)

    def _save(self):
        if not self._frozen_vec:
            self.status.configure(text="Capture a hand or pick a photo first.")
            return
        label = self.name_entry.get().strip()
        try:
            self.store.add_custom_sign(label, self._frozen_vec)
        except ValueError as exc:
            self.status.configure(text=str(exc))
            return
        self._templates = self.store.list_custom_sign_vectors()
        self._frozen_vec = None
        self.name_entry.delete(0, "end")
        self._refresh_list()
        self.status.configure(
            text=f"Saved “{label}”. It works here and on Home.")

    def stop(self):
        self.running = False
        if self.cap is not None:
            self.cap.release()
            self.cap = None
        self.recognizer.close()


class TranslatorPage(ctk.CTkFrame):
    def __init__(self, master, store):
        super().__init__(master, fg_color=COLORS["bg"])
        self.store = store

        inner = _card(self)
        inner.pack(fill="both", expand=True, padx=20, pady=20)

        ctk.CTkLabel(inner, text="Speech & Text Translator",
                     font=("Arial", 26, "bold"), text_color=COLORS["text"]).pack(
                         pady=(22, 2))
        ctk.CTkLabel(inner, text="Type or paste — Translate, then Speak translation (click only).",
                     text_color=COLORS["muted"]).pack()

        langs = ctk.CTkFrame(inner, fg_color="transparent")
        langs.pack(fill="x", padx=24, pady=16)
        langs.grid_columnconfigure((0, 2), weight=1)
        self.src = LanguagePicker(langs, LANG_NAMES, value="English", width=200)
        self.src.grid(row=0, column=0, sticky="ew", padx=6)
        ctk.CTkLabel(langs, text="→", text_color=COLORS["muted"],
                     font=("Arial", 18)).grid(row=0, column=1, padx=8)
        dest = self.store.settings.get("translate_lang") or "Hindi"
        if dest not in LANG_NAMES:
            dest = "Hindi"
        self.dst = LanguagePicker(langs, LANG_NAMES, value=dest, width=200)
        self.dst.grid(row=0, column=2, sticky="ew", padx=6)

        boxes = ctk.CTkFrame(inner, fg_color="transparent")
        boxes.pack(fill="both", expand=True, padx=24)
        boxes.grid_columnconfigure((0, 1), weight=1)
        boxes.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(boxes, text="INPUT", text_color=COLORS["muted"]).grid(
            row=0, column=0, sticky="w")
        ctk.CTkLabel(boxes, text="TRANSLATION", text_color=COLORS["muted"]).grid(
            row=0, column=1, sticky="w", padx=(12, 0))
        self.inp = ctk.CTkTextbox(boxes, corner_radius=12, fg_color=COLORS["surface_2"],
                                  font=("Arial", 16))
        self.inp.grid(row=1, column=0, sticky="nsew", pady=(4, 8))
        self.out = ctk.CTkTextbox(boxes, corner_radius=12, fg_color=COLORS["surface_2"],
                                  font=("Arial", 16))
        self.out.grid(row=1, column=1, sticky="nsew", padx=(12, 0), pady=(4, 8))

        chips = ctk.CTkFrame(inner, fg_color="transparent")
        chips.pack(fill="x", padx=24, pady=(0, 8))
        ctk.CTkLabel(chips, text="Quick phrases", text_color=COLORS["muted"]).pack(
            side="left", padx=(0, 8))
        for phrase in PHRASES:
            ctk.CTkButton(chips, text=phrase, width=1, height=28, corner_radius=14,
                          fg_color=COLORS["surface_2"], font=("Arial", 11),
                          command=lambda p=phrase: self._use_phrase(p)).pack(
                              side="left", padx=3)

        actions = ctk.CTkFrame(inner, fg_color="transparent")
        actions.pack(pady=(4, 10))
        ctk.CTkButton(actions, text="Speak input", width=140, height=42,
                      fg_color=COLORS["surface_2"], command=self._speak_input).pack(
                          side="left", padx=6)
        ctk.CTkButton(actions, text="Translate", width=160, height=42,
                      fg_color=COLORS["info"], command=self._translate).pack(
                          side="left", padx=6)
        ctk.CTkButton(actions, text="🔊 Speak translation", width=180, height=42,
                      fg_color=COLORS["primary"], command=self._speak_translation).pack(
                          side="left", padx=6)
        ctk.CTkButton(actions, text="Copy", width=140, height=42,
                      fg_color=COLORS["surface_2"], command=self._copy).pack(
                          side="left", padx=6)

        self.status = ctk.CTkLabel(inner, text="Needs a network connection for translation and Speak translation.",
                                   text_color=COLORS["muted"])
        self.status.pack(pady=(0, 18))
        self._tts_job = self.after(400, self._poll_tts)

    def _poll_tts(self):
        note = pop_status()
        if note:
            self.status.configure(text=note)
        self._tts_job = self.after(400, self._poll_tts)

    def stop(self):
        if getattr(self, "_tts_job", None):
            self.after_cancel(self._tts_job)
            self._tts_job = None

    def _use_phrase(self, phrase):
        self.inp.delete("1.0", "end")
        self.inp.insert("1.0", phrase)

    def _translate(self):
        text = self.inp.get("1.0", "end").strip()
        if not text:
            self.status.configure(text="Type something first.")
            return
        src, dst = self.src.get(), self.dst.get()
        if src == dst:
            self._set_out(text)
            self.status.configure(text="Same language — copied across.")
            return
        self.status.configure(text="Translating…")
        self.after(20, lambda: self._fetch(text, src, dst))

    def _fetch(self, text, src, dst):
        try:
            translated = translate_text(text, src, dst)
            self._set_out(translated)
            self.status.configure(text="Done.")
        except RuntimeError as exc:
            self.status.configure(text=str(exc) + " Check the network and try again.")

    def _set_out(self, text):
        self.out.configure(state="normal")
        self.out.delete("1.0", "end")
        self.out.insert("1.0", text)
        self.out.configure(state="normal")

    def _speak_input(self):
        text = self.inp.get("1.0", "end").strip()
        if not text:
            self.status.configure(text="Type something first.")
            return
        self.status.configure(text=f"Speaking {self.src.get()}…")
        speak(
            text,
            rate=int(self.store.settings.get("tts_rate", 160)),
            language=self.src.get(),
        )

    def _speak_translation(self):
        text = self.out.get("1.0", "end").strip()
        if not text:
            self.status.configure(text="Translate first, then press Speak translation.")
            return
        self.status.configure(text=f"Speaking {self.dst.get()}…")
        speak(
            text,
            rate=int(self.store.settings.get("tts_rate", 160)),
            language=self.dst.get(),
        )

    def _speak(self):
        self._speak_translation()

    def _copy(self):
        text = self.out.get("1.0", "end").strip() or self.inp.get("1.0", "end").strip()
        self.clipboard_clear()
        self.clipboard_append(text)
        self.status.configure(text="Copied.")


class AboutPage(ctk.CTkFrame):
    def __init__(self, master, on_translate=None, on_home=None):
        super().__init__(master, fg_color=COLORS["bg"])
        card = _card(self, width=720)
        card.place(relx=0.5, rely=0.5, anchor="center")

        ctk.CTkLabel(card, text="👐", font=("Arial", 54)).pack(pady=(28, 0))
        ctk.CTkLabel(card, text=APP_NAME, font=("Arial", 32, "bold"),
                     text_color=COLORS["text"]).pack()
        ctk.CTkLabel(card, text=APP_TAGLINE, text_color=COLORS["muted"]).pack(pady=(0, 12))

        body = (
            "A real-time sign language detection and translation system. "
            "Computer vision reads your hand from the webcam, a MediaPipe "
            "gesture model turns it into words, and you can build sentences, "
            "speak them aloud, or send them through the translator — all on "
            "this machine, with no cloud camera feed."
        )
        ctk.CTkLabel(card, text=body, wraplength=620, justify="center",
                     font=("Arial", 14), text_color=COLORS["text"]).pack(
                         padx=28, pady=(8, 16))

        tags = ctk.CTkFrame(card, fg_color="transparent")
        tags.pack(pady=8)
        for t in ("AI-powered detection", "Real-time video", "Offline speech",
                  "Multi-language translation", "Practice studio", "Privacy first"):
            ctk.CTkLabel(tags, text=t, fg_color=COLORS["surface_2"], corner_radius=12,
                         text_color=COLORS["info"], font=("Arial", 12)).pack(
                             side="left", padx=4, ipadx=10, ipady=6)

        btns = ctk.CTkFrame(card, fg_color="transparent")
        btns.pack(pady=(22, 28))
        ctk.CTkButton(btns, text="Back to Home", width=160, height=40,
                      fg_color=COLORS["surface_2"],
                      command=on_home).pack(side="left", padx=8)
        ctk.CTkButton(btns, text="Try Translator", width=180, height=40,
                      fg_color=COLORS["info"],
                      command=on_translate).pack(side="left", padx=8)


class SettingsPage(ctk.CTkFrame):
    def __init__(self, master, store):
        super().__init__(master, fg_color=COLORS["bg"])
        self.store = store
        s = store.settings

        card = _card(self, width=520)
        card.place(relx=0.5, rely=0.45, anchor="center")

        ctk.CTkLabel(card, text="Settings", font=("Arial", 26, "bold"),
                     text_color=COLORS["text"]).pack(pady=(24, 6), padx=24, anchor="w")
        ctk.CTkLabel(card, text="These apply the next time you open Home or Practice.",
                     text_color=COLORS["muted"]).pack(anchor="w", padx=24)

        ctk.CTkLabel(card, text="Minimum confidence", text_color=COLORS["text"]).pack(
            anchor="w", padx=24, pady=(18, 0))
        self.conf = ctk.CTkSlider(card, from_=0.2, to=0.9, number_of_steps=14)
        self.conf.set(float(s.get("min_confidence", 0.45)))
        self.conf.pack(fill="x", padx=24, pady=6)
        self.conf_lbl = ctk.CTkLabel(card, text="", text_color=COLORS["muted"])
        self.conf_lbl.pack(anchor="w", padx=24)
        self.conf.configure(command=lambda v: self.conf_lbl.configure(
            text=f"{float(v):.2f}"))
        self.conf_lbl.configure(text=f"{float(s.get('min_confidence', 0.45)):.2f}")

        ctk.CTkLabel(card, text="Speak speed", text_color=COLORS["text"]).pack(
            anchor="w", padx=24, pady=(14, 0))
        self.rate = ctk.CTkSlider(card, from_=120, to=220, number_of_steps=20)
        self.rate.set(float(s.get("tts_rate", 160)))
        self.rate.pack(fill="x", padx=24, pady=6)

        self.auto = ctk.CTkSwitch(card, text="Auto-speak each committed word on Home",
                                  progress_color=COLORS["accent"])
        if s.get("auto_speak"):
            self.auto.select()
        self.auto.pack(anchor="w", padx=24, pady=10)

        self.ac = ctk.CTkSwitch(card, text="Autocorrect fingerspelled words",
                                progress_color=COLORS["accent"])
        if s.get("autocorrect", True):
            self.ac.select()
        self.ac.pack(anchor="w", padx=24, pady=(0, 8))

        self.subs = ctk.CTkSwitch(card, text="Live dual subtitles on Home",
                                  progress_color=COLORS["info"])
        if s.get("dual_subs", True):
            self.subs.select()
        self.subs.pack(anchor="w", padx=24, pady=(0, 8))

        ctk.CTkLabel(card, text="Home translation language", text_color=COLORS["text"]).pack(
            anchor="w", padx=24, pady=(10, 0))
        self.tlang = LanguagePicker(
            card, LANG_NAMES,
            value=s.get("translate_lang") if s.get("translate_lang") in LANG_NAMES else "Hindi",
            width=240,
        )
        self.tlang.pack(anchor="w", padx=24, pady=6)

        self.msg = ctk.CTkLabel(card, text="", text_color=COLORS["accent"])
        self.msg.pack()
        ctk.CTkButton(card, text="Save settings", height=42, width=240,
                      fg_color=COLORS["primary"], command=self._save).pack(pady=(8, 24))

    def _save(self):
        self.store.update_settings(
            min_confidence=round(float(self.conf.get()), 2),
            tts_rate=int(self.rate.get()),
            auto_speak=bool(self.auto.get()),
            autocorrect=bool(self.ac.get()),
            dual_subs=bool(self.subs.get()),
            translate_lang=self.tlang.get(),
        )
        self.msg.configure(text="Saved")
