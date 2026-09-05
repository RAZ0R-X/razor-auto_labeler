"""Main application window."""

from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon, QPainter, QPixmap
from PyQt6.QtSvg import QSvgRenderer
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSizePolicy,
    QSpinBox,
    QStackedWidget,
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
from src.worker import LabelOptions, LabelWorker

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


def _section_label(text: str) -> QLabel:
    label = QLabel(text)
    label.setObjectName("sectionLabel")
    return label


def _hint_label(text: str) -> QLabel:
    label = QLabel(text)
    label.setObjectName("hintLabel")
    label.setWordWrap(True)
    return label


def _option_card(title: str) -> tuple[QFrame, QVBoxLayout]:
    card = QFrame()
    card.setObjectName("optionCard")
    card.setMinimumHeight(132)
    card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
    layout = QVBoxLayout(card)
    layout.setContentsMargins(16, 14, 16, 14)
    layout.setSpacing(10)
    layout.addWidget(_section_label(title))
    return card, layout


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("RAZOR-Auto Labeler")
        self.setWindowIcon(_load_app_icon())
        self.resize(1120, 880)
        self.setMinimumSize(1040, 800)
        self.setStyleSheet(APP_STYLESHEET)

        self.model_manager = ModelManager()
        self.image_paths: list[Path] = []
        self.class_mappings = []
        self.worker: LabelWorker | None = None

        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(28, 24, 28, 24)
        root.setSpacing(16)

        root.addLayout(self._build_header())
        root.addLayout(self._build_controls())
        root.addWidget(self._build_status_panel())
        root.addWidget(self._build_options_panel())

        body = QHBoxLayout()
        body.setSpacing(14)
        body.addWidget(self._build_class_list(), stretch=2)
        body.addWidget(self._build_image_list(), stretch=3)
        root.addLayout(body, stretch=1)

        root.addWidget(self._build_log_panel())
        root.addLayout(self._build_footer())
        self.load_model_btn.setFocus()

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

        format_wrap = QVBoxLayout()
        format_wrap.setSpacing(4)
        format_wrap.addWidget(_section_label("FORMAT"))
        self.format_combo = QComboBox()
        populate_format_combo(self.format_combo)
        self.format_combo.setMinimumWidth(220)
        self.format_combo.setToolTip("Label format written to the output folder.")
        format_wrap.addWidget(self.format_combo)

        conf_wrap = QVBoxLayout()
        conf_wrap.setSpacing(4)
        conf_wrap.addWidget(_section_label("CONFIDENCE"))
        self.conf_spin = QDoubleSpinBox()
        self.conf_spin.setRange(0.05, 1.0)
        self.conf_spin.setSingleStep(0.05)
        self.conf_spin.setValue(0.25)
        self.conf_spin.setDecimals(2)
        self.conf_spin.setFixedWidth(92)
        self.conf_spin.setToolTip("Detections below this score are discarded.")
        conf_wrap.addWidget(self.conf_spin)

        layout.addLayout(format_wrap)
        layout.addSpacing(8)
        layout.addLayout(conf_wrap)
        return layout

    def _stat_chip(self, caption: str, value: QLabel) -> QFrame:
        chip = QFrame()
        chip.setObjectName("statChip")
        box = QVBoxLayout(chip)
        box.setContentsMargins(14, 10, 14, 12)
        box.setSpacing(4)
        box.addWidget(_section_label(caption))
        value.setObjectName("statValue")
        value.setStyleSheet(f"color: {COLORS['text_muted']};")
        box.addWidget(value)
        return chip

    def _build_status_panel(self) -> QFrame:
        panel = QFrame()
        panel.setObjectName("accentPanel")
        row = QHBoxLayout(panel)
        row.setContentsMargins(10, 10, 10, 10)
        row.setSpacing(10)

        self.model_label = QLabel("Not loaded")
        self.classes_label = QLabel("—")
        self.images_label = QLabel("0")
        self.device_label = QLabel(ModelManager.device_label())

        row.addWidget(self._stat_chip("MODEL", self.model_label), stretch=2)
        row.addWidget(self._stat_chip("CLASSES", self.classes_label), stretch=3)
        row.addWidget(self._stat_chip("IMAGES", self.images_label), stretch=1)
        row.addWidget(self._stat_chip("DEVICE", self.device_label), stretch=1)
        return panel

    def _build_options_panel(self) -> QFrame:
        panel = QFrame()
        panel.setObjectName("optionsPanel")
        panel.setMinimumHeight(180)
        panel.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(12)

        header = QHBoxLayout()
        header.addWidget(_section_label("DATASET OPTIONS"))
        header.addStretch()
        layout.addLayout(header)
        layout.addWidget(_hint_label("These settings only apply when you click Auto Label."))

        cards = QHBoxLayout()
        cards.setSpacing(12)

        export_card, export_layout = _option_card("EXPORT")
        self.skip_empty_check = QCheckBox("Skip empty images")
        self.skip_empty_check.setChecked(True)
        self.skip_empty_check.setToolTip(
            "Images with no detections are not written as labels and are left out of the dataset."
        )
        self.resume_check = QCheckBox("Resume unfinished runs")
        self.resume_check.setChecked(True)
        self.resume_check.setToolTip(
            "Skips images that already have labels and continues a job from where it left off."
        )
        export_layout.addWidget(self.skip_empty_check)
        export_layout.addWidget(self.resume_check)
        export_layout.addWidget(_hint_label("Skip blanks. Continue a stopped job."))
        cards.addWidget(export_card, stretch=1)

        split_card, split_layout = _option_card("SPLIT")
        self.split_check = QCheckBox("Train / valid / test  (70/20/10)")
        self.split_check.setChecked(True)
        self.split_check.setToolTip(
            "Creates a dataset folder with 70/20/10 split ratios. Images are hard-linked "
            "so disk usage does not double."
        )
        self.split_check.toggled.connect(self._on_split_toggled)

        group_row = QHBoxLayout()
        group_row.setSpacing(8)
        self.split_group_label = QLabel("Frame group")
        self.split_group_label.setObjectName("fieldLabel")
        self.split_block_spin = QSpinBox()
        self.split_block_spin.setRange(1, 64)
        self.split_block_spin.setValue(4)
        self.split_block_spin.setToolTip(
            "How many consecutive frames stay in the same split. Keeps burst shots of "
            "the same plant from landing in both train and test."
        )
        group_row.addWidget(self.split_group_label)
        group_row.addStretch()
        group_row.addWidget(self.split_block_spin)

        split_layout.addWidget(self.split_check)
        split_layout.addLayout(group_row)
        split_layout.addWidget(_hint_label("Nearby frames stay in the same split."))
        cards.addWidget(split_card, stretch=1)

        layout.addLayout(cards)

        for box in (self.skip_empty_check, self.resume_check, self.split_check):
            box.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
            box.setMinimumHeight(26)

        return panel

    def _on_split_toggled(self, enabled: bool) -> None:
        self.split_block_spin.setEnabled(enabled)
        self.split_group_label.setEnabled(enabled)

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
        return layout

    def _build_class_list(self) -> QFrame:
        panel = QFrame()
        panel.setObjectName("panel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(8)

        self.class_header = _section_label("CLASSES")
        layout.addWidget(self.class_header)

        self.class_empty = QLabel("Load a model to see classes")
        self.class_empty.setObjectName("emptyHint")
        self.class_empty.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.class_list = QListWidget()

        self.class_stack = QStackedWidget()
        self.class_stack.addWidget(self.class_empty)
        self.class_stack.addWidget(self.class_list)
        layout.addWidget(self.class_stack)
        return panel

    def _build_image_list(self) -> QFrame:
        panel = QFrame()
        panel.setObjectName("panel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(8)

        self.image_header = _section_label("IMAGES")
        layout.addWidget(self.image_header)

        self.image_empty = QLabel("Load images or a folder to get started")
        self.image_empty.setObjectName("emptyHint")
        self.image_empty.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.image_list = QListWidget()

        self.image_stack = QStackedWidget()
        self.image_stack.addWidget(self.image_empty)
        self.image_stack.addWidget(self.image_list)
        layout.addWidget(self.image_stack)
        return panel

    def _build_log_panel(self) -> QFrame:
        panel = QFrame()
        panel.setObjectName("panel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(18, 14, 18, 14)
        layout.setSpacing(8)

        header = _section_label("LOG")
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

        self.stop_btn = QPushButton("Stop")
        self.stop_btn.setObjectName("ghostButton")
        self.stop_btn.setEnabled(False)

        self.run_btn = QPushButton("Auto Label")
        self.run_btn.setObjectName("primaryButton")
        self.run_btn.setEnabled(False)
        self.run_btn.setMinimumWidth(190)
        self.clear_btn.clicked.connect(self._clear_all)
        self.stop_btn.clicked.connect(self._stop_labeling)
        self.run_btn.clicked.connect(self._run_labeling)

        layout.addWidget(owner)
        layout.addWidget(self.progress, stretch=1)
        layout.addWidget(self.clear_btn)
        layout.addWidget(self.stop_btn)
        layout.addWidget(self.run_btn)
        return layout

    def _log(self, message: str) -> None:
        self.log_box.append(message)

    def _set_model_loaded_style(self, model_name: str) -> None:
        self.model_label.setText(model_name)
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

        has_model = self.model_manager.is_loaded
        if active:
            preview = ", ".join(m.export_name for m in active[:5])
            if len(active) > 5:
                preview += f" (+{len(active) - 5})"
            self.classes_label.setText(f"{len(active)} selected — {preview}")
            self.classes_label.setStyleSheet(f"color: {COLORS['text']};")
            self.class_header.setText(f"CLASSES  ·  {len(active)}")
            self.class_stack.setCurrentWidget(self.class_list)
        elif has_model:
            self.classes_label.setText("None selected")
            self.classes_label.setStyleSheet(f"color: {COLORS['text_muted']};")
            self.class_header.setText("CLASSES")
            self.class_empty.setText("No classes selected — click Edit Classes")
            self.class_stack.setCurrentWidget(self.class_empty)
        else:
            self.classes_label.setText("No model loaded")
            self.classes_label.setStyleSheet(f"color: {COLORS['text_muted']};")
            self.class_header.setText("CLASSES")
            self.class_empty.setText("Load a model to see classes")
            self.class_stack.setCurrentWidget(self.class_empty)

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

        self.images_label.setText(str(len(self.image_paths)))
        self.images_label.setStyleSheet(f"color: {COLORS['text']};" if self.image_paths else f"color: {COLORS['text_muted']};")
        self.image_header.setText(
            f"IMAGES  ·  {len(self.image_paths)}" if self.image_paths else "IMAGES"
        )
        self.image_stack.setCurrentWidget(
            self.image_list if self.image_paths else self.image_empty
        )
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

        options = LabelOptions(
            export_format=self.format_combo.currentText(),
            confidence=self.conf_spin.value(),
            iou=0.45,
            skip_empty=self.skip_empty_check.isChecked(),
            resume=self.resume_check.isChecked(),
            make_split=self.split_check.isChecked(),
            split_block=self.split_block_spin.value(),
        )

        self.run_btn.setEnabled(False)
        self.load_model_btn.setEnabled(False)
        self.load_images_btn.setEnabled(False)
        self.load_folder_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.progress.setValue(0)

        self.worker = LabelWorker(
            model_manager=self.model_manager,
            image_paths=self.image_paths,
            output_dir=Path(output_dir),
            class_mappings=self.class_mappings,
            options=options,
            parent=self,
        )
        self.worker.progress.connect(self._on_progress)
        self.worker.finished_ok.connect(self._on_finished)
        self.worker.failed.connect(self._on_failed)
        self.worker.start()

        self._log(f"Auto labeling started ({len(self.image_paths)} images)...")

    def _stop_labeling(self) -> None:
        if self.worker is None or not self.worker.isRunning():
            return
        self.worker.requestInterruption()
        self.stop_btn.setEnabled(False)
        self.progress.setFormat("Stopping...")
        self._log("Stop requested; labeling will stop after the current image.")

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
        self.stop_btn.setEnabled(not enabled)
        self.configure_classes_btn.setEnabled(enabled and self.model_manager.is_loaded)
        if enabled:
            self._refresh_class_list()
        self._update_run_state()

    def _clear_all(self) -> None:
        self.image_paths.clear()
        self.image_list.clear()
        self.images_label.setText("0")
        self.images_label.setStyleSheet(f"color: {COLORS['text_muted']};")
        self.image_header.setText("IMAGES")
        self.image_stack.setCurrentWidget(self.image_empty)
        self.progress.setValue(0)
        self.progress.setFormat("")
        self._log("Image list cleared.")
        self._update_run_state()
