"""UI pieces that do not use CustomTkinter's grab-based dropdown menus.

CTkComboBox / CTkOptionMenu open a Toplevel with grab_set(), which freezes
the rest of the app (especially while a camera loop is running). These
widgets stay inside the normal layout so clicks keep working.
"""

import customtkinter as ctk

from .config import AUTH_FIELD_HEIGHT, COLORS
from .emoji_img import emoji_ctk

# Match default CTkEntry colors so the password shell looks like other fields.
_ENTRY_FG = ("#F9F9FA", "#343638")
_ENTRY_BORDER = ("#979DA2", "#565B5E")


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
    """Password field with a centered in-box eye toggle."""

    _ICON_TILE = 28
    _ICON_SLOT = 40

    def __init__(self, master, placeholder="Password", width=320, height=AUTH_FIELD_HEIGHT, **kwargs):
        placeholder = kwargs.pop("placeholder_text", placeholder)
        kwargs.setdefault("fg_color", "transparent")
        super().__init__(master, width=width, height=height, **kwargs)
        self.pack_propagate(False)
        self._hidden = True
        self._img_show = emoji_ctk("👁", 17, self._ICON_TILE)
        self._img_hide = emoji_ctk("🙈", 17, self._ICON_TILE)

        self._shell = ctk.CTkFrame(
            self, width=width, height=height, corner_radius=10,
            fg_color=_ENTRY_FG, border_width=2, border_color=_ENTRY_BORDER,
        )
        self._shell.place(relx=0.5, rely=0.5, anchor="center")
        self._shell.pack_propagate(False)

        text_w = width - self._ICON_SLOT - 6
        self.entry = ctk.CTkEntry(
            self._shell, placeholder_text=placeholder, show="•",
            width=text_w, height=height - 8,
            border_width=0, fg_color="transparent",
        )
        self.entry.place(relx=0, rely=0.5, anchor="w", x=10)

        self._btn = ctk.CTkButton(
            self._shell, text="", width=self._ICON_SLOT, height=height - 8,
            corner_radius=8, fg_color="transparent",
            hover_color=("#E5E5E5", "#3E4042"),
            image=self._img_show, command=self.toggle,
        )
        self._btn.place(relx=1.0, rely=0.5, anchor="e", x=-2)

    def toggle(self):
        self._hidden = not self._hidden
        self.entry.configure(show="•" if self._hidden else "")
        self._btn.configure(image=self._img_show if self._hidden else self._img_hide)

    def get(self):
        return self.entry.get()

    def delete(self, first, last=None):
        self.entry.delete(first, last if last is not None else "end")

    def bind(self, sequence, func, add=True):
        return self.entry.bind(sequence, func, add=True)
