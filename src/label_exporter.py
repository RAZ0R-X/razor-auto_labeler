"""Export detections to multiple annotation formats."""

from __future__ import annotations

import csv
import json
import xml.etree.ElementTree as ET
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from pathlib import Path

from src.model_manager import Detection


IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tif", ".tiff"}

# BGR — theme accent #e50914
BOX_COLOR = (20, 9, 229)
BOX_THICKNESS = 2
LABEL_BG_COLOR = (20, 9, 229)
LABEL_TEXT_COLOR = (255, 255, 255)

PALIGEMMA_LOC_MAX = 1023


def to_yolo_line(detection: Detection, img_w: int, img_h: int) -> str:
    cx = ((detection.x1 + detection.x2) / 2) / img_w
    cy = ((detection.y1 + detection.y2) / 2) / img_h
    w = (detection.x2 - detection.x1) / img_w
    h = (detection.y2 - detection.y1) / img_h
    return f"{detection.class_id} {cx:.6f} {cy:.6f} {w:.6f} {h:.6f}"


def to_yolo_obb_line(detection: Detection, img_w: int, img_h: int) -> str:
    cx = ((detection.x1 + detection.x2) / 2) / img_w
    cy = ((detection.y1 + detection.y2) / 2) / img_h
    w = (detection.x2 - detection.x1) / img_w
    h = (detection.y2 - detection.y1) / img_h
    angle = 0.0
    return f"{detection.class_id} {cx:.6f} {cy:.6f} {w:.6f} {h:.6f} {angle:.6f}"


