"""Detection model loading and inference."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from src.class_config import ClassMapping, export_id_for_model_class, export_name_for_model_class


@dataclass
class Detection:
    model_class_id: int
    class_id: int
    class_name: str
    confidence: float
    x1: float
    y1: float
    x2: float
    y2: float


class ModelManager:
    """Wraps Ultralytics YOLO and compatible ONNX/TorchScript models."""

    SUPPORTED_EXTENSIONS = {".pt", ".onnx", ".engine", ".torchscript", ".xml", ".tflite"}

    def __init__(self) -> None:
        self.model = None
        self.model_path: Path | None = None
        self.class_names: dict[int, str] = {}

    @property
    def is_loaded(self) -> bool:
        return self.model is not None

    def load(self, path: str | Path) -> dict[int, str]:
        path = Path(path)
        if path.suffix.lower() not in self.SUPPORTED_EXTENSIONS:
            raise ValueError(
                f"Unsupported model format: {path.suffix}. "
                f"Supported: {', '.join(sorted(self.SUPPORTED_EXTENSIONS))}"
            )

        from ultralytics import YOLO

        self.model = YOLO(str(path))
        self.model_path = path
        self.class_names = {int(k): str(v) for k, v in self.model.names.items()}
        return self.class_names

    def supports_open_vocabulary(self) -> bool:
        if not self.is_loaded or self.model_path is None:
            return False
        name = self.model_path.name.lower()
        if "world" in name:
            return True
        model_type = type(self.model).__name__.lower()
        return "world" in model_type

    def set_target_class_names(self, class_names: list[str]) -> bool:
        """Apply custom class names for open-vocabulary models (e.g. YOLO-World)."""
        if not self.is_loaded or not class_names:
            return False
        if not hasattr(self.model, "set_classes"):
            return False
        try:
            self.model.set_classes(class_names)
            self.class_names = {int(k): str(v) for k, v in self.model.names.items()}
            return True
        except Exception:
            return False

    def predict(
        self,
        image_path: str | Path,
        class_mappings: list[ClassMapping],
        confidence: float = 0.25,
        iou: float = 0.45,
    ) -> list[Detection]:
        if not self.is_loaded:
            raise RuntimeError("Model not loaded.")

        active = [m for m in class_mappings if m.enabled]
        if not active:
            return []

        if self.supports_open_vocabulary():
            self.set_target_class_names([m.export_name for m in active])

        enabled_ids = {m.model_class_id for m in active}
        if self.supports_open_vocabulary():
            enabled_ids = set(range(len(active)))

        results = self.model.predict(
            source=str(image_path),
            conf=confidence,
            iou=iou,
            verbose=False,
        )

        detections: list[Detection] = []
        for result in results:
            boxes = result.boxes
            if boxes is None:
                continue

            for box in boxes:
                model_class_id = int(box.cls.item())
                if self.supports_open_vocabulary():
                    if model_class_id < 0 or model_class_id >= len(active):
                        continue
                    mapping = active[model_class_id]
                    export_id = model_class_id
                    export_name = mapping.export_name
                else:
                    if model_class_id not in enabled_ids:
                        continue
                    export_id = export_id_for_model_class(class_mappings, model_class_id)
                    export_name = export_name_for_model_class(class_mappings, model_class_id)
                    if export_id is None or export_name is None:
                        continue

                conf = float(box.conf.item())
                x1, y1, x2, y2 = box.xyxy[0].tolist()
                detections.append(
                    Detection(
                        model_class_id=model_class_id,
                        class_id=export_id,
                        class_name=export_name,
                        confidence=conf,
                        x1=x1,
                        y1=y1,
                        x2=x2,
                        y2=y2,
                    )
                )

        return detections

    def get_image_size(self, image_path: str | Path) -> tuple[int, int]:
        from PIL import Image

        with Image.open(image_path) as img:
            width, height = img.size
        return width, height
