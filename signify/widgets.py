"""UI pieces that do not use CustomTkinter's grab-based dropdown menus.

CTkComboBox / CTkOptionMenu open a Toplevel with grab_set(), which freezes
the rest of the app (especially while a camera loop is running). These
widgets stay inside the normal layout so clicks keep working.
"""

import customtkinter as ctk

from .config import AUTH_FIELD_HEIGHT, COLORS


class LanguagePicker(ctk.CTkFrame):
    """Expand-in-place language list. Same .get() / .set() as a combo box."""

    def __init__(self, master, values, value=None, command=None, width=220, **kwargs):
        kwargs.setdefault("fg_color", "transparent")
        super().__init__(master, **kwargs)
        self._values = list(values)
        self._command = command
        self._open = False
        start = value if value in self._values else (self._values[0] if self._values else "")
        self._value = start

        self._btn = ctk.CTkButton(
            self, text=f"{start}   ▾", width=width, height=34, anchor="w",
            fg_color=COLORS["surface_2"], hover_color=COLORS["primary"],
            command=self.toggle,
        )
        self._btn.pack(fill="x")

        self._panel = ctk.CTkFrame(self, fg_color=COLORS["surface_2"], corner_radius=10)
        for i, name in enumerate(self._values):
            r, c = divmod(i, 2)
            b = ctk.CTkButton(
                self._panel, text=name, height=30, width=100,
                fg_color="transparent", hover_color=COLORS["primary"],
                command=lambda n=name: self._pick(n),
            )
            b.grid(row=r, column=c, padx=4, pady=3, sticky="ew")
        self._panel.grid_columnconfigure((0, 1), weight=1)

    def toggle(self):
        if self._open:
            self._panel.pack_forget()
            self._btn.configure(text=f"{self._value}   ▾")
            self._open = False
        else:
            self._panel.pack(fill="x", pady=(6, 0))
            self._btn.configure(text=f"{self._value}   ▴")
            self._open = True

    def _pick(self, name):
        self.set(name)
        if self._open:
            self.toggle()
        if self._command:
            self._command(name)

    def get(self):
        return self._value

    def set(self, name):
        if name in self._values:
            self._value = name
            arrow = "▴" if self._open else "▾"
            self._btn.configure(text=f"{name}   {arrow}")


class PasswordEntry(ctk.CTkFrame):
    """Password field with an in-box eye toggle on the right."""

    def __init__(self, master, placeholder="Password", width=320, height=AUTH_FIELD_HEIGHT, **kwargs):
        placeholder = kwargs.pop("placeholder_text", placeholder)
        kwargs.setdefault("fg_color", "transparent")
        super().__init__(master, width=width, height=height, **kwargs)
        self.pack_propagate(False)
        self._hidden = True
        self._eye_w = 36

        self.entry = ctk.CTkEntry(
            self, placeholder_text=placeholder, show="•",
            width=width, height=height,
        )
        self.entry.place(x=0, y=0)

        # Overlay inside the entry (right edge). Entry is full width so the box looks uniform.
        self._btn = ctk.CTkButton(
            self, text="👁", width=self._eye_w, height=height - 10, corner_radius=6,
            fg_color="transparent", hover_color=COLORS["surface_2"],
            text_color=COLORS["muted"], border_width=0,
            font=("Arial", 15), command=self.toggle,
        )
        self._btn.place(x=width - self._eye_w - 8, y=5)
        self._btn.lift()

    def toggle(self):
        self._hidden = not self._hidden
        self.entry.configure(show="•" if self._hidden else "")
        self._btn.configure(text="👁" if self._hidden else "🙈")

    def get(self):
        return self.entry.get()

    def delete(self, first, last=None):
        self.entry.delete(first, last if last is not None else "end")

    def bind(self, sequence, func, add=True):
        return self.entry.bind(sequence, func, add=True)
