"""Sign reference chart — sample training images and what each sign means."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PIL import Image

from .sentence_builder import display_name, is_letter

ROOT = Path(__file__).resolve().parent.parent
DATASET_DIRS = (
    ROOT / "sign_language_dataset",
    ROOT / "combined_dataset",
)

_IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}

# Short plain-English meaning for whole-word signs.
WORD_MEANINGS = {
    "Hello": "Greeting — say hello",
    "Bye": "Goodbye / see you later",
    "Yes": "Yes / agree",
    "No": "No / refuse",
    "Please": "Please (polite request)",
    "Thankyou": "Thank you",
    "Ok": "OK / all right",
    "NotOk": "Not OK / something is wrong",
    "Name": "Name",
    "Me": "Me / myself",
    "ILoveYou": "I love you",
    "Learn": "Learn / study",
    "Meet": "Meet / introduction",
    "Tell": "Tell / explain",
    "Pen": "Pen / write",
    "Deaf": "Deaf (community / identity)",
    "Please": "Please",
    "Father": "Father / dad",
    "Fine": "Fine / I'm fine",
    "Friend": "Friend",
    "Help": "Help",
    "MyNameIs": "My name is…",
    "Who": "Who?",
    "You": "You",
    "GoodMorning": "Good morning",
}


@dataclass(frozen=True)
class SignChartEntry:
    label: str
    title: str
    meaning: str
    kind: str
    image_path: Path


def _pick_image(folder: Path) -> Path | None:
    if not folder.is_dir():
        return None
    files = sorted(
        p for p in folder.iterdir()
        if p.is_file() and p.suffix.lower() in _IMAGE_EXTS
    )
    return files[0] if files else None


def _meaning(label: str) -> str:
    if is_letter(label):
        return f"Fingerspell the letter {label}"
    return WORD_MEANINGS.get(label, f"ASL word sign: {display_name(label)}")


def load_sign_chart_entries() -> list[SignChartEntry]:
    """One sample image per class from training folders (42-class + extras)."""
    found: dict[str, Path] = {}
    for root in DATASET_DIRS:
        if not root.is_dir():
            continue
        for folder in sorted(root.iterdir()):
            if not folder.is_dir():
                continue
            label = folder.name
            if label == "none":
                continue
            if label in found:
                continue
            img = _pick_image(folder)
            if img is not None:
                found[label] = img

    entries: list[SignChartEntry] = []
    for label in sorted(found, key=_sort_key):
        entries.append(SignChartEntry(
            label=label,
            title=display_name(label),
            meaning=_meaning(label),
            kind="Letter" if is_letter(label) else "Word",
            image_path=found[label],
        ))
    return entries


def _sort_key(label: str):
    if is_letter(label):
        return (0, label)
    return (1, label.lower())


def load_thumbnail(path: Path, size: tuple[int, int] = (200, 150)) -> Image.Image:
    img = Image.open(path).convert("RGB")
    img.thumbnail(size, Image.Resampling.LANCZOS)
    return img
