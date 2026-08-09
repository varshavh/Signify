"""
Signify — desktop sign-language recognition app (CustomTkinter).

Screens:
  * LoginScreen     — fixed admin credentials, no database
  * DetectScreen    — live webcam recognition + sentence building

Run:  python -m signify.app     (from the repo root)
"""

import threading
import time
from datetime import datetime
from pathlib import Path

import cv2
import customtkinter as ctk
from PIL import Image

from .config import (APP_NAME, APP_TAGLINE, COLORS, NUM_HANDS,
                     STABILITY_FRAMES, MIN_CONFIDENCE, check_credentials)
from .recognizer import SignRecognizer
from .sentence_builder import SentenceBuilder, display_name, is_letter

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")

HISTORY_FILE = Path(__file__).resolve().parent.parent / "saved_sentences.txt"


# ---------------------------------------------------------------------------
class LoginScreen(ctk.CTkFrame):
    def __init__(self, master, on_success):
        super().__init__(master, fg_color=COLORS["bg"])
        self.on_success = on_success

        # Centered card
        card = ctk.CTkFrame(self, fg_color=COLORS["surface"], corner_radius=20,
                            width=420, height=460)
        card.place(relx=0.5, rely=0.5, anchor="center")
        card.pack_propagate(False)

        ctk.CTkLabel(card, text="👐", font=("Arial", 56)).pack(pady=(38, 4))
        ctk.CTkLabel(card, text=APP_NAME, font=("Arial", 34, "bold"),
                     text_color=COLORS["text"]).pack()
        ctk.CTkLabel(card, text=APP_TAGLINE, font=("Arial", 13),
                     text_color=COLORS["muted"]).pack(pady=(0, 24))

        self.user = ctk.CTkEntry(card, placeholder_text="Username", width=300,
                                 height=44, corner_radius=10)
        self.user.pack(pady=8)
        self.pw = ctk.CTkEntry(card, placeholder_text="Password", show="•",
                               width=300, height=44, corner_radius=10)
        self.pw.pack(pady=8)
        self.pw.bind("<Return>", lambda e: self._try_login())

        self.msg = ctk.CTkLabel(card, text="", font=("Arial", 12),
                                text_color=COLORS["danger"])
        self.msg.pack(pady=(6, 0))

        ctk.CTkButton(card, text="Sign In", width=300, height=46, corner_radius=10,
                      font=("Arial", 15, "bold"), fg_color=COLORS["primary"],
                      hover_color=COLORS["primary_h"],
                      command=self._try_login).pack(pady=(10, 6))

        ctk.CTkLabel(card, text="demo:  admin  /  admin123", font=("Arial", 11),
                     text_color=COLORS["muted"]).pack()

    def _try_login(self):
        if check_credentials(self.user.get().strip(), self.pw.get()):
            self.on_success()
        else:
            self.msg.configure(text="Invalid credentials. Try admin / admin123")
            self.pw.delete(0, "end")


