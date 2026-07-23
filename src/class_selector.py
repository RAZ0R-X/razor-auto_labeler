"""Dialog for selecting and renaming export classes."""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from src.class_config import ClassMapping
from src.theme import COLORS


class _ClassRow(QWidget):
    def __init__(self, mapping: ClassMapping, parent=None):
        super().__init__(parent)
        self.model_class_id = mapping.model_class_id

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        self.checkbox = QCheckBox()
        self.checkbox.setChecked(mapping.enabled)
        self.checkbox.setFixedWidth(28)

        model_label = QLabel(f"[{mapping.model_class_id}] {mapping.model_class_name}")
        model_label.setStyleSheet(f"color: {COLORS['text_muted']}; min-width: 140px;")
        model_label.setToolTip("Original class name detected by the model")

        arrow = QLabel("→")
        arrow.setStyleSheet(f"color: {COLORS['accent']}; font-weight: 700;")

        self.export_edit = QLineEdit(mapping.export_name)
        self.export_edit.setPlaceholderText("Export name...")
        self.export_edit.setToolTip(
            "Custom name shown in label files and previews.\n"
            "Rename the export label even if the model detects a different class name."
        )

        layout.addWidget(self.checkbox)
        layout.addWidget(model_label, stretch=1)
        layout.addWidget(arrow)
        layout.addWidget(self.export_edit, stretch=2)

    def to_mapping(self, model_class_name: str) -> ClassMapping:
        export_name = self.export_edit.text().strip() or model_class_name
        return ClassMapping(
            model_class_id=self.model_class_id,
            model_class_name=model_class_name,
            export_name=export_name,
            enabled=self.checkbox.isChecked(),
        )


class ClassSelectorDialog(QDialog):
    """Pick detections to include and set custom export names."""

    def __init__(
        self,
        mappings: list[ClassMapping],
        parent=None,
    ):
        super().__init__(parent)
        self.setWindowTitle("Class Configuration")
        self.setMinimumSize(620, 580)
        self._rows: dict[int, _ClassRow] = {}
        self._model_names = {m.model_class_id: m.model_class_name for m in mappings}

        layout = QVBoxLayout(self)
        layout.setSpacing(14)

        title = QLabel("Select objects to label and set export names")
        title.setStyleSheet(f"font-size: 17px; font-weight: 700; color: {COLORS['text']};")
        layout.addWidget(title)

        info = QFrame()
        info.setStyleSheet(
            f"""
            QFrame {{
                background-color: {COLORS['bg_card']};
                border: 1px solid {COLORS['border']};
                border-left: 3px solid {COLORS['accent']};
                border-radius: 8px;
                padding: 4px;
            }}
            """
        )
        info_layout = QVBoxLayout(info)
        info_layout.setContentsMargins(14, 10, 14, 10)
        info_text = QLabel(
            "Objects can be detected even if your model file uses different class names.\n"
            "Select model classes and set a custom export name on the right.\n"
            'Example: model detects "truck" → you export as "forklift".'
        )
        info_text.setWordWrap(True)
        info_text.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 12px;")
        info_layout.addWidget(info_text)
        layout.addWidget(info)

        header = QHBoxLayout()
        header.addWidget(self._header_label("Active", 28))
        header.addWidget(self._header_label("Model Class", 140), stretch=1)
        header.addWidget(self._header_label("", 20))
        header.addWidget(self._header_label("Export Name", 0), stretch=2)
        layout.addLayout(header)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        container = QWidget()
        list_layout = QVBoxLayout(container)
        list_layout.setSpacing(8)

        for mapping in mappings:
            row = _ClassRow(mapping)
            self._rows[mapping.model_class_id] = row
            list_layout.addWidget(row)

        list_layout.addStretch()
        scroll.setWidget(container)
        layout.addWidget(scroll)

        actions = QHBoxLayout()
        select_all = QPushButton("Select All")
        select_none = QPushButton("Clear")
        select_all.clicked.connect(self._select_all)
        select_none.clicked.connect(self._select_none)
        actions.addWidget(select_all)
        actions.addWidget(select_none)
        actions.addStretch()
        layout.addLayout(actions)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._validate_and_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _header_label(self, text: str, min_width: int) -> QLabel:
        label = QLabel(text)
        label.setObjectName("sectionLabel")
        if min_width:
            label.setMinimumWidth(min_width)
        return label

    def _select_all(self) -> None:
        for row in self._rows.values():
            row.checkbox.setChecked(True)

    def _select_none(self) -> None:
        for row in self._rows.values():
            row.checkbox.setChecked(False)

    def _validate_and_accept(self) -> None:
        active = [row for row in self._rows.values() if row.checkbox.isChecked()]
        if not active:
            return
        self.accept()

    def get_mappings(self) -> list[ClassMapping]:
        result: list[ClassMapping] = []
        for class_id, row in self._rows.items():
            result.append(row.to_mapping(self._model_names[class_id]))
        return sorted(result, key=lambda m: m.model_class_id)
