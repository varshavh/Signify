"""
Signify — desktop sign-language recognition app (CustomTkinter).

Screens:
  * AuthScreen    — local sign in / sign up
  * MainShell     — Home, Dashboard, Profile, Practice, Translate, About, Settings

Run:  python -m signify.app     (from the repo root)
"""

from datetime import datetime
from pathlib import Path
import sys
import threading
import time

import cv2
import customtkinter as ctk
from PIL import Image

from .config import APP_NAME, COLORS, NUM_HANDS, SIDEBAR_WIDTH, STABILITY_FRAMES
from .camera import open_webcam
from .recognizer import SignRecognizer
from .sentence_builder import SentenceBuilder, display_name, is_letter
from .autocorrect import AutoCorrector
from .store import AppStore, AuthError, LocalAuth
from .tts import speak
from .translate import LANG_NAMES, translate_text
from .widgets import LanguagePicker
from .pages import (AboutPage, DashboardPage, PracticePage, ProfilePage,
                    SettingsPage, TranslatorPage)

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")

HISTORY_FILE = Path(__file__).resolve().parent.parent / "saved_sentences.txt"

NAV = [
    ("home", "Home"),
    ("dash", "Dashboard"),
    ("profile", "Profile"),
    ("practice", "Practice"),
    ("translate", "Translate"),
    ("about", "About"),
    ("settings", "Settings"),
]