# ---------------------------------------------------------------------------
class DetectScreen(ctk.CTkFrame):
    def __init__(self, master, on_logout):
        super().__init__(master, fg_color=COLORS["bg"])
        self.on_logout = on_logout

        self.recognizer = SignRecognizer(num_hands=NUM_HANDS)
        self.builder = SentenceBuilder(stability=STABILITY_FRAMES,
                                       min_confidence=MIN_CONFIDENCE)
        self.cap = None
        self.running = False
        self.current_pred = ("—", 0.0)

        self._build_ui()
        self.start_camera()

    # ---- layout ----------------------------------------------------------
    def _build_ui(self):
        # Top bar
        top = ctk.CTkFrame(self, fg_color=COLORS["surface"], height=64, corner_radius=0)
        top.pack(fill="x")
        top.pack_propagate(False)
        ctk.CTkLabel(top, text=f"👐  {APP_NAME}", font=("Arial", 22, "bold"),
                     text_color=COLORS["text"]).pack(side="left", padx=20)
        self.status_dot = ctk.CTkLabel(top, text="● live", font=("Arial", 13),
                                       text_color=COLORS["accent"])
        self.status_dot.pack(side="left")
        ctk.CTkButton(top, text="Logout", width=90, height=36, corner_radius=8,
                      fg_color=COLORS["surface_2"], hover_color=COLORS["danger"],
                      command=self._logout).pack(side="right", padx=20)

        body = ctk.CTkFrame(self, fg_color=COLORS["bg"])
        body.pack(fill="both", expand=True, padx=16, pady=16)

        # Left: video
        left = ctk.CTkFrame(body, fg_color=COLORS["surface"], corner_radius=16)
        left.pack(side="left", fill="both", expand=True, padx=(0, 10))
        self.video_label = ctk.CTkLabel(left, text="Starting camera…",
                                        text_color=COLORS["muted"])
        self.video_label.pack(fill="both", expand=True, padx=12, pady=12)

        # Prediction pill under video
        self.pred_label = ctk.CTkLabel(left, text="Detecting…", font=("Arial", 20, "bold"),
                                       text_color=COLORS["accent"])
        self.pred_label.pack(pady=(0, 12))

        # Right: sentence panel
        right = ctk.CTkFrame(body, fg_color=COLORS["surface"], corner_radius=16, width=380)
        right.pack(side="right", fill="y")
        right.pack_propagate(False)

        ctk.CTkLabel(right, text="Sentence", font=("Arial", 16, "bold"),
                     text_color=COLORS["text"]).pack(anchor="w", padx=18, pady=(18, 6))

        self.sentence_box = ctk.CTkTextbox(right, height=160, corner_radius=12,
                                           font=("Arial", 18), fg_color=COLORS["surface_2"],
                                           text_color=COLORS["text"], wrap="word")
        self.sentence_box.pack(fill="x", padx=18)
        self.sentence_box.insert("1.0", "")
        self.sentence_box.configure(state="disabled")

        ctk.CTkLabel(right, text="Letters spell into a word; pause or press "
                     "“End word” to finish it. Whole-word signs stand alone.",
                     font=("Arial", 11), text_color=COLORS["muted"],
                     wraplength=340, justify="left").pack(anchor="w", padx=18, pady=(6, 0))

        # Editing controls
        btns = ctk.CTkFrame(right, fg_color="transparent")
        btns.pack(fill="x", padx=18, pady=14)
        grid = [
            ("✓ End word", self._space, COLORS["surface_2"]),
            ("⌫ Backspace", self._backspace, COLORS["surface_2"]),
            ("🗑 Clear", self._clear, COLORS["surface_2"]),
            ("🔊 Speak", self._speak, COLORS["primary"]),
            ("📋 Copy", self._copy, COLORS["surface_2"]),
            ("💾 Save", self._save, COLORS["accent"]),
        ]
        for i, (txt, cmd, color) in enumerate(grid):
            ctk.CTkButton(btns, text=txt, command=cmd, corner_radius=10, height=40,
                          fg_color=color, hover_color=COLORS["primary_h"],
                          font=("Arial", 13)).grid(row=i // 2, column=i % 2,
                                                    padx=5, pady=5, sticky="ew")
        btns.grid_columnconfigure((0, 1), weight=1)

        # Pause / resume detection
        self.pause_btn = ctk.CTkButton(right, text="⏸ Pause detection",
                                       command=self._toggle_pause, corner_radius=10,
                                       height=42, fg_color=COLORS["surface_2"],
                                       font=("Arial", 13))
        self.pause_btn.pack(fill="x", padx=18, pady=(0, 8))

        # Settings: confidence + stability sliders
        ctk.CTkLabel(right, text="Sensitivity", font=("Arial", 13),
                     text_color=COLORS["muted"]).pack(anchor="w", padx=18, pady=(6, 0))
        self.conf_slider = ctk.CTkSlider(right, from_=0.2, to=0.9, number_of_steps=14,
                                         command=self._set_conf)
        self.conf_slider.set(MIN_CONFIDENCE)
        self.conf_slider.pack(fill="x", padx=18, pady=(0, 4))
        self.conf_val = ctk.CTkLabel(right, text=f"min confidence: {MIN_CONFIDENCE:.2f}",
                                     font=("Arial", 11), text_color=COLORS["muted"])
        self.conf_val.pack(anchor="w", padx=18)

        # History log
        ctk.CTkLabel(right, text="Committed words", font=("Arial", 13),
                     text_color=COLORS["muted"]).pack(anchor="w", padx=18, pady=(12, 2))
        self.log_box = ctk.CTkTextbox(right, height=90, corner_radius=12,
                                      font=("Arial", 12), fg_color=COLORS["surface_2"],
                                      text_color=COLORS["muted"])
        self.log_box.pack(fill="both", expand=True, padx=18, pady=(0, 18))
        self.log_box.configure(state="disabled")

    # ---- camera loop -----------------------------------------------------
    def start_camera(self):
        self.cap = cv2.VideoCapture(0)
        if not self.cap.isOpened():
            self.video_label.configure(text="⚠ Could not open webcam")
            return
        self.running = True
        self._update_frame()

    def _update_frame(self):
        if not self.running or self.cap is None:
            return
        ok, frame = self.cap.read()
        if ok:
            frame = cv2.flip(frame, 1)
            annotated, preds = self.recognizer.process(frame)

            label, score = (preds[0] if preds else (None, 0.0))
            if label and label != "none":
                self.current_pred = (label, score)
                shown = display_name(label)
                # hint that a letter is being spelled vs a whole word
                kind = "letter" if is_letter(label) else "word"
                self.pred_label.configure(text=f"{shown}   {score:.0%}   ·  {kind}")
            else:
                self.pred_label.configure(text="Detecting…")

            committed = self.builder.update(label, score)
            if committed:
                self._refresh_sentence()
                self._append_log(committed)

            # render frame to the label
            rgb = cv2.cvtColor(annotated, cv2.COLOR_BGR2RGB)
            img = Image.fromarray(rgb)
            # fit while keeping aspect
            lw = max(self.video_label.winfo_width(), 640)
            lh = max(self.video_label.winfo_height(), 480)
            img.thumbnail((lw, lh))
            ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=img.size)
            self.video_label.configure(image=ctk_img, text="")
            self.video_label.image = ctk_img

        self.after(15, self._update_frame)

    # ---- actions ---------------------------------------------------------
    def _refresh_sentence(self):
        self.sentence_box.configure(state="normal")
        self.sentence_box.delete("1.0", "end")
        self.sentence_box.insert("1.0", self.builder.text())
        self.sentence_box.configure(state="disabled")

    def _append_log(self, word):
        self.log_box.configure(state="normal")
        self.log_box.insert("end", f"{datetime.now():%H:%M:%S}  {word}\n")
        self.log_box.see("end")
        self.log_box.configure(state="disabled")

    def _space(self):
        self.builder.add_space(); self._refresh_sentence()

    def _backspace(self):
        self.builder.backspace(); self._refresh_sentence()

    def _clear(self):
        self.builder.clear(); self._refresh_sentence()

    def _copy(self):
        text = self.builder.text()
        self.clipboard_clear(); self.clipboard_append(text)
        self.status_dot.configure(text="● copied")
        self.after(1200, lambda: self.status_dot.configure(text="● live"))

    def _save(self):
        text = self.builder.text().strip()
        if not text:
            return
        with open(HISTORY_FILE, "a") as f:
            f.write(f"{datetime.now():%Y-%m-%d %H:%M:%S}\t{text}\n")
        self.status_dot.configure(text="● saved")
        self.after(1200, lambda: self.status_dot.configure(text="● live"))

    def _speak(self):
        text = self.builder.text().strip()
        if not text:
            return
        threading.Thread(target=self._speak_worker, args=(text,), daemon=True).start()

    def _speak_worker(self, text):
        try:
            import pyttsx3
            engine = pyttsx3.init()
            engine.setProperty("rate", 160)
            engine.say(text)
            engine.runAndWait()
            engine.stop()
        except Exception as e:
            print("[speak] error:", e)

    def _toggle_pause(self):
        self.running = not self.running
        if self.running:
            self.pause_btn.configure(text="⏸ Pause detection")
            self.status_dot.configure(text="● live", text_color=COLORS["accent"])
            self._update_frame()
        else:
            self.pause_btn.configure(text="▶ Resume detection")
            self.status_dot.configure(text="● paused", text_color=COLORS["muted"])

    def _set_conf(self, val):
        self.builder.min_confidence = float(val)
        self.conf_val.configure(text=f"min confidence: {float(val):.2f}")

    def _logout(self):
        self.stop()
        self.on_logout()

    def stop(self):
        self.running = False
        if self.cap is not None:
            self.cap.release()
            self.cap = None
        self.recognizer.close()


# ---------------------------------------------------------------------------
class SignifyApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title(APP_NAME)
        self.geometry("1180x720")
        self.minsize(1000, 640)
        self.configure(fg_color=COLORS["bg"])
        self.current = None
        self.show_login()
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _swap(self, frame):
        if self.current is not None:
            if isinstance(self.current, DetectScreen):
                self.current.stop()
            self.current.destroy()
        self.current = frame
        self.current.pack(fill="both", expand=True)

    def show_login(self):
        self._swap(LoginScreen(self, on_success=self.show_detect))

    def show_detect(self):
        self._swap(DetectScreen(self, on_logout=self.show_login))

    def _on_close(self):
        if isinstance(self.current, DetectScreen):
            self.current.stop()
        self.destroy()


def main():
    SignifyApp().mainloop()


if __name__ == "__main__":
    main()
