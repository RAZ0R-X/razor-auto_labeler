"""Capture application screenshots for GitHub documentation."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs" / "screenshots"

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _demo_images() -> list[Path]:
    from PIL import Image, ImageDraw

    demo_dir = ROOT / "docs" / "demo_images"
    demo_dir.mkdir(parents=True, exist_ok=True)
    names = [
        ("street_001.jpg", (45, 120, 200)),
        ("street_002.jpg", (60, 90, 160)),
        ("street_003.jpg", (80, 140, 90)),
        ("street_004.jpg", (200, 80, 60)),
        ("street_005.jpg", (30, 60, 110)),
    ]
    paths: list[Path] = []
    for name, color in names:
        path = demo_dir / name
        if not path.exists():
            img = Image.new("RGB", (640, 480), color)
            draw = ImageDraw.Draw(img)
            draw.rectangle([120, 100, 280, 380], outline=(229, 9, 20), width=4)
            draw.rectangle([340, 160, 520, 320], outline=(229, 9, 20), width=4)
            img.save(path, quality=90)
        paths.append(path)
    return paths


def main() -> int:
    from PyQt6.QtCore import QTimer, Qt
    from PyQt6.QtWidgets import QApplication

    from src.class_config import ClassMapping, build_mappings_from_model
    from src.main_window import MainWindow, _load_app_icon
    from src.splash import SplashScreen
    from src.theme import APP_STYLESHEET

    DOCS.mkdir(parents=True, exist_ok=True)

    app = QApplication(sys.argv)
    app.setApplicationName("RAZOR-Auto Labeler")
    app.setWindowIcon(_load_app_icon())
    app.setStyle("Fusion")
    app.setStyleSheet(APP_STYLESHEET)

    splash = SplashScreen()
    splash.setWindowOpacity(1.0)
    splash.show()
    app.processEvents()
    splash.grab().save(str(DOCS / "splash.png"), "PNG")
    splash.close()

    window = MainWindow()
    demo_paths = _demo_images()

    try:
        from ultralytics import YOLO

        model_path = ROOT / "docs" / "yolov8n.pt"
        if not model_path.exists():
            YOLO("yolov8n.pt").save(str(model_path.parent / "yolov8n.pt"))
        class_names = window.model_manager.load(model_path)
        window.class_mappings = build_mappings_from_model(class_names)
        window._set_model_loaded_style("yolov8n.pt")
        window.class_mappings = [
            ClassMapping(0, "person", "person", True),
            ClassMapping(2, "car", "vehicle", True),
            ClassMapping(5, "bus", "vehicle", True),
            ClassMapping(7, "truck", "vehicle", True),
        ]
    except Exception:
        window.model_label.setText("● Model: yolov8n.pt")
        window.model_label.setObjectName("statusOk")
        window.class_mappings = [
            ClassMapping(0, "person", "person", True),
            ClassMapping(2, "car", "vehicle", True),
            ClassMapping(5, "bus", "vehicle", True),
        ]
        window.configure_classes_btn.setEnabled(True)

    window._add_images([str(p) for p in demo_paths])
    window._log("Model loaded: yolov8n.pt")
    window._log("Export classes: person, vehicle")
    window._log("5 image(s) added.")
    window._refresh_class_list()
    window._update_run_state()
    window.progress.setValue(100)
    window.progress.setFormat("Completed — 5 / 5 images")
    window.show()
    app.processEvents()

    window.grab().save(str(DOCS / "main_window.png"), "PNG")

    from src.class_selector import ClassSelectorDialog

    all_mappings = sorted(window.class_mappings, key=lambda m: m.model_class_id)
    dialog = ClassSelectorDialog(all_mappings, parent=window)
    dialog.show()
    app.processEvents()
    dialog.grab().save(str(DOCS / "class_selector.png"), "PNG")
    dialog.close()

    print(f"Screenshots saved to {DOCS}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
