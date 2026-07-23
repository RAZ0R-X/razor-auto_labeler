"""Razor Auto Labeler entry point."""

import sys

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication

from src.main_window import MainWindow, _load_app_icon
from src.splash import SplashScreen
from src.theme import APP_STYLESHEET


def main() -> int:
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setApplicationName("RAZOR-Auto Labeler")
    app.setWindowIcon(_load_app_icon())
    app.setStyle("Fusion")
    app.setStyleSheet(APP_STYLESHEET)

    splash = SplashScreen()
    window = MainWindow()

    def show_main() -> None:
        screen = app.primaryScreen()
        if screen is not None:
            geo = screen.availableGeometry()
            window.move(
                geo.x() + (geo.width() - window.width()) // 2,
                geo.y() + (geo.height() - window.height()) // 2,
            )
        window.show()
        splash.close()

    splash.finished.connect(show_main)
    splash.start()

    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
