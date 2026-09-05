"""Background worker for batch auto-labeling."""

from dataclasses import dataclass, field
from pathlib import Path
from time import monotonic

from PyQt6.QtCore import QThread, pyqtSignal

from src.class_config import ClassMapping, export_class_names
from src.dataset_splitter import write_split_dataset
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


@dataclass
class LabelOptions:
    """Everything the run needs beyond the model, images and output folder."""

    export_format: str = "YOLOv11"
    confidence: float = 0.25
    iou: float = 0.45

    # Sliced inference. Without it a 50 MP frame is squashed to the network
    # input size and small objects disappear entirely.
    tiled: bool = False
    tile: int = 1024
    overlap: float = 0.2
    batch: int = 8

    skip_empty: bool = True
    resume: bool = True

    make_split: bool = False
    split_block: int = 1
    split_seed: int = 17

    preview_max_side: int = 1600

    class_counts: dict[str, int] = field(default_factory=dict)


def _tally_label_file(
    path: Path, export_names: dict[int, str], class_counts: dict[str, int]
) -> int:
    """Fold an already-written YOLO label file into the running totals.

    Resumed images are not re-detected, so without this their boxes would be
    missing from the final per-class report.
    """
    found = 0
    for line in path.read_text(encoding="utf-8").splitlines():
        parts = line.split()
        if not parts:
            continue
        try:
            class_id = int(parts[0])
        except ValueError:
            continue
        name = export_names.get(class_id, str(class_id))
        class_counts[name] = class_counts.get(name, 0) + 1
        found += 1
    return found


def _format_eta(seconds: float) -> str:
    if seconds < 90:
        return f"{seconds:.0f}s"
    if seconds < 5400:
        return f"{seconds / 60:.0f} min"
    return f"{seconds / 3600:.1f}h"


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
        options: LabelOptions,
        parent=None,
    ):
        super().__init__(parent)
        self.model_manager = model_manager
        self.image_paths = image_paths
        self.output_dir = output_dir
        self.class_mappings = class_mappings
        self.options = options

    def run(self) -> None:
        try:
            self._label()
        except Exception as exc:
            self.failed.emit(str(exc))

    def _label(self) -> None:
        options = self.options
        total = len(self.image_paths)
        if total == 0:
            self.failed.emit("No images found to label.")
            return

        labels_dir = self.output_dir / "labels"
        labels_dir.mkdir(parents=True, exist_ok=True)

        annotated_dir = self.output_dir / "annotated"
        annotated_dir.mkdir(parents=True, exist_ok=True)

        export_names = export_class_names(self.class_mappings)
        write_data_yaml(export_names, self.output_dir)
        if options.export_format == "YOLO Darknet":
            write_obj_names_file(export_names, self.output_dir)

        batch_exporter = create_batch_exporter(options.export_format, export_names)
        writes_own_labels = (
            is_standard_yolo(options.export_format)
            or is_obb_yolo(options.export_format)
            or is_pascal_voc(options.export_format)
        )

        class_counts: dict[str, int] = {}
        total_detections = 0
        empty_images = 0
        resumed = 0
        started = monotonic()

        for index, image_path in enumerate(self.image_paths, start=1):
            if self.isInterruptionRequested():
                self.progress.emit(100, "Stopped")
                self.finished_ok.emit(
                    f"Stopped by user. {index - 1}/{total} images processed.\n"
                    f"Labels: {labels_dir}"
                )
                return

            if options.resume and writes_own_labels:
                existing = labels_dir / f"{image_path.stem}.txt"
                if existing.exists():
                    resumed += 1
                    if not is_pascal_voc(options.export_format):
                        total_detections += _tally_label_file(
                            existing, export_names, class_counts
                        )
                    continue

            done_ratio = (index - 1) / total
            elapsed = monotonic() - started
            processed = index - 1 - resumed
            eta = ""
            if processed >= 3 and done_ratio > 0:
                per_image = elapsed / processed
                eta = f"  ~{_format_eta(per_image * (total - index + 1))} left"

            self.progress.emit(
                int(done_ratio * 100),
                f"{image_path.name} ({index}/{total}){eta}",
            )

            img_w, img_h = self.model_manager.get_image_size(image_path)
            detections = self.model_manager.predict(
                image_path,
                self.class_mappings,
                confidence=options.confidence,
                iou=options.iou,
                tiled=options.tiled,
                tile=options.tile,
                overlap=options.overlap,
                batch=options.batch,
            )

            if not detections:
                empty_images += 1
                if options.skip_empty:
                    continue

            total_detections += len(detections)
            for detection in detections:
                class_counts[detection.class_name] = class_counts.get(detection.class_name, 0) + 1

            if is_standard_yolo(options.export_format):
                export_yolo(image_path, detections, labels_dir, img_w, img_h)
            elif is_obb_yolo(options.export_format):
                export_yolo_obb(image_path, detections, labels_dir, img_w, img_h)
            elif is_pascal_voc(options.export_format):
                export_voc(image_path, detections, labels_dir, img_w, img_h)
            elif batch_exporter is not None:
                batch_exporter.add_image(image_path, img_w, img_h, detections)

            if detections:
                save_annotated_image(
                    image_path,
                    detections,
                    annotated_dir / image_path.name,
                    max_side=options.preview_max_side,
                )

        write_info_file(class_counts, self.output_dir)

        notes = [
            f"{total} images scanned, {total_detections} labels created.",
            f"Format: {options.export_format}",
        ]
        if resumed:
            notes.append(f"{resumed} images already labeled, skipped.")
        if empty_images:
            action = "skipped" if options.skip_empty else "saved with empty labels"
            notes.append(f"{empty_images} images had no detections, {action}.")

        if batch_exporter is not None:
            out_path = batch_export_output_path(self.output_dir, options.export_format)
            batch_exporter.save(out_path)
            notes.append(f"Label file: {out_path}")
        elif writes_own_labels:
            notes.append(f"Labels: {labels_dir}")

        if options.make_split and is_standard_yolo(options.export_format):
            self.progress.emit(99, "Splitting train/valid/test...")
            report = write_split_dataset(
                self.image_paths,
                labels_dir,
                self.output_dir / "dataset",
                export_names,
                block=options.split_block,
                seed=options.split_seed,
            )
            notes.append(f"Split (70/20/10): {report.summary()}")
            notes.append(
                f"{report.linked} images hard-linked, {report.copied} copied → "
                f"{self.output_dir / 'dataset'}"
            )
            if report.data_yaml:
                notes.append(f"Training file: {report.data_yaml}")
        elif options.make_split:
            notes.append("Split skipped: only works with standard YOLO formats.")

        notes.append(f"Summary: {self.output_dir / 'info.txt'}")
        notes.append(f"Boxed images: {annotated_dir}")
        notes.append(f"Time: {_format_eta(monotonic() - started)}")

        self.progress.emit(100, "Completed")
        self.finished_ok.emit("\n".join(notes))
