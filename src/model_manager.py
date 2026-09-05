"""Detection model loading and inference."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from src.class_config import ClassMapping, export_id_for_model_class, export_name_for_model_class
from src.tiled_predict import RawBox, predict_tiled


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

    @staticmethod
    def device_label() -> str:
        try:
            import torch
        except ImportError:
            return "CPU (torch missing)"
        if torch.cuda.is_available():
            return f"GPU: {torch.cuda.get_device_name(0)}"
        return "CPU (no CUDA — will be slow)"

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

    def _to_detection(
        self,
        model_class_id: int,
        confidence: float,
        box: tuple[float, float, float, float],
        class_mappings: list[ClassMapping],
        active: list[ClassMapping],
    ) -> Detection | None:
        if self.supports_open_vocabulary():
            if model_class_id < 0 or model_class_id >= len(active):
                return None
            export_id = model_class_id
            export_name = active[model_class_id].export_name
        else:
            if model_class_id not in {m.model_class_id for m in active}:
                return None
            export_id = export_id_for_model_class(class_mappings, model_class_id)
            export_name = export_name_for_model_class(class_mappings, model_class_id)
            if export_id is None or export_name is None:
                return None

        x1, y1, x2, y2 = box
        return Detection(
            model_class_id=model_class_id,
            class_id=export_id,
            class_name=export_name,
            confidence=confidence,
            x1=x1,
            y1=y1,
            x2=x2,
            y2=y2,
        )

    def predict(
        self,
        image_path: str | Path,
        class_mappings: list[ClassMapping],
        confidence: float = 0.25,
        iou: float = 0.45,
        tiled: bool = False,
        tile: int = 1024,
        overlap: float = 0.2,
        batch: int = 8,
        progress: Callable[[int, int], None] | None = None,
    ) -> list[Detection]:
        if not self.is_loaded:
            raise RuntimeError("Model not loaded.")

        active = [m for m in class_mappings if m.enabled]
        if not active:
            return []

        if self.supports_open_vocabulary():
            self.set_target_class_names([m.export_name for m in active])

        if tiled:
            raw = self._predict_tiled(
                image_path,
                confidence=confidence,
                iou=iou,
                tile=tile,
                overlap=overlap,
                batch=batch,
                progress=progress,
            )
            candidates = [
                (box.class_id, box.confidence, (box.x1, box.y1, box.x2, box.y2)) for box in raw
            ]
        else:
            candidates = self._predict_whole(image_path, confidence=confidence, iou=iou)

        detections: list[Detection] = []
        for model_class_id, conf, box in candidates:
            detection = self._to_detection(model_class_id, conf, box, class_mappings, active)
            if detection is not None:
                detections.append(detection)
        return detections

    def _predict_whole(
        self, image_path: str | Path, confidence: float, iou: float
    ) -> list[tuple[int, float, tuple[float, float, float, float]]]:
        results = self.model.predict(
            source=str(image_path),
            conf=confidence,
            iou=iou,
            verbose=False,
        )

        out: list[tuple[int, float, tuple[float, float, float, float]]] = []
        for result in results:
            boxes = result.boxes
            if boxes is None:
                continue
            for entry in boxes:
                x1, y1, x2, y2 = entry.xyxy[0].tolist()
                out.append((int(entry.cls.item()), float(entry.conf.item()), (x1, y1, x2, y2)))
        return out

    def _predict_tiled(
        self,
        image_path: str | Path,
        confidence: float,
        iou: float,
        tile: int,
        overlap: float,
        batch: int,
        progress: Callable[[int, int], None] | None,
    ) -> list[RawBox]:
        import numpy as np
        from PIL import Image

        Image.MAX_IMAGE_PIXELS = None
        with Image.open(image_path) as handle:
            frame = np.asarray(handle.convert("RGB"))

        return predict_tiled(
            self.model,
            frame,
            tile=tile,
            overlap=overlap,
            confidence=confidence,
            iou=iou,
            batch=batch,
            progress=progress,
        )

    def get_image_size(self, image_path: str | Path) -> tuple[int, int]:
        from PIL import Image

        Image.MAX_IMAGE_PIXELS = None
        with Image.open(image_path) as img:
            width, height = img.size
        return width, height
