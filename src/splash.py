"""Opening splash animation with RAZOR branding."""

from PyQt6.QtCore import QEasingCurve, QPropertyAnimation, QTimer, Qt, pyqtSignal
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import QApplication, QLabel, QVBoxLayout, QWidget

from src.theme import COLORS


class SplashScreen(QWidget):
    """Centered splash window with animated RAZOR text."""

    finished = pyqtSignal()

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("splashRoot")
        self.setFixedSize(680, 320)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setStyleSheet(
            f"""
            QWidget#splashRoot {{
                background-color: {COLORS['bg_dark']};
                border: none;
                border-radius: 20px;
            }}
            QLabel {{
                border: none;
                background: transparent;
            }}
            """
        )

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setContentsMargins(40, 40, 40, 40)

        self.logo = QLabel("RAZOR")
        self.logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.logo.setStyleSheet(
            f"""
            color: {COLORS['accent']};
            font-size: 68px;
            font-weight: 900;
            letter-spacing: 20px;
            border: none;
            background: transparent;
            padding: 0;
            margin: 0;
            """
        )
        font = QFont("Segoe UI", 68, QFont.Weight.Black)
        font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 20)
        self.logo.setFont(font)

        self.tagline = QLabel("AUTO LABELER")
        self.tagline.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.tagline.setStyleSheet(
            f"""
            color: {COLORS['text_muted']};
            font-size: 13px;
            letter-spacing: 10px;
            border: none;
            background: transparent;
            """
        )

        layout.addWidget(self.logo)
        layout.addSpacing(6)
        layout.addWidget(self.tagline)

        self._fade_in = QPropertyAnimation(self, b"windowOpacity")
        self._fade_in.setDuration(850)
        self._fade_in.setStartValue(0.0)
        self._fade_in.setEndValue(1.0)
        self._fade_in.setEasingCurve(QEasingCurve.Type.OutCubic)

        self._fade_out = QPropertyAnimation(self, b"windowOpacity")
        self._fade_out.setDuration(650)
        self._fade_out.setStartValue(1.0)
        self._fade_out.setEndValue(0.0)
        self._fade_out.setEasingCurve(QEasingCurve.Type.InCubic)
        self._fade_out.finished.connect(self._on_finished)

    def start(self) -> None:
        self.setWindowOpacity(0.0)
        screen = QApplication.primaryScreen()
        if screen is not None:
            geo = screen.availableGeometry()
            self.move(
                geo.x() + (geo.width() - self.width()) // 2,
                geo.y() + (geo.height() - self.height()) // 2,
            )
        self.show()
        self._fade_in.start()
        QTimer.singleShot(1700, self._begin_fade_out)

    def _begin_fade_out(self) -> None:
        self._fade_out.start()

    def _on_finished(self) -> None:
        self.hide()
        self.finished.emit()
