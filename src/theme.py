"""Razor black/red theme constants and stylesheets."""

COLORS = {
    "bg_dark": "#080808",
    "bg_panel": "#111111",
    "bg_card": "#181818",
    "bg_elevated": "#1f1f1f",
    "border": "#2d2d2d",
    "border_soft": "#222222",
    "text": "#f5f5f5",
    "text_muted": "#9a9a9a",
    "accent": "#e50914",
    "accent_hover": "#ff2430",
    "accent_dark": "#b0070f",
    "accent_soft": "#3a1014",
    "success": "#22c55e",
    "success_glow": "#4ade80",
    "success_soft": "#0f2a1a",
    "warning": "#f59e0b",
}

APP_STYLESHEET = f"""
QWidget {{
    background-color: {COLORS["bg_dark"]};
    color: {COLORS["text"]};
    font-family: "Segoe UI", "Inter", sans-serif;
    font-size: 13px;
}}

QLabel#ownerLabel {{
    font-size: 11px;
    font-weight: 500;
    letter-spacing: 0.4px;
    padding-left: 2px;
}}

QMainWindow {{
    background-color: {COLORS["bg_dark"]};
}}

QLabel#titleLabel {{
    font-size: 22px;
    font-weight: 800;
    color: {COLORS["text"]};
    letter-spacing: 1px;
}}

QLabel#subtitleLabel {{
    font-size: 11px;
    color: {COLORS["text_muted"]};
    letter-spacing: 3px;
    margin-top: 2px;
}}

QLabel#sectionLabel {{
    font-size: 10px;
    font-weight: 700;
    color: {COLORS["text_muted"]};
    letter-spacing: 1.5px;
}}

QLabel#statusOk {{
    color: {COLORS["success_glow"]};
    font-weight: 600;
    font-size: 13px;
}}

QFrame#panel {{
    background-color: {COLORS["bg_panel"]};
    border: 1px solid {COLORS["border_soft"]};
    border-radius: 14px;
}}

QFrame#accentPanel {{
    background-color: {COLORS["bg_panel"]};
    border: 1px solid {COLORS["border_soft"]};
    border-top: 2px solid {COLORS["accent"]};
    border-radius: 14px;
}}

QPushButton {{
    background-color: {COLORS["bg_elevated"]};
    color: {COLORS["text"]};
    border: 1px solid {COLORS["border"]};
    border-radius: 10px;
    padding: 11px 20px;
    font-weight: 600;
    min-height: 18px;
}}

QPushButton:hover {{
    background-color: {COLORS["bg_card"]};
    border-color: {COLORS["accent"]};
    color: {COLORS["accent"]};
}}

QPushButton:pressed {{
    background-color: {COLORS["accent_soft"]};
}}

QPushButton#primaryButton {{
    background-color: {COLORS["accent"]};
    color: white;
    border: none;
    padding: 12px 24px;
}}

QPushButton#primaryButton:hover {{
    background-color: {COLORS["accent_hover"]};
    color: white;
}}

QPushButton#primaryButton:disabled {{
    background-color: #2a2a2a;
    color: #666666;
    border: 1px solid {COLORS["border"]};
}}

QPushButton#ghostButton {{
    background-color: transparent;
    border: 1px solid {COLORS["border"]};
    color: {COLORS["text_muted"]};
}}

QPushButton#ghostButton:hover {{
    border-color: {COLORS["text_muted"]};
    color: {COLORS["text"]};
}}

QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox {{
    background-color: {COLORS["bg_card"]};
    color: {COLORS["text"]};
    border: 1px solid {COLORS["border"]};
    border-radius: 8px;
    padding: 9px 12px;
    selection-background-color: {COLORS["accent"]};
}}

QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus {{
    border-color: {COLORS["accent"]};
}}

QComboBox::drop-down {{
    border: none;
    width: 28px;
}}

QComboBox QAbstractItemView {{
    background-color: {COLORS["bg_elevated"]};
    color: {COLORS["text"]};
    selection-background-color: {COLORS["accent"]};
    border: 1px solid {COLORS["border"]};
    border-radius: 8px;
    padding: 4px;
}}

QListWidget {{
    background-color: {COLORS["bg_card"]};
    border: none;
    border-radius: 10px;
    padding: 6px;
    outline: none;
}}

QListWidget::item {{
    padding: 10px 12px;
    border-radius: 8px;
    margin: 2px 0;
    color: {COLORS["text_muted"]};
}}

QListWidget::item:hover {{
    background-color: {COLORS["bg_elevated"]};
    color: {COLORS["text"]};
}}

QListWidget::item:selected {{
    background-color: {COLORS["accent_soft"]};
    color: {COLORS["accent"]};
    border: 1px solid {COLORS["accent"]};
}}

QProgressBar {{
    background-color: {COLORS["bg_card"]};
    border: 1px solid {COLORS["border_soft"]};
    border-radius: 8px;
    text-align: center;
    color: {COLORS["text_muted"]};
    height: 22px;
    font-size: 11px;
}}

QProgressBar::chunk {{
    background-color: qlineargradient(
        x1:0, y1:0, x2:1, y2:0,
        stop:0 {COLORS["accent_dark"]}, stop:1 {COLORS["accent"]}
    );
    border-radius: 7px;
}}

QScrollBar:vertical {{
    background: transparent;
    width: 8px;
    margin: 4px 2px;
}}

QScrollBar::handle:vertical {{
    background: {COLORS["border"]};
    border-radius: 4px;
    min-height: 30px;
}}

QScrollBar::handle:vertical:hover {{
    background: {COLORS["accent"]};
}}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
}}

QCheckBox {{
    spacing: 10px;
}}

QCheckBox::indicator {{
    width: 20px;
    height: 20px;
    border-radius: 6px;
    border: 1px solid {COLORS["border"]};
    background: {COLORS["bg_card"]};
}}

QCheckBox::indicator:checked {{
    background: {COLORS["accent"]};
    border-color: {COLORS["accent"]};
}}

QTextEdit {{
    background-color: {COLORS["bg_card"]};
    border: none;
    border-radius: 10px;
    padding: 10px 12px;
    color: {COLORS["text_muted"]};
    font-family: "Cascadia Code", "Consolas", monospace;
    font-size: 12px;
}}

QDialog {{
    background-color: {COLORS["bg_dark"]};
}}
"""