class AuthScreen(ctk.CTkFrame):
    """Sign in, or create a local account with profile details."""

    def __init__(self, master, auth: LocalAuth, on_success):
        super().__init__(master, fg_color=COLORS["bg"])
        self.auth = auth
        self.on_success = on_success
        self._panel = None
        self._show_login()

    def _clear(self):
        if self._panel is not None:
            self._panel.destroy()
            self._panel = None

    def _card(self, width=440, height=520):
        self._clear()
        card = ctk.CTkFrame(self, fg_color=COLORS["surface"], corner_radius=20,
                            width=width, height=height)
        card.place(relx=0.5, rely=0.5, anchor="center")
        card.pack_propagate(False)
        self._panel = card
        return card

    def _show_login(self):
        card = self._card(440, 500)
        empty = self.auth.user_count() == 0

        ctk.CTkLabel(card, text="👐", font=("Arial", 52)).pack(pady=(32, 2))
        ctk.CTkLabel(card, text=APP_NAME, font=("Arial", 32, "bold"),
                     text_color=COLORS["text"]).pack()
        hint = ("No account yet — create one to get started." if empty
                else "Sign in to load your profile and history.")
        ctk.CTkLabel(card, text=hint, font=("Arial", 13),
                     text_color=COLORS["muted"], wraplength=340).pack(pady=(4, 18))

        self.user = ctk.CTkEntry(card, placeholder_text="Username", width=300, height=44)
        self.user.pack(pady=6)
        last = self.auth.last_username()
        if last:
            self.user.insert(0, last)
        self.pw = ctk.CTkEntry(card, placeholder_text="Password", show="•",
                               width=300, height=44)
        self.pw.pack(pady=6)
        self.pw.bind("<Return>", lambda e: self._try_login())

        self.msg = ctk.CTkLabel(card, text="", font=("Arial", 12),
                                text_color=COLORS["danger"], wraplength=320)
        self.msg.pack(pady=(8, 0))

        ctk.CTkButton(card, text="Sign In", width=300, height=46, corner_radius=10,
                      font=("Arial", 15, "bold"), fg_color=COLORS["primary"],
                      hover_color=COLORS["primary_h"],
                      command=self._try_login).pack(pady=(12, 8))
        ctk.CTkButton(card, text="Create account", width=300, height=42, corner_radius=10,
                      fg_color=COLORS["surface_2"], hover_color=COLORS["info"],
                      command=self._show_signup).pack()
        ctk.CTkLabel(card, text="Accounts stay on this computer (local database).",
                     font=("Arial", 11), text_color=COLORS["muted"]).pack(pady=14)

        if empty:
            self.after(80, self._show_signup)

    def _try_login(self):
        try:
            username = self.auth.login(self.user.get(), self.pw.get())
        except AuthError as exc:
            if str(exc) == "NO_ACCOUNT":
                self.msg.configure(
                    text="No account with that username. Create one below.")
                self.after(600, self._show_signup)
            else:
                self.msg.configure(text=str(exc))
                self.pw.delete(0, "end")
            return
        self.on_success(username)

    def _show_signup(self):
        self._clear()
        wrap = ctk.CTkScrollableFrame(self, fg_color=COLORS["surface"],
                                      width=460, height=620, corner_radius=20)
        wrap.place(relx=0.5, rely=0.5, anchor="center")
        self._panel = wrap

        ctk.CTkLabel(wrap, text="Create account", font=("Arial", 26, "bold"),
                     text_color=COLORS["text"]).pack(pady=(18, 4), padx=16)
        ctk.CTkLabel(wrap, text="Fill your profile now — it loads again on every login.",
                     text_color=COLORS["muted"], wraplength=380).pack(padx=16)

        def field(placeholder, show=None):
            e = ctk.CTkEntry(wrap, placeholder_text=placeholder, width=320, height=42)
            if show:
                e.configure(show=show)
            e.pack(pady=6)
            return e

        self.su_user = field("Username")
        self.su_pw = field("Password", show="•")
        self.su_pw2 = field("Confirm password", show="•")
        self.su_name = field("Full name")
        self.su_email = field("Email")
        self.su_loc = field("Location (e.g. India)")
        self.su_bio = field("Short bio")
        self.su_pw2.bind("<Return>", lambda e: self._try_signup())

        self.su_msg = ctk.CTkLabel(wrap, text="", font=("Arial", 12),
                                   text_color=COLORS["danger"], wraplength=340)
        self.su_msg.pack(pady=(8, 0))

        ctk.CTkButton(wrap, text="Create account & continue", width=320, height=46,
                      font=("Arial", 14, "bold"), fg_color=COLORS["info"],
                      hover_color=COLORS["primary"],
                      command=self._try_signup).pack(pady=(10, 8))
        if self.auth.user_count() > 0:
            ctk.CTkButton(wrap, text="Back to sign in", width=320, height=38,
                          fg_color=COLORS["surface_2"],
                          command=self._show_login).pack(pady=(0, 18))
        else:
            ctk.CTkLabel(wrap, text="You’ll sign in with this username next time.",
                         text_color=COLORS["muted"], font=("Arial", 11)).pack(pady=(0, 18))

    def _try_signup(self):
        try:
            username = self.auth.signup(
                self.su_user.get(), self.su_pw.get(), self.su_pw2.get(),
                self.su_name.get(), self.su_email.get(),
                self.su_loc.get(), self.su_bio.get(),
            )
        except AuthError as exc:
            self.su_msg.configure(text=str(exc))
            return
        self.on_success(username)


