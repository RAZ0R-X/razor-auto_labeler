"""Export format definitions and grouping (Roboflow-compatible list)."""

from __future__ import annotations

EXPORT_FORMAT_GROUPS: dict[str, list[str]] = {
    "JSON": [
        "COCO",
        "COCO-MMDetection",
        "CreateML",
        "PaliGemma",
        "Florence 2 Object Detection",
        "OpenAI",
    ],
    "XML": [
        "Pascal VOC",
    ],
    "TXT": [
        "YOLO Darknet",
        "YOLO v3 Keras",
        "YOLO v4 PyTorch",
        "Scaled-YOLOv4",
        "YOLOv5 Oriented Bounding Boxes",
        "meituan/YOLOv6",
        "YOLO v5 PyTorch",
        "YOLO v7 PyTorch",
        "YOLOv8",
        "YOLOv8 Oriented Bounding Boxes",
        "YOLOv9",
        "YOLOv11",
        "YOLOv12",
        "YOLO26",
        "CSV",
    ],
}

ALL_EXPORT_FORMATS: list[str] = [
    fmt for formats in EXPORT_FORMAT_GROUPS.values() for fmt in formats
]

STANDARD_YOLO_FORMATS = {
    "YOLO v3 Keras",
    "YOLO v4 PyTorch",
    "Scaled-YOLOv4",
    "meituan/YOLOv6",
    "YOLO v5 PyTorch",
    "YOLO v7 PyTorch",
    "YOLOv8",
    "YOLOv9",
    "YOLOv11",
    "YOLOv12",
    "YOLO26",
}

OBB_YOLO_FORMATS = {
    "YOLOv5 Oriented Bounding Boxes",
    "YOLOv8 Oriented Bounding Boxes",
}

BATCH_JSON_FORMATS = {
    "COCO",
    "COCO-MMDetection",
    "CreateML",
    "PaliGemma",
    "Florence 2 Object Detection",
    "OpenAI",
}


def is_standard_yolo(export_format: str) -> bool:
    return export_format in STANDARD_YOLO_FORMATS or export_format == "YOLO Darknet"


def is_obb_yolo(export_format: str) -> bool:
    return export_format in OBB_YOLO_FORMATS


def is_batch_json(export_format: str) -> bool:
    return export_format in BATCH_JSON_FORMATS


def is_csv(export_format: str) -> bool:
    return export_format == "CSV"


def is_pascal_voc(export_format: str) -> bool:
    return export_format == "Pascal VOC"


def default_export_format() -> str:
    return "YOLOv11"


def populate_format_combo(combo) -> None:
    """Fill a QComboBox with grouped, non-selectable section headers."""
    from PyQt6.QtGui import QFont, QStandardItem, QStandardItemModel

    model = QStandardItemModel()
    for group_name, formats in EXPORT_FORMAT_GROUPS.items():
        header = QStandardItem(group_name)
        header.setEnabled(False)
        font = QFont()
        font.setBold(True)
        header.setFont(font)
        model.appendRow(header)
        for fmt in formats:
            model.appendRow(QStandardItem(fmt))

    combo.setModel(model)
    default = default_export_format()
    idx = combo.findText(default)
    if idx >= 0:
        combo.setCurrentIndex(idx)
