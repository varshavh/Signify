"""
Build a combined training dataset for the extended Signify model.

Combines:
  1. The existing 42-class dataset (sign_language_dataset/) — copied as-is.
  2. Seven word-signs from the Roboflow YOLOv8 "Signify AI" dataset, CROPPED to
     their bounding boxes so only the signing hand region is kept.

Output: combined_dataset/<ClassName>/*.jpg  (49 classes total)

The YOLO dataset path is configurable below. Run once before training.
"""

import shutil
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
EXISTING = HERE / "sign_language_dataset"
OUT = HERE / "combined_dataset"

# Roboflow YOLOv8 dataset root (already unzipped in the signify_ai project).
YOLO_ROOT = Path("/Users/varshit.hegde/my_own/signify_ai/dataset/signify")

# YOLO class-id -> output folder name (kept close to app naming conventions).
NEW_CLASSES = {
    1:  "Father",
    2:  "Fine",
    3:  "Friend",
    6:  "Help",
    14: "MyNameIs",
    22: "Who",
    24: "You",
}


def yolo_box_to_pixels(xc, yc, bw, bh, W, H):
    x1 = int((xc - bw / 2) * W); y1 = int((yc - bh / 2) * H)
    x2 = int((xc + bw / 2) * W); y2 = int((yc + bh / 2) * H)
    return max(0, x1), max(0, y1), min(W, x2), min(H, y2)


def copy_existing():
    print("[1/2] copying existing 42 classes...")
    n = 0
    for cls_dir in sorted(EXISTING.iterdir()):
        if not cls_dir.is_dir():
            continue
        dst = OUT / cls_dir.name
        dst.mkdir(parents=True, exist_ok=True)
        for img in cls_dir.glob("*.jpg"):
            shutil.copy2(img, dst / img.name)
            n += 1
    print(f"      copied {n} images across existing classes")


def crop_new_classes():
    print("[2/2] cropping 7 word-classes from the YOLO dataset...")
    for cid, name in NEW_CLASSES.items():
        dst = OUT / name
        dst.mkdir(parents=True, exist_ok=True)
        count = 0
        for split in ("train", "valid", "test"):
            labels_dir = YOLO_ROOT / split / "labels"
            images_dir = YOLO_ROOT / split / "images"
            if not labels_dir.exists():
                continue
            for lbl in labels_dir.glob("*.txt"):
                line = lbl.read_text().strip().splitlines()
                if not line:
                    continue
                parts = line[0].split()
                if len(parts) != 5 or int(parts[0]) != cid:
                    continue
                img_path = images_dir / (lbl.stem + ".jpg")
                if not img_path.exists():
                    continue
                im = Image.open(img_path)
                W, H = im.size
                _, xc, yc, bw, bh = (float(p) for p in parts)
                box = yolo_box_to_pixels(xc, yc, bw, bh, W, H)
                if box[2] <= box[0] or box[3] <= box[1]:
                    continue
                crop = im.crop(box)
                crop.save(dst / f"{name}_{split}_{count}.jpg")
                count += 1
        print(f"      {name:10s}: {count} cropped images")


def main():
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True)
    copy_existing()
    crop_new_classes()
    total_classes = len([d for d in OUT.iterdir() if d.is_dir()])
    total_images = sum(1 for _ in OUT.rglob("*.jpg"))
    print(f"\n[done] combined_dataset/: {total_classes} classes, {total_images} images")


if __name__ == "__main__":
    main()