def export_yolo(
    image_path: Path,
    detections: list[Detection],
    output_dir: Path,
    img_w: int,
    img_h: int,
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    label_path = output_dir / f"{image_path.stem}.txt"
    lines = [to_yolo_line(d, img_w, img_h) for d in detections]
    label_path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
    return label_path


def export_yolo_obb(
    image_path: Path,
    detections: list[Detection],
    output_dir: Path,
    img_w: int,
    img_h: int,
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    label_path = output_dir / f"{image_path.stem}.txt"
    lines = [to_yolo_obb_line(d, img_w, img_h) for d in detections]
    label_path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
    return label_path


def export_voc(
    image_path: Path,
    detections: list[Detection],
    output_dir: Path,
    img_w: int,
    img_h: int,
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    annotation = ET.Element("annotation")

    ET.SubElement(annotation, "folder").text = str(output_dir.name)
    ET.SubElement(annotation, "filename").text = image_path.name
    size = ET.SubElement(annotation, "size")
    ET.SubElement(size, "width").text = str(img_w)
    ET.SubElement(size, "height").text = str(img_h)
    ET.SubElement(size, "depth").text = "3"

    for det in detections:
        obj = ET.SubElement(annotation, "object")
        ET.SubElement(obj, "name").text = det.class_name
        ET.SubElement(obj, "confidence").text = f"{det.confidence:.4f}"
        bbox = ET.SubElement(obj, "bndbox")
        ET.SubElement(bbox, "xmin").text = str(int(det.x1))
        ET.SubElement(bbox, "ymin").text = str(int(det.y1))
        ET.SubElement(bbox, "xmax").text = str(int(det.x2))
        ET.SubElement(bbox, "ymax").text = str(int(det.y2))

    label_path = output_dir / f"{image_path.stem}.xml"
    ET.ElementTree(annotation).write(label_path, encoding="utf-8", xml_declaration=True)
    return label_path


def _paligemma_loc(value: float, size: int) -> str:
    clamped = max(0, min(size, value))
    token = int(round(clamped / size * PALIGEMMA_LOC_MAX))
    return f"<loc{token:04d}>"


def _paligemma_box_tokens(det: Detection, img_w: int, img_h: int) -> str:
    return "".join(
        [
            _paligemma_loc(det.y1, img_h),
            _paligemma_loc(det.x1, img_w),
            _paligemma_loc(det.y2, img_h),
            _paligemma_loc(det.x2, img_w),
        ]
    )


def _florence_loc(value: float, size: int) -> str:
    clamped = max(0, min(size, value))
    token = int(round(clamped / size * 999))
    return f"<loc_{token}>"


def _florence_box_tokens(det: Detection, img_w: int, img_h: int) -> str:
    return "".join(
        [
            _florence_loc(det.y1, img_h),
            _florence_loc(det.x1, img_w),
            _florence_loc(det.y2, img_h),
            _florence_loc(det.x2, img_w),
        ]
    )


class BatchExporter(ABC):
    @abstractmethod
    def add_image(
        self, image_path: Path, img_w: int, img_h: int, detections: list[Detection]
    ) -> None:
        pass

    @abstractmethod
    def save(self, output_path: Path) -> Path:
        pass


class CocoExporter(BatchExporter):
    """Accumulates annotations and writes a single COCO JSON file."""

    def __init__(self, class_names: dict[int, str]) -> None:
        self.class_names = class_names
        self.images: list[dict] = []
        self.annotations: list[dict] = []
        self.categories = [
            {"id": cid, "name": name, "supercategory": "object"}
            for cid, name in sorted(class_names.items())
        ]
        self._image_id = 0
        self._ann_id = 0

    def add_image(
        self, image_path: Path, img_w: int, img_h: int, detections: list[Detection]
    ) -> None:
        self._image_id += 1
        image_id = self._image_id
        self.images.append(
            {
                "id": image_id,
                "file_name": image_path.name,
                "width": img_w,
                "height": img_h,
            }
        )

        for det in detections:
            self._ann_id += 1
            w = det.x2 - det.x1
            h = det.y2 - det.y1
            self.annotations.append(
                {
                    "id": self._ann_id,
                    "image_id": image_id,
                    "category_id": det.class_id,
                    "bbox": [det.x1, det.y1, w, h],
                    "area": w * h,
                    "iscrowd": 0,
                    "score": det.confidence,
                }
            )

    def save(self, output_path: Path) -> Path:
        payload = {
            "info": {
                "description": "Razor Auto Labeler export",
                "version": "1.0",
                "year": datetime.now(timezone.utc).year,
                "date_created": datetime.now(timezone.utc).isoformat(),
            },
            "licenses": [],
            "images": self.images,
            "annotations": self.annotations,
            "categories": self.categories,
        }
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return output_path


class CocoMMDetectionExporter(CocoExporter):
    """COCO JSON with MMDetection-compatible segmentation fields."""

    def add_image(
        self, image_path: Path, img_w: int, img_h: int, detections: list[Detection]
    ) -> None:
        before = len(self.annotations)
        super().add_image(image_path, img_w, img_h, detections)
        for ann in self.annotations[before:]:
            ann["segmentation"] = []
            ann["ignore"] = 0


class CreateMLExporter(BatchExporter):
    def __init__(self) -> None:
        self.entries: list[dict] = []

    def add_image(
        self, image_path: Path, img_w: int, img_h: int, detections: list[Detection]
    ) -> None:
        annotations = []
        for det in detections:
            w = det.x2 - det.x1
            h = det.y2 - det.y1
            annotations.append(
                {
                    "label": det.class_name,
                    "coordinates": {
                        "x": det.x1 + w / 2,
                        "y": det.y1 + h / 2,
                        "width": w,
                        "height": h,
                    },
                }
            )
        self.entries.append({"image": image_path.name, "annotations": annotations})

    def save(self, output_path: Path) -> Path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(self.entries, indent=2), encoding="utf-8")
        return output_path


class PaliGemmaExporter(BatchExporter):
    def __init__(self) -> None:
        self.lines: list[dict] = []

    def add_image(
        self, image_path: Path, img_w: int, img_h: int, detections: list[Detection]
    ) -> None:
        parts = []
        for det in detections:
            parts.append(f"{det.class_name}{_paligemma_box_tokens(det, img_w, img_h)}")
        suffix = " ; ".join(parts) if parts else ""
        self.lines.append(
            {
                "image": image_path.name,
                "prefix": "detect ",
                "suffix": suffix,
            }
        )

    def save(self, output_path: Path) -> Path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        content = "\n".join(json.dumps(line, ensure_ascii=False) for line in self.lines)
        output_path.write_text(content + ("\n" if self.lines else ""), encoding="utf-8")
        return output_path


class Florence2Exporter(BatchExporter):
    def __init__(self) -> None:
        self.lines: list[dict] = []

    def add_image(
        self, image_path: Path, img_w: int, img_h: int, detections: list[Detection]
    ) -> None:
        inner = ""
        for det in detections:
            inner += f"{det.class_name}{_florence_box_tokens(det, img_w, img_h)}"
        suffix = f"<OD>{inner}</OD>" if inner else "<OD></OD>"
        self.lines.append({"image": image_path.name, "suffix": suffix})

    def save(self, output_path: Path) -> Path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        content = "\n".join(json.dumps(line, ensure_ascii=False) for line in self.lines)
        output_path.write_text(content + ("\n" if self.lines else ""), encoding="utf-8")
        return output_path


class OpenAIExporter(BatchExporter):
    def __init__(self) -> None:
        self.lines: list[dict] = []

    def add_image(
        self, image_path: Path, img_w: int, img_h: int, detections: list[Detection]
    ) -> None:
        labels = []
        for det in detections:
            labels.append(
                f"{det.class_name} {int(det.x1)} {int(det.y1)} {int(det.x2)} {int(det.y2)}"
            )
        assistant_content = ", ".join(labels) if labels else "none"
        self.lines.append(
            {
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": "Detect and locate all objects."},
                            {
                                "type": "image_url",
                                "image_url": {"url": image_path.name},
                            },
                        ],
                    },
                    {"role": "assistant", "content": assistant_content},
                ]
            }
        )

    def save(self, output_path: Path) -> Path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        content = "\n".join(json.dumps(line, ensure_ascii=False) for line in self.lines)
        output_path.write_text(content + ("\n" if self.lines else ""), encoding="utf-8")
        return output_path


