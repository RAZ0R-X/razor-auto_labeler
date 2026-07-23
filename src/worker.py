"""Background worker for batch auto-labeling."""

from pathlib import Path

from PyQt6.QtCore import QThread, pyqtSignal

from src.class_config import ClassMapping, export_class_names
from src.export_formats import is_obb_yolo, is_pascal_voc, is_standard_yolo
from src.label_exporter import (
    batch_export_output_path,
    create_batch_exporter,
    export_voc,
    export_yolo,
    export_yolo_obb,
    save_annotated_image,
    write_info_file,
    write_data_yaml,
    write_obj_names_file,
)
from src.model_manager import ModelManager


class LabelWorker(QThread):
    progress = pyqtSignal(int, str)
    finished_ok = pyqtSignal(str)
    failed = pyqtSignal(str)

    def __init__(
        self,
        model_manager: ModelManager,
        image_paths: list[Path],
        output_dir: Path,
        class_mappings: list[ClassMapping],
        export_format: str,
        confidence: float,
        iou: float,
        parent=None,
    ):
        super().__init__(parent)
        self.model_manager = model_manager
        self.image_paths = image_paths
        self.output_dir = output_dir
        self.class_mappings = class_mappings
        self.export_format = export_format
        self.confidence = confidence
        self.iou = iou

    def run(self) -> None:
        try:
            total = len(self.image_paths)
            if total == 0:
                self.failed.emit("No images found to label.")
                return

            labels_dir = self.output_dir / "labels"
            annotated_dir = self.output_dir / "annotated"
            labels_dir.mkdir(parents=True, exist_ok=True)
            annotated_dir.mkdir(parents=True, exist_ok=True)

            export_names = export_class_names(self.class_mappings)
            write_data_yaml(export_names, self.output_dir)
            class_counts: dict[str, int] = {}

            if self.export_format == "YOLO Darknet":
                write_obj_names_file(export_names, self.output_dir)

            batch_exporter = create_batch_exporter(self.export_format, export_names)
            total_detections = 0

            for index, image_path in enumerate(self.image_paths, start=1):
                self.progress.emit(
                    int((index - 1) / total * 100),
                    f"Processing: {image_path.name} ({index}/{total})",
                )

                img_w, img_h = self.model_manager.get_image_size(image_path)
                detections = self.model_manager.predict(
                    image_path,
                    self.class_mappings,
                    confidence=self.confidence,
                    iou=self.iou,
                )
                total_detections += len(detections)
                for det in detections:
                    class_counts[det.class_name] = class_counts.get(det.class_name, 0) + 1

                if is_standard_yolo(self.export_format):
                    export_yolo(image_path, detections, labels_dir, img_w, img_h)
                elif is_obb_yolo(self.export_format):
                    export_yolo_obb(image_path, detections, labels_dir, img_w, img_h)
                elif is_pascal_voc(self.export_format):
                    export_voc(image_path, detections, labels_dir, img_w, img_h)
                elif batch_exporter is not None:
                    batch_exporter.add_image(image_path, img_w, img_h, detections)

                save_annotated_image(
                    image_path,
                    detections,
                    annotated_dir / image_path.name,
                )

            write_info_file(class_counts, self.output_dir)

            export_note = ""
            if batch_exporter is not None:
                out_path = batch_export_output_path(self.output_dir, self.export_format)
                batch_exporter.save(out_path)
                export_note = f"\nLabel file: {out_path}"
            elif is_pascal_voc(self.export_format) or is_standard_yolo(self.export_format) or is_obb_yolo(
                self.export_format
            ):
                export_note = f"\nLabels: {labels_dir}"

            self.progress.emit(100, "Completed")
            self.finished_ok.emit(
                f"{total} image(s) processed, {total_detections} label(s) created.\n"
                f"Format: {self.export_format}\n"
                f"Output: {self.output_dir}"
                f"{export_note}\n"
                f"Summary: {self.output_dir / 'info.txt'}\n"
                f"Annotated previews: {annotated_dir}"
            )
        except Exception as exc:
            self.failed.emit(str(exc))
