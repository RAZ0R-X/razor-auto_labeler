"""Generate logo.ico from logo.svg for Windows taskbar / title bar."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"


def main() -> int:
    from PyQt6.QtCore import Qt
    from PyQt6.QtGui import QImage, QPainter
    from PyQt6.QtSvg import QSvgRenderer
    from PyQt6.QtWidgets import QApplication

    app = QApplication(sys.argv)
    svg = ASSETS / "logo.svg"
    if not svg.exists():
        print(f"Missing {svg}")
        return 1

    sizes = (16, 32, 48, 64, 128, 256)
    png_paths: list[Path] = []
    for size in sizes:
        img = QImage(size, size, QImage.Format.Format_ARGB32)
        img.fill(Qt.GlobalColor.transparent)
        painter = QPainter(img)
        QSvgRenderer(str(svg)).render(painter)
        painter.end()
        out = ASSETS / f"logo_{size}.png"
        img.save(str(out))
        png_paths.append(out)

    try:
        from PIL import Image

        images = [Image.open(p) for p in png_paths]
        images[0].save(
            ASSETS / "logo.ico",
            format="ICO",
            sizes=[(s, s) for s in sizes],
            append_images=images[1:],
        )
        print(f"Created {ASSETS / 'logo.ico'}")
    except ImportError:
        print("Pillow not installed; PNG sizes created, ICO skipped.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