class CsvExporter(BatchExporter):
    HEADER = [
        "filename",
        "width",
        "height",
        "class",
        "xmin",
        "ymin",
        "xmax",
        "ymax",
        "confidence",
    ]

    def __init__(self) -> None:
        self.rows: list[list] = []

    def add_image(
        self, image_path: Path, img_w: int, img_h: int, detections: list[Detection]
    ) -> None:
        for det in detections:
            self.rows.append(
                [
                    image_path.name,
                    img_w,
                    img_h,
                    det.class_name,
                    int(det.x1),
                    int(det.y1),
                    int(det.x2),
                    int(det.y2),
                    round(det.confidence, 4),
                ]
            )

    def save(self, output_path: Path) -> Path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(self.HEADER)
            writer.writerows(self.rows)
        return output_path


def create_batch_exporter(export_format: str, class_names: dict[int, str]) -> BatchExporter | None:
    if export_format == "COCO":
        return CocoExporter(class_names)
    if export_format == "COCO-MMDetection":
        return CocoMMDetectionExporter(class_names)
    if export_format == "CreateML":
        return CreateMLExporter()
    if export_format == "PaliGemma":
        return PaliGemmaExporter()
    if export_format == "Florence 2 Object Detection":
        return Florence2Exporter()
    if export_format == "OpenAI":
        return OpenAIExporter()
    if export_format == "CSV":
        return CsvExporter()
    return None


def batch_export_output_path(output_dir: Path, export_format: str) -> Path:
    mapping = {
        "COCO": output_dir / "annotations.json",
        "COCO-MMDetection": output_dir / "annotations_mmdet.json",
        "CreateML": output_dir / "annotations.json",
        "PaliGemma": output_dir / "paligemma.jsonl",
        "Florence 2 Object Detection": output_dir / "florence2.jsonl",
        "OpenAI": output_dir / "openai_finetune.jsonl",
        "CSV": output_dir / "labels.csv",
    }
    return mapping[export_format]


def write_info_file(class_counts: dict[str, int], output_dir: Path) -> Path:
    """Write labeling summary: class name and bounding-box count per class."""
    info_path = output_dir / "info.txt"
    lines = [f"{name}: {count}" for name, count in sorted(class_counts.items())]
    info_path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
    return info_path


def write_obj_names_file(class_names: dict[int, str], output_dir: Path) -> Path:
    """Darknet obj.names — one class name per line."""
    names_path = output_dir / "obj.names"
    lines = [class_names[i] for i in sorted(class_names.keys())]
    names_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return names_path


def save_annotated_image(
    image_path: Path,
    detections: list[Detection],
    output_path: Path,
) -> Path:
    """Draw bounding boxes on the image and save a visual preview."""
    import cv2

    image = cv2.imread(str(image_path))
    if image is None:
        raise ValueError(f"Could not read image: {image_path}")

    for det in detections:
        x1 = max(0, int(det.x1))
        y1 = max(0, int(det.y1))
        x2 = min(image.shape[1], int(det.x2))
        y2 = min(image.shape[0], int(det.y2))

        cv2.rectangle(image, (x1, y1), (x2, y2), BOX_COLOR, BOX_THICKNESS)

        label = f"{det.class_name} {det.confidence * 100:.0f}%"
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 0.55
        thickness = 1
        (text_w, text_h), baseline = cv2.getTextSize(label, font, font_scale, thickness)

        label_y1 = max(y1 - text_h - baseline - 6, 0)
        label_y2 = label_y1 + text_h + baseline + 6
        label_x2 = min(x1 + text_w + 10, image.shape[1])

        cv2.rectangle(image, (x1, label_y1), (label_x2, label_y2), LABEL_BG_COLOR, -1)
        cv2.putText(
            image,
            label,
            (x1 + 5, label_y2 - baseline - 3),
            font,
            font_scale,
            LABEL_TEXT_COLOR,
            thickness,
            cv2.LINE_AA,
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(output_path), image)
    return output_path


def write_data_yaml(class_names: dict[int, str], output_dir: Path) -> Path:
    """Write Roboflow / Ultralytics-compatible data.yaml."""
    yaml_path = output_dir / "data.yaml"
    names = [class_names[i] for i in sorted(class_names.keys())]
    names_lines = "\n".join(f"  - {name}" for name in names)
    content = (
        f"train: train/images\n"
        f"val: valid/images\n"
        f"test: test/images\n"
        f"\n"
        f"nc: {len(names)}\n"
        f"names:\n"
        f"{names_lines}\n"
    )
    yaml_path.write_text(content, encoding="utf-8")
    return yaml_path
