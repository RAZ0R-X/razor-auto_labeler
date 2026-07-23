"""Dialog for adding a target class to label."""

from __future__ import annotations

from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QLabel,
    QLineEdit,
    QVBoxLayout,
)

from src.class_config import ClassMapping
from src.theme import COLORS


class AddClassDialog(QDialog):
    def __init__(
        self,
        model_class_names: dict[int, str],
        existing_export_names: set[str],
        open_vocabulary: bool = False,
        parent=None,
    ):
        super().__init__(parent)
        self.setWindowTitle("Sınıf Ekle")
        self.setMinimumWidth(420)
        self._model_class_names = model_class_names
        self._existing = existing_export_names
        self._open_vocabulary = open_vocabulary

        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        title = QLabel("Etiketlenecek sınıfı ekleyin")
        title.setStyleSheet(f"font-size: 16px; font-weight: 700; color: {COLORS['text']};")
        layout.addWidget(title)

        hint = QLabel(
            "YOLO-World modeli: sadece istediğiniz sınıf adını yazın, model metne göre arar."
            if open_vocabulary
            else "Export ismi etiket dosyalarında görünür.\n"
            "Model sınıfı, modelin görüntüde arayacağı nesne türüdür."
        )
        hint.setWordWrap(True)
        hint.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 12px;")
        layout.addWidget(hint)

        layout.addWidget(QLabel("Export ismi (istediğiniz ad)"))
        self.export_edit = QLineEdit()
        self.export_edit.setPlaceholderText("ör. forklift, baret, insan...")
        self.export_edit.textChanged.connect(self._auto_match_model_class)
        layout.addWidget(self.export_edit)

        self.model_label = QLabel("Model sınıfı (algılanacak nesne)")
        layout.addWidget(self.model_label)
        self.model_combo = QComboBox()
        for class_id, name in sorted(model_class_names.items()):
            self.model_combo.addItem(f"[{class_id}] {name}", class_id)
        layout.addWidget(self.model_combo)

        if open_vocabulary:
            self.model_label.hide()
            self.model_combo.hide()

        self.error_label = QLabel("")
        self.error_label.setStyleSheet(f"color: {COLORS['accent']}; font-size: 12px;")
        layout.addWidget(self.error_label)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._validate_and_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _auto_match_model_class(self) -> None:
        query = self.export_edit.text().strip().lower()
        if not query:
            return
        for index in range(self.model_combo.count()):
            label = self.model_combo.itemText(index).lower()
            if query in label:
                self.model_combo.setCurrentIndex(index)
                return

    def _validate_and_accept(self) -> None:
        export_name = self.export_edit.text().strip()
        if not export_name:
            self.error_label.setText("Export ismi boş olamaz.")
            return
        if export_name.lower() in {name.lower() for name in self._existing}:
            self.error_label.setText("Bu isim zaten ekli.")
            return
        self.error_label.setText("")
        self.accept()

    def get_mapping(self) -> ClassMapping:
        export_name = self.export_edit.text().strip()
        if self._open_vocabulary:
            model_class_id = len(self._existing)
            model_class_name = export_name
        else:
            model_class_id = int(self.model_combo.currentData())
            model_class_name = self._model_class_names[model_class_id]
        return ClassMapping(
            model_class_id=model_class_id,
            model_class_name=model_class_name,
            export_name=export_name,
            enabled=True,
        )
