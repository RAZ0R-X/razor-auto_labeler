"""Main application window."""

from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon, QPainter, QPixmap
from PyQt6.QtSvg import QSvgRenderer
from PyQt6.QtWidgets import (
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from src.class_config import ClassMapping, build_mappings_from_model, enabled_mappings
from src.class_selector import ClassSelectorDialog
from src.export_formats import populate_format_combo
from src.label_exporter import IMAGE_EXTENSIONS
from src.model_manager import ModelManager
from src.theme import APP_STYLESHEET, COLORS
from src.worker import LabelWorker

LOGO_PATH = Path(__file__).resolve().parent.parent / "assets" / "logo.svg"
LOGO_ICO_PATH = Path(__file__).resolve().parent.parent / "assets" / "logo.ico"


def _load_logo_pixmap(size: int = 44) -> QPixmap:
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    if LOGO_PATH.exists():
        renderer = QSvgRenderer(str(LOGO_PATH))
        painter = QPainter(pixmap)
        renderer.render(painter)
        painter.end()
    return pixmap


def _load_app_icon() -> QIcon:
    if LOGO_ICO_PATH.exists():
        return QIcon(str(LOGO_ICO_PATH))
    icon = QIcon()
    for size in (16, 24, 32, 48, 64, 128, 256):
        icon.addPixmap(_load_logo_pixmap(size))
    return icon


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("RAZOR-Auto Labeler")
        self.setWindowIcon(_load_app_icon())
        self.resize(1100, 740)
        self.setMinimumSize(960, 680)
        self.setStyleSheet(APP_STYLESHEET)

        self.model_manager = ModelManager()
        self.image_paths: list[Path] = []
        self.class_mappings = []
        self.worker: LabelWorker | None = None

        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(32, 28, 32, 28)
        root.setSpacing(18)

        root.addLayout(self._build_header())
        root.addWidget(self._build_status_panel())
        root.addLayout(self._build_controls())
        root.addWidget(self._build_class_list(), stretch=0)
        root.addWidget(self._build_image_list(), stretch=1)
        root.addWidget(self._build_log_panel())
        root.addLayout(self._build_footer())

    def _build_header(self) -> QHBoxLayout:
        layout = QHBoxLayout()
        layout.setSpacing(14)

        logo = QLabel()
        logo.setPixmap(_load_logo_pixmap())
        logo.setFixedSize(44, 44)

        titles = QVBoxLayout()
        titles.setSpacing(2)
        title = QLabel("RAZOR-Auto Labeler")
        title.setObjectName("titleLabel")
        subtitle = QLabel("OBJECT DETECTION AUTO LABELER")
        subtitle.setObjectName("subtitleLabel")
        titles.addWidget(title)
        titles.addWidget(subtitle)

        layout.addWidget(logo)
        layout.addLayout(titles)
        layout.addStretch()
        return layout

    def _build_status_panel(self) -> QFrame:
        panel = QFrame()
        panel.setObjectName("accentPanel")
        grid = QGridLayout(panel)
        grid.setContentsMargins(22, 18, 22, 18)
        grid.setHorizontalSpacing(32)

        self.model_label = QLabel("Model: Not loaded")
        self.model_label.setStyleSheet(f"color: {COLORS['text_muted']};")
        self.classes_label = QLabel("Classes: —")
        self.classes_label.setStyleSheet(f"color: {COLORS['text_muted']};")
        self.images_label = QLabel("Images: 0")
        self.images_label.setStyleSheet(f"color: {COLORS['text_muted']};")

        grid.addWidget(self.model_label, 0, 0)
        grid.addWidget(self.classes_label, 0, 1)
        grid.addWidget(self.images_label, 0, 2)
        return panel

    def _build_controls(self) -> QHBoxLayout:
        layout = QHBoxLayout()
        layout.setSpacing(10)

        self.load_model_btn = QPushButton("Load Model")
        self.load_model_btn.clicked.connect(self._load_model)

        self.configure_classes_btn = QPushButton("Edit Classes")
        self.configure_classes_btn.setEnabled(False)
        self.configure_classes_btn.clicked.connect(self._select_classes)

        self.load_images_btn = QPushButton("Load Images")
        self.load_images_btn.clicked.connect(self._load_images)

        self.load_folder_btn = QPushButton("Load Folder")
        self.load_folder_btn.clicked.connect(self._load_folder)

        layout.addWidget(self.load_model_btn)
        layout.addWidget(self.configure_classes_btn)
        layout.addWidget(self.load_images_btn)
        layout.addWidget(self.load_folder_btn)
        layout.addStretch()

        format_label = QLabel("FORMAT")
        format_label.setObjectName("sectionLabel")
        self.format_combo = QComboBox()
        populate_format_combo(self.format_combo)
        self.format_combo.setFixedWidth(240)

        conf_label = QLabel("CONFIDENCE")
        conf_label.setObjectName("sectionLabel")
        self.conf_spin = QDoubleSpinBox()
        self.conf_spin.setRange(0.05, 1.0)
        self.conf_spin.setSingleStep(0.05)
        self.conf_spin.setValue(0.25)
        self.conf_spin.setFixedWidth(72)

        layout.addWidget(format_label)
        layout.addWidget(self.format_combo)
        layout.addSpacing(12)
        layout.addWidget(conf_label)
        layout.addWidget(self.conf_spin)
        return layout

    def _build_class_list(self) -> QFrame:
        panel = QFrame()
        panel.setObjectName("panel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(18, 14, 18, 14)
        layout.setSpacing(8)

        header = QLabel("CURRENT CLASSES")
        header.setObjectName("sectionLabel")
        layout.addWidget(header)

        self.class_list = QListWidget()
        self.class_list.setMaximumHeight(96)
        layout.addWidget(self.class_list)
        return panel

    def _build_image_list(self) -> QFrame:
        panel = QFrame()
        panel.setObjectName("panel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(10)

        header = QLabel("LOADED IMAGES")
        header.setObjectName("sectionLabel")
        layout.addWidget(header)

        self.image_list = QListWidget()
        layout.addWidget(self.image_list)
        return panel

    def _build_log_panel(self) -> QFrame:
        panel = QFrame()
        panel.setObjectName("panel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(18, 14, 18, 14)
        layout.setSpacing(8)

        header = QLabel("LOG")
        header.setObjectName("sectionLabel")
        layout.addWidget(header)

        self.log_box = QTextEdit()
        self.log_box.setReadOnly(True)
        self.log_box.setMaximumHeight(110)
        layout.addWidget(self.log_box)
        return panel

    def _build_footer(self) -> QHBoxLayout:
        layout = QHBoxLayout()
        layout.setSpacing(12)

        self.progress = QProgressBar()
        self.progress.setValue(0)
        self.progress.setTextVisible(True)

        owner = QLabel(
            f'<span style="color:{COLORS["accent"]}; font-weight:700; letter-spacing:1px;">Owner</span>'
            f'<span style="color:{COLORS["text_muted"]};"> · Cihan Cinoğlu</span>'
        )
        owner.setObjectName("ownerLabel")
        owner.setTextFormat(Qt.TextFormat.RichText)

        self.clear_btn = QPushButton("Clear")
        self.clear_btn.setObjectName("ghostButton")

        self.run_btn = QPushButton("Auto Label")
        self.run_btn.setObjectName("primaryButton")
        self.run_btn.setEnabled(False)
        self.run_btn.setMinimumWidth(190)
        self.clear_btn.clicked.connect(self._clear_all)
        self.run_btn.clicked.connect(self._run_labeling)

        layout.addWidget(owner)
        layout.addWidget(self.progress, stretch=1)
        layout.addWidget(self.clear_btn)
        layout.addWidget(self.run_btn)
        return layout

    def _log(self, message: str) -> None:
        self.log_box.append(message)

    def _set_model_loaded_style(self, model_name: str) -> None:
        self.model_label.setText(f"● Model: {model_name}")
        self.model_label.setObjectName("statusOk")
        self.model_label.setStyleSheet(
            f"""
            color: {COLORS['success_glow']};
            font-weight: 600;
            font-size: 13px;
            """
        )

    def _refresh_class_list(self) -> None:
        self.class_list.clear()
        active = enabled_mappings(self.class_mappings)
        open_vocab = self.model_manager.supports_open_vocabulary()

        for mapping in active:
            if open_vocab or mapping.export_name == mapping.model_class_name:
                text = mapping.export_name
            else:
                text = f"{mapping.export_name}  ←  [{mapping.model_class_id}] {mapping.model_class_name}"
            self.class_list.addItem(text)

        if active:
            preview = ", ".join(m.export_name for m in active[:5])
            if len(active) > 5:
                preview += f" (+{len(active) - 5})"
            self.classes_label.setText(f"Selected: {len(active)} classes — {preview}")
            self.classes_label.setStyleSheet(f"color: {COLORS['text']};")
        else:
            self.classes_label.setText("Classes: No model loaded")
            self.classes_label.setStyleSheet(f"color: {COLORS['text_muted']};")

        has_model = self.model_manager.is_loaded
        self.configure_classes_btn.setEnabled(has_model)
        self._update_run_state()

    def _update_run_state(self) -> None:
        ready = (
            self.model_manager.is_loaded
            and bool(self.image_paths)
            and bool(enabled_mappings(self.class_mappings))
        )
        self.run_btn.setEnabled(ready)

    def _load_model(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Model File",
            "",
            "Model Files (*.pt *.onnx *.engine *.torchscript *.xml *.tflite);;All Files (*.*)",
        )
        if not path:
            return

        try:
            class_names = self.model_manager.load(path)
            self.class_mappings = build_mappings_from_model(class_names)
            self._set_model_loaded_style(Path(path).name)
            self._refresh_class_list()
            active = enabled_mappings(self.class_mappings)
            self._log(f"Model loaded: {path}")
            self._log(
                f"All classes selected ({len(active)}): {', '.join(m.export_name for m in active[:8])}"
                + (f" (+{len(active) - 8})" if len(active) > 8 else "")
            )
            self._update_run_state()
        except Exception as exc:
            QMessageBox.critical(self, "Model Error", str(exc))
            self._log(f"ERROR: {exc}")

    def _select_classes(self) -> None:
        if not self.model_manager.is_loaded:
            return

        all_mappings = list(self.class_mappings)
        model_ids = {m.model_class_id for m in all_mappings}
        for class_id, name in self.model_manager.class_names.items():
            if class_id not in model_ids:
                all_mappings.append(
                    ClassMapping(
                        model_class_id=class_id,
                        model_class_name=name,
                        export_name=name,
                        enabled=False,
                    )
                )

        dialog = ClassSelectorDialog(sorted(all_mappings, key=lambda m: m.model_class_id), parent=self)
        if dialog.exec():
            self.class_mappings = [m for m in dialog.get_mappings() if m.enabled]
            if not self.class_mappings:
                QMessageBox.warning(self, "Warning", "Select at least one class.")
                return
            self._refresh_class_list()
            active = enabled_mappings(self.class_mappings)
            self._log(f"Export classes: {', '.join(m.export_name for m in active)}")

    def _add_images(self, paths: list[str]) -> None:
        added = 0
        for raw in paths:
            path = Path(raw)
            if path.suffix.lower() not in IMAGE_EXTENSIONS:
                continue
            if path not in self.image_paths:
                self.image_paths.append(path)
                self.image_list.addItem(path.name)
                added += 1

        self.images_label.setText(f"Images: {len(self.image_paths)}")
        if added:
            self._log(f"{added} image(s) added.")
        self._update_run_state()

    def _load_images(self) -> None:
        paths, _ = QFileDialog.getOpenFileNames(
            self,
            "Select Images",
            "",
            "Images (*.jpg *.jpeg *.png *.bmp *.webp *.tif *.tiff);;All Files (*.*)",
        )
        if paths:
            self._add_images(paths)

    def _load_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Select Image Folder")
        if not folder:
            return

        paths = []
        for ext in IMAGE_EXTENSIONS:
            paths.extend(str(p) for p in Path(folder).rglob(f"*{ext}"))
            paths.extend(str(p) for p in Path(folder).rglob(f"*{ext.upper()}"))

        self._add_images(sorted(set(paths)))

    def _run_labeling(self) -> None:
        if not self.model_manager.is_loaded or not self.image_paths:
            return

        if not enabled_mappings(self.class_mappings):
            QMessageBox.warning(
                self,
                "Classes Required",
                "Select at least one class before labeling.",
            )
            return

        output_dir = QFileDialog.getExistingDirectory(self, "Select Output Folder")
        if not output_dir:
            return

        self.run_btn.setEnabled(False)
        self.load_model_btn.setEnabled(False)
        self.load_images_btn.setEnabled(False)
        self.load_folder_btn.setEnabled(False)
        self.progress.setValue(0)

        self.worker = LabelWorker(
            model_manager=self.model_manager,
            image_paths=self.image_paths,
            output_dir=Path(output_dir),
            class_mappings=self.class_mappings,
            export_format=self.format_combo.currentText(),
            confidence=self.conf_spin.value(),
            iou=0.45,
            parent=self,
        )
        self.worker.progress.connect(self._on_progress)
        self.worker.finished_ok.connect(self._on_finished)
        self.worker.failed.connect(self._on_failed)
        self.worker.start()
        self._log("Auto labeling started...")

    def _on_progress(self, value: int, message: str) -> None:
        self.progress.setValue(value)
        self.progress.setFormat(message)

    def _on_finished(self, message: str) -> None:
        self._log(message)
        self.progress.setValue(100)
        self.progress.setFormat("Completed")
        self._set_controls_enabled(True)
        QMessageBox.information(self, "Success", message)

    def _on_failed(self, message: str) -> None:
        self._log(f"ERROR: {message}")
        self.progress.setFormat("Error")
        self._set_controls_enabled(True)
        QMessageBox.critical(self, "Labeling Error", message)

    def _set_controls_enabled(self, enabled: bool) -> None:
        self.load_model_btn.setEnabled(enabled)
        self.load_images_btn.setEnabled(enabled)
        self.load_folder_btn.setEnabled(enabled)
        self.configure_classes_btn.setEnabled(enabled and self.model_manager.is_loaded)
        if enabled:
            self._refresh_class_list()
        self._update_run_state()

    def _clear_all(self) -> None:
        self.image_paths.clear()
        self.image_list.clear()
        self.images_label.setText("Images: 0")
        self.progress.setValue(0)
        self.progress.setFormat("")
        self._log("Image list cleared.")
        self._update_run_state()
