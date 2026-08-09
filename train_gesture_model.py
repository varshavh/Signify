"""
Train an extended gesture-recognition .task model with MediaPipe Model Maker.

Trains on combined_dataset/ (49 classes = the original 42 + 7 new word-signs
cropped from the YOLO dataset) and exports a NEW .task file, leaving the
original models/sign_language_recognizer.task untouched.

Run with the 3.10 training venv:
    .venv-train/bin/python train_gesture_model.py

Output:
    models/signify_extended.task
"""

from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA_DIR = HERE / "combined_dataset"
EXPORT_DIR = HERE / "models"
EXPORT_NAME = "signify_extended.task"


def main():
    from mediapipe_model_maker import gesture_recognizer

    print(f"[info] dataset: {DATA_DIR}")

    # Model Maker requires a 'none' class (no-gesture). Our dataset already has
    # a 'none' folder from the original set, so this is satisfied.
    data = gesture_recognizer.Dataset.from_folder(
        dirname=str(DATA_DIR),
        hparams=gesture_recognizer.HandDataPreprocessingParams(),
    )
    train_data, rest = data.split(0.8)
    val_data, test_data = rest.split(0.5)
    print(f"[info] size: train={train_data.size} val={val_data.size} test={test_data.size}")

    hparams = gesture_recognizer.HParams(
        export_dir=str(EXPORT_DIR),
        epochs=30,
        batch_size=16,
        learning_rate=0.001,
    )
    options = gesture_recognizer.GestureRecognizerOptions(hparams=hparams)

    print("[info] training...")
    model = gesture_recognizer.GestureRecognizer.create(
        train_data=train_data,
        validation_data=val_data,
        options=options,
    )

    loss, acc = model.evaluate(test_data)
    print(f"\n[result] test loss={loss:.4f}  test accuracy={acc:.4f}")

    model.export_model(model_name=EXPORT_NAME)
    print(f"[saved] {EXPORT_DIR / EXPORT_NAME}")


if __name__ == "__main__":
    main()