class DetectScreen(ctk.CTkFrame):
    def __init__(self, master, store):
        super().__init__(master, fg_color=COLORS["bg"])
        self.store = store
        settings = store.settings
        min_conf = float(settings.get("min_confidence", 0.45))

        self.recognizer = None  # created on the camera thread
        self.corrector = AutoCorrector(extra_words=[APP_NAME])
        self.builder = SentenceBuilder(stability=STABILITY_FRAMES,
                                       min_confidence=min_conf,
                                       corrector=self.corrector)
        self.builder.autocorrect_enabled = bool(settings.get("autocorrect", True))
        self.running = False
        self.current_pred = ("—", 0.0)
        self._frame_job = None
        self._video_size = (640, 360)
        self._stop_evt = threading.Event()
        self._lock = threading.Lock()
        self._latest = None
        self._cam_error = None
        self._worker = None
        self._tr_result = None
        self._sub_job = None
        self._tr_busy = False
        self._tr_source = ""
        self._tr_lang = ""

        self._build_ui()
        self.start_camera()

    def _build_ui(self):
        body = ctk.CTkFrame(self, fg_color=COLORS["bg"])
        body.pack(fill="both", expand=True, padx=12, pady=12)
        body.grid_columnconfigure(0, weight=1)
        body.grid_columnconfigure(1, weight=0, minsize=SIDEBAR_WIDTH)
        body.grid_rowconfigure(0, weight=1)

        left = ctk.CTkFrame(body, fg_color=COLORS["surface"], corner_radius=16)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        left.grid_rowconfigure(0, weight=1)
        left.grid_columnconfigure(0, weight=1)

        self.video_host = ctk.CTkFrame(left, fg_color="#0a0c12", corner_radius=12)
        self.video_host.grid(row=0, column=0, sticky="nsew", padx=12, pady=(12, 6))
        self.video_host.grid_propagate(False)
        self.video_label = ctk.CTkLabel(self.video_host, text="Starting camera…",
                                        text_color=COLORS["muted"])
        self.video_label.place(relx=0, rely=0, relwidth=1, relheight=1)

        self.subs = ctk.CTkFrame(left, fg_color="#0a0c12", corner_radius=12)
        ctk.CTkLabel(self.subs, text="EN", font=("Arial", 11, "bold"),
                     text_color=COLORS["muted"]).pack(anchor="w", padx=14, pady=(10, 0))
        self.sub_en = ctk.CTkLabel(
            self.subs, text="Sign to see English here", font=("Arial", 22, "bold"),
            text_color=COLORS["text"], wraplength=720, justify="left", anchor="w",
        )
        self.sub_en.pack(fill="x", padx=14, pady=(0, 6))
        self.sub_lang_tag = ctk.CTkLabel(self.subs, text="HI", font=("Arial", 11, "bold"),
                                         text_color=COLORS["info"])
        self.sub_lang_tag.pack(anchor="w", padx=14)
        self.sub_tr = ctk.CTkLabel(
            self.subs, text="Translation appears here", font=("Arial", 20),
            text_color=COLORS["info"], wraplength=720, justify="left", anchor="w",
        )
        self.sub_tr.pack(fill="x", padx=14, pady=(0, 12))
        self.subs.grid(row=1, column=0, sticky="ew", padx=12, pady=(0, 6))

        self.pred_label = ctk.CTkLabel(left, text="Detecting…", font=("Arial", 16, "bold"),
                                       text_color=COLORS["accent"])
        self.pred_label.grid(row=2, column=0, pady=(0, 10))

        right = ctk.CTkScrollableFrame(
            body, fg_color=COLORS["surface"], corner_radius=16,
            width=SIDEBAR_WIDTH,
        )
        right.grid(row=0, column=1, sticky="nsew")

        who = self.store.profile.get("name") or self.store.username
        ctk.CTkLabel(right, text=f"Logged in as {who}", font=("Arial", 12),
                     text_color=COLORS["muted"]).pack(anchor="w", padx=18, pady=(16, 0))
        ctk.CTkLabel(right, text="Sentence", font=("Arial", 16, "bold"),
                     text_color=COLORS["text"]).pack(anchor="w", padx=18, pady=(10, 6))

        self.sentence_box = ctk.CTkTextbox(right, height=140, corner_radius=12,
                                           font=("Arial", 18), fg_color=COLORS["surface_2"],
                                           text_color=COLORS["text"], wrap="word")
        self.sentence_box.pack(fill="x", padx=18)
        self.sentence_box.insert("1.0", "")
        self.sentence_box.configure(state="disabled")

        ctk.CTkLabel(right, text="Letters spell into a word; pause or press "
                     "“Space” to finish it. Whole-word signs stand alone.",
                     font=("Arial", 11), text_color=COLORS["muted"],
                     wraplength=340, justify="left").pack(anchor="w", padx=18, pady=(6, 0))

        btns = ctk.CTkFrame(right, fg_color="transparent")
        btns.pack(fill="x", padx=18, pady=14)
        grid = [
            ("␣ Space", self._space, COLORS["surface_2"]),
            ("⌫ Backspace", self._backspace, COLORS["surface_2"]),
            (".  Stop", self._period, COLORS["surface_2"]),
            ("🗑 Clear", self._clear, COLORS["surface_2"]),
            ("🔊 Speak", self._speak, COLORS["primary"]),
            ("📋 Copy", self._copy, COLORS["surface_2"]),
            ("💾 Save", self._save, COLORS["accent"]),
        ]
        for i, (txt, cmd, color) in enumerate(grid):
            ctk.CTkButton(btns, text=txt, command=cmd, corner_radius=10, height=40,
                          fg_color=color, hover_color=COLORS["primary_h"],
                          font=("Arial", 13)).grid(row=i // 3, column=i % 3,
                                                    padx=5, pady=5, sticky="ew")
        btns.grid_columnconfigure((0, 1, 2), weight=1)

        self.pause_btn = ctk.CTkButton(right, text="⏸ Pause detection",
                                       command=self._toggle_pause, corner_radius=10,
                                       height=42, fg_color=COLORS["surface_2"],
                                       font=("Arial", 13))
        self.pause_btn.pack(fill="x", padx=18, pady=(0, 8))

        self.autocorrect_switch = ctk.CTkSwitch(
            right, text="Autocorrect spelled words", command=self._toggle_autocorrect,
            font=("Arial", 13), progress_color=COLORS["accent"])
        if self.builder.autocorrect_enabled:
            self.autocorrect_switch.select()
        self.autocorrect_switch.pack(anchor="w", padx=18, pady=(0, 6))

        self.auto_speak = ctk.CTkSwitch(
            right, text="Voice output (auto-speak words)",
            command=self._toggle_auto_speak,
            font=("Arial", 13), progress_color=COLORS["info"])
        if self.store.settings.get("auto_speak"):
            self.auto_speak.select()
        self.auto_speak.pack(anchor="w", padx=18, pady=(0, 6))

        self.subs_switch = ctk.CTkSwitch(
            right, text="Live dual subtitles under camera",
            command=self._toggle_subs,
            font=("Arial", 13), progress_color=COLORS["info"])
        if self.store.settings.get("dual_subs", True):
            self.subs_switch.select()
        self.subs_switch.pack(anchor="w", padx=18, pady=(0, 8))

        ctk.CTkLabel(right, text="Sensitivity", font=("Arial", 13),
                     text_color=COLORS["muted"]).pack(anchor="w", padx=18, pady=(6, 0))
        self.conf_slider = ctk.CTkSlider(right, from_=0.2, to=0.9, number_of_steps=14,
                                         command=self._set_conf)
        self.conf_slider.set(self.builder.min_confidence)
        self.conf_slider.pack(fill="x", padx=18, pady=(0, 4))
        self.conf_val = ctk.CTkLabel(
            right, text=f"min confidence: {self.builder.min_confidence:.2f}",
            font=("Arial", 11), text_color=COLORS["muted"])
        self.conf_val.pack(anchor="w", padx=18)

        ctk.CTkLabel(right, text="Translate sentence", font=("Arial", 13, "bold"),
                     text_color=COLORS["text"]).pack(anchor="w", padx=18, pady=(14, 4))
        pref = self.store.settings.get("translate_lang") or "Hindi"
        if pref not in LANG_NAMES:
            pref = "Hindi"
        self.tlang = LanguagePicker(
            right, LANG_NAMES, value=pref, command=self._on_lang_chosen, width=SIDEBAR_WIDTH - 40,
        )
        self.tlang.pack(fill="x", padx=18)
        trow = ctk.CTkFrame(right, fg_color="transparent")
        trow.pack(fill="x", padx=18, pady=(8, 0))
        ctk.CTkButton(trow, text="Translate", height=32,
                      fg_color=COLORS["info"], command=self._translate_sentence).pack(
                          side="left", expand=True, fill="x")
        ctk.CTkButton(trow, text="Speak", height=32,
                      fg_color=COLORS["surface_2"], command=self._speak_translation).pack(
                          side="left", expand=True, fill="x", padx=(8, 0))
        self.tbox = ctk.CTkTextbox(right, height=72, corner_radius=12,
                                   font=("Arial", 14), fg_color=COLORS["surface_2"],
                                   text_color=COLORS["text"], wrap="word")
        self.tbox.pack(fill="x", padx=18, pady=(8, 0))
        self.tstatus = ctk.CTkLabel(right, text="English → chosen language",
                                    font=("Arial", 11), text_color=COLORS["muted"])
        self.tstatus.pack(anchor="w", padx=18, pady=(4, 0))

        ctk.CTkLabel(right, text="Recent detections", font=("Arial", 13),
                     text_color=COLORS["muted"]).pack(anchor="w", padx=18, pady=(12, 2))
        self.log_box = ctk.CTkTextbox(right, height=90, corner_radius=12,
                                      font=("Arial", 12), fg_color=COLORS["surface_2"],
                                      text_color=COLORS["muted"])
        self.log_box.pack(fill="both", expand=True, padx=18, pady=(0, 18))
        self.log_box.configure(state="disabled")
        self._apply_subs_visible(bool(self.subs_switch.get()))

    def start_camera(self):
        self.running = True
        self._stop_evt.clear()
        self._worker = threading.Thread(target=self._cam_loop, daemon=True)
        self._worker.start()
        self._pump_ui()

    def _cam_loop(self):
        cap = open_webcam(0)
        if not cap.isOpened():
            self._cam_error = "camera"
            return
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
        try:
            recognizer = SignRecognizer(num_hands=NUM_HANDS)
        except Exception:
            cap.release()
            self._cam_error = "camera"
            return
        try:
            while not self._stop_evt.is_set():
                if not self.running:
                    time.sleep(0.05)
                    continue
                ok, frame = cap.read()
                if not ok:
                    time.sleep(0.02)
                    continue
                frame = cv2.flip(frame, 1)
                try:
                    annotated, preds = recognizer.process(frame)
                except Exception:
                    continue
                with self._lock:
                    self._latest = (annotated, preds)
        finally:
            recognizer.close()
            cap.release()

    def _pump_ui(self):
        if self._stop_evt.is_set():
            return
        if self._cam_error:
            self.video_label.configure(text="⚠ Could not open webcam")
            self._cam_error = None
        payload = None
        tr = None
        with self._lock:
            if self._tr_result is not None:
                tr = self._tr_result
                self._tr_result = None
            if self._latest is not None:
                payload = self._latest
                self._latest = None
        if tr is not None:
            self._apply_translation(*tr)
        if payload is not None:
            annotated, preds = payload
            label, score = (preds[0] if preds else (None, 0.0))
            if label and label != "none":
                self.current_pred = (label, score)
                shown = display_name(label)
                kind = "letter" if is_letter(label) else "word"
                self.pred_label.configure(text=f"{shown}   {score:.0%}   ·  {kind}")
            else:
                self.pred_label.configure(text="Detecting…")

            if self.running:
                committed = self.builder.update(label, score)
                if committed:
                    self._refresh_sentence()
                    self._append_log(committed)
                    self.store.record_detection(committed, score)
                    if self.auto_speak.get():
                        speak(committed, rate=int(self.store.settings.get("tts_rate", 160)))

            rgb = cv2.cvtColor(annotated, cv2.COLOR_BGR2RGB)
            img = Image.fromarray(rgb)
            host = getattr(self, "video_host", self.video_label)
            lw = host.winfo_width()
            lh = host.winfo_height()
            if lw >= 80 and lh >= 80:
                self._video_size = (lw, lh)
            img = self._cover(img, self._video_size)
            ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=self._video_size)
            self.video_label.configure(image=ctk_img, text="")
            self.video_label.image = ctk_img

        self._frame_job = self.after(33, self._pump_ui)

    @staticmethod
    def _cover(img, size):
        """Scale and crop so the frame fills the video area (no empty margins)."""
        tw, th = size
        if tw < 2 or th < 2:
            return img
        scale = max(tw / img.width, th / img.height)
        nw = max(1, int(img.width * scale))
        nh = max(1, int(img.height * scale))
        img = img.resize((nw, nh), Image.BILINEAR)
        left = max(0, (nw - tw) // 2)
        top = max(0, (nh - th) // 2)
        return img.crop((left, top, left + tw, top + th))

    def _refresh_sentence(self):
        self.sentence_box.configure(state="normal")
        self.sentence_box.delete("1.0", "end")
        self.sentence_box.insert("1.0", self.builder.text())
        self.sentence_box.configure(state="disabled")
        self._sync_en_sub()
        self._schedule_live_translate()

    def _target_lang(self) -> str:
        picker = getattr(self, "tlang", None)
        if picker is not None:
            return picker.get() or "Hindi"
        return self.store.settings.get("translate_lang") or "Hindi"

    def _sync_en_sub(self):
        text = self.builder.text().strip()
        self.sub_en.configure(text=text or "Sign to see English here")
        lang = self._target_lang()
        self.sub_lang_tag.configure(text=(lang[:2] if lang else "TR").upper())

    def _schedule_live_translate(self):
        if not bool(self.subs_switch.get()):
            return
        if self._sub_job is not None:
            self.after_cancel(self._sub_job)
        self._sub_job = self.after(900, self._live_translate)

    def _live_translate(self):
        self._sub_job = None
        text = self.builder.text().strip()
        target = self._target_lang()
        self._sync_en_sub()
        if not text:
            self.sub_tr.configure(text="Translation appears here")
            return
        if text == self._tr_source and target == self._tr_lang:
            return
        if self._tr_busy:
            self._sub_job = self.after(400, self._live_translate)
            return
        self._start_translate(text, target, live=True)

    def _start_translate(self, text, target, live=False):
        self._tr_busy = True
        if live:
            current = self.sub_tr.cget("text")
            if not current or current in ("Translation appears here", "Translation unavailable"):
                self.sub_tr.configure(text="…")
        else:
            self.tstatus.configure(text="Translating…")
        threading.Thread(target=self._translate_worker,
                         args=(text, target), daemon=True).start()

    def _translate_worker(self, text, target):
        err, out = None, None
        try:
            out = translate_text(text, "English", target)
        except Exception as exc:
            err = str(exc) if str(exc) else exc.__class__.__name__
        with self._lock:
            self._tr_result = (out, err, target)

    def _append_log(self, word):
        self.log_box.configure(state="normal")
        self.log_box.insert("end", f"{datetime.now():%H:%M:%S}  {word}\n")
        self.log_box.see("end")
        self.log_box.configure(state="disabled")

    def _space(self):
        self.builder.add_space(); self._refresh_sentence()

    def _period(self):
        self.builder.add_period(); self._refresh_sentence()

    def _backspace(self):
        self.builder.backspace(); self._refresh_sentence()

    def _clear(self):
        self.builder.clear()
        self._tr_source = ""
        self._refresh_sentence()

    def _copy(self):
        text = self.builder.text()
        self.clipboard_clear(); self.clipboard_append(text)

    def _save(self):
        text = self.builder.text().strip()
        if not text:
            return
        with open(HISTORY_FILE, "a", encoding="utf-8") as f:
            f.write(f"{datetime.now():%Y-%m-%d %H:%M:%S}\t{text}\n")
        self.store.add_sentence(text)

    def _speak(self):
        speak(self.builder.text(), rate=int(self.store.settings.get("tts_rate", 160)))

    def _toggle_pause(self):
        self.running = not self.running
        if self.running:
            self.pause_btn.configure(text="⏸ Pause detection")
        else:
            self.pause_btn.configure(text="▶ Resume detection")

    def _set_conf(self, val):
        self.builder.min_confidence = float(val)
        self.conf_val.configure(text=f"min confidence: {float(val):.2f}")

    def _toggle_autocorrect(self):
        enabled = bool(self.autocorrect_switch.get())
        self.builder.autocorrect_enabled = enabled
        self.store.update_settings(autocorrect=enabled)

    def _toggle_auto_speak(self):
        self.store.update_settings(auto_speak=bool(self.auto_speak.get()))

    def _apply_subs_visible(self, on: bool):
        if on:
            self.subs.grid()
            self.update_idletasks()
            self._sync_en_sub()
            self._schedule_live_translate()
        else:
            self.subs.grid_remove()
            if self._sub_job is not None:
                self.after_cancel(self._sub_job)
                self._sub_job = None

    def _toggle_subs(self):
        on = bool(self.subs_switch.get())
        self.store.update_settings(dual_subs=on)
        self._apply_subs_visible(on)

    def _translate_sentence(self):
        text = self.builder.text().strip()
        if not text:
            self.tstatus.configure(text="Build a sentence first.")
            return
        target = self._target_lang()
        if self._sub_job is not None:
            self.after_cancel(self._sub_job)
            self._sub_job = None
        self._start_translate(text, target, live=False)

    def _apply_translation(self, out, err, target):
        self._tr_busy = False
        if err:
            self.tstatus.configure(text=err)
            self.sub_tr.configure(text="Translation unavailable")
            return
        self._tr_source = self.builder.text().strip()
        self._tr_lang = target
        self.tbox.delete("1.0", "end")
        self.tbox.insert("1.0", out or "")
        self.tstatus.configure(text=f"English → {target}")
        self.sub_tr.configure(text=out or "")
        tag = (target[:2] if target else "TR").upper()
        self.sub_lang_tag.configure(text=tag)

    def _on_lang_chosen(self, value):
        self.store.update_settings(translate_lang=value)
        self._tr_lang = ""
        self._sync_en_sub()
        self._schedule_live_translate()

    def _speak_translation(self):
        text = self.tbox.get("1.0", "end").strip() or self.builder.text().strip()
        speak(text, rate=int(self.store.settings.get("tts_rate", 160)))

    def stop(self):
        self.running = False
        self._stop_evt.set()
        if self._sub_job is not None:
            self.after_cancel(self._sub_job)
            self._sub_job = None
        if self._frame_job is not None:
            self.after_cancel(self._frame_job)
            self._frame_job = None
        if self._worker is not None:
            self._worker.join(timeout=1.5)
            self._worker = None


class MainShell(ctk.CTkFrame):
    def __init__(self, master, store, on_logout):
        super().__init__(master, fg_color=COLORS["bg"])
        self.store = store
        self.on_logout = on_logout
        self.page = None
        self.page_id = None
        self.nav_btns = {}
        self._usage_job = None

        top = ctk.CTkFrame(self, fg_color=COLORS["surface"], height=62, corner_radius=0)
        top.pack(fill="x")
        top.pack_propagate(False)
        ctk.CTkLabel(top, text=f"👐  {APP_NAME}", font=("Arial", 20, "bold"),
                     text_color=COLORS["text"]).pack(side="left", padx=18)

        who = store.profile.get("name") or store.username
        ctk.CTkLabel(top, text=who, font=("Arial", 13),
                     text_color=COLORS["muted"]).pack(side="left", padx=(0, 10))

        self.live_dot = ctk.CTkLabel(top, text="●  Online", font=("Arial", 13),
                                     text_color=COLORS["ok"])
        self.live_dot.pack(side="left", padx=(4, 12))

        ctk.CTkButton(top, text="Logout", width=88, height=34, corner_radius=8,
                      fg_color=COLORS["surface_2"], hover_color=COLORS["danger"],
                      command=self._logout).pack(side="right", padx=16)

        nav = ctk.CTkFrame(top, fg_color="transparent")
        nav.pack(side="right", padx=8)
        for pid, label in NAV:
            btn = ctk.CTkButton(nav, text=label, width=92, height=32, corner_radius=8,
                                fg_color="transparent", hover_color=COLORS["surface_2"],
                                command=lambda p=pid: self.show(p))
            btn.pack(side="left", padx=2)
            self.nav_btns[pid] = btn

        self.body = ctk.CTkFrame(self, fg_color=COLORS["bg"])
        self.body.pack(fill="both", expand=True)

        self.show("home")
        self._tick_usage()

    def show(self, page_id: str):
        self._teardown()
        self.page_id = page_id
        for pid, btn in self.nav_btns.items():
            if pid == page_id:
                btn.configure(fg_color=COLORS["primary"])
            else:
                btn.configure(fg_color="transparent")

        if page_id == "home":
            self.page = DetectScreen(self.body, self.store)
            self.live_dot.configure(text="●  Live", text_color=COLORS["accent"])
        elif page_id == "dash":
            self.page = DashboardPage(self.body, self.store)
            self.live_dot.configure(text="●  Online", text_color=COLORS["ok"])
        elif page_id == "profile":
            self.page = ProfilePage(self.body, self.store)
            self.live_dot.configure(text="●  Online", text_color=COLORS["ok"])
        elif page_id == "practice":
            self.page = PracticePage(self.body, self.store)
            self.live_dot.configure(text="●  Practice", text_color=COLORS["info"])
        elif page_id == "translate":
            self.page = TranslatorPage(self.body, self.store)
            self.live_dot.configure(text="●  Online", text_color=COLORS["ok"])
        elif page_id == "about":
            self.page = AboutPage(self.body,
                                  on_translate=lambda: self.show("translate"),
                                  on_home=lambda: self.show("home"))
            self.live_dot.configure(text="●  Online", text_color=COLORS["ok"])
        else:
            self.page = SettingsPage(self.body, self.store)
            self.live_dot.configure(text="●  Online", text_color=COLORS["ok"])

        self.page.pack(fill="both", expand=True)

    def _teardown(self):
        if self.page is None:
            return
        if hasattr(self.page, "stop"):
            self.page.stop()
        self.page.destroy()
        self.page = None

    def _tick_usage(self):
        self.store.add_usage_seconds(15)
        self._usage_job = self.after(15_000, self._tick_usage)

    def _logout(self):
        if self._usage_job is not None:
            self.after_cancel(self._usage_job)
            self._usage_job = None
        self._teardown()
        self.on_logout()

    def stop(self):
        if self._usage_job is not None:
            self.after_cancel(self._usage_job)
            self._usage_job = None
        self._teardown()


class SignifyApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title(APP_NAME)
        self.configure(fg_color=COLORS["bg"])
        self._fit_to_screen()
        self.auth = LocalAuth()
        self.store = None
        self.current = None
        self.show_login()
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _fit_to_screen(self):
        """Laptop / high-DPI Windows: don't demand a 1280×780 window."""
        self.update_idletasks()
        sw = max(self.winfo_screenwidth(), 800)
        sh = max(self.winfo_screenheight(), 600)
        w = min(1280, max(880, sw - 64))
        h = min(780, max(560, sh - 96))
        self.geometry(f"{w}x{h}")
        self.minsize(min(820, sw - 48), min(520, sh - 72))

    def _swap(self, frame):
        if self.current is not None:
            if hasattr(self.current, "stop"):
                self.current.stop()
            self.current.destroy()
        self.current = frame
        self.current.pack(fill="both", expand=True)

    def show_login(self):
        self.store = None
        self._swap(AuthScreen(self, self.auth, on_success=self.show_shell))

    def show_shell(self, username: str):
        self.store = AppStore(username)
        self._swap(MainShell(self, self.store, on_logout=self.show_login))

    def _on_close(self):
        if hasattr(self.current, "stop"):
            self.current.stop()
        self.destroy()


def main():
    if sys.platform == "win32":
        try:
            from ctypes import windll
            windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            pass
    SignifyApp().mainloop()


if __name__ == "__main__":
    main()
