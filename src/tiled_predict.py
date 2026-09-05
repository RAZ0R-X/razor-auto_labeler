"""Sliced inference for photographs much larger than the model input size.

A 6144x8192 field photo rescaled to a 640 px network input shrinks a 60 px
lentil pod down to roughly 6 px, which no detector can find. Cutting the frame
into overlapping tiles at native resolution keeps objects at their true size;
the per-tile boxes are then mapped back to full-frame coordinates and merged.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Iterable, Sequence

import numpy as np


@dataclass(frozen=True)
class TilePlan:
    x: int
    y: int
    width: int
    height: int

    @property
    def right(self) -> int:
        return self.x + self.width

    @property
    def bottom(self) -> int:
        return self.y + self.height


@dataclass
class RawBox:
    class_id: int
    confidence: float
    x1: float
    y1: float
    x2: float
    y2: float


def _offsets(total: int, tile: int, step: int) -> list[int]:
    if total <= tile:
        return [0]
    positions = list(range(0, total - tile + 1, step))
    if positions[-1] + tile < total:
        positions.append(total - tile)
    return positions


def plan_tiles(width: int, height: int, tile: int, overlap: float) -> list[TilePlan]:
    """Lay out overlapping tiles, shifting the last one inwards to reach the edge."""
    tile = max(64, int(tile))
    overlap = min(max(float(overlap), 0.0), 0.9)
    step = max(1, int(round(tile * (1.0 - overlap))))

    tile_w, tile_h = min(tile, width), min(tile, height)
    return [
        TilePlan(x, y, tile_w, tile_h)
        for y in _offsets(height, tile_h, step)
        for x in _offsets(width, tile_w, step)
    ]


def non_max_suppression(
    boxes: np.ndarray, scores: np.ndarray, threshold: float
) -> list[int]:
    order = scores.argsort()[::-1]
    x1, y1, x2, y2 = boxes[:, 0], boxes[:, 1], boxes[:, 2], boxes[:, 3]
    areas = (x2 - x1).clip(0) * (y2 - y1).clip(0)

    keep: list[int] = []
    while order.size:
        current = int(order[0])
        keep.append(current)
        if order.size == 1:
            break

        rest = order[1:]
        inter_w = (np.minimum(x2[current], x2[rest]) - np.maximum(x1[current], x1[rest])).clip(0)
        inter_h = (np.minimum(y2[current], y2[rest]) - np.maximum(y1[current], y1[rest])).clip(0)
        inter = inter_w * inter_h
        iou = inter / (areas[current] + areas[rest] - inter + 1e-9)
        order = rest[iou <= threshold]
    return keep


def merge_boxes(raw: Sequence[RawBox], merge_iou: float) -> list[RawBox]:
    """Class-wise suppression of the duplicates produced by overlapping tiles."""
    if len(raw) < 2:
        return list(raw)

    kept: list[RawBox] = []
    for class_id in {box.class_id for box in raw}:
        group = [box for box in raw if box.class_id == class_id]
        coords = np.array([[b.x1, b.y1, b.x2, b.y2] for b in group], dtype=np.float32)
        scores = np.array([b.confidence for b in group], dtype=np.float32)
        kept.extend(group[i] for i in non_max_suppression(coords, scores, merge_iou))

    kept.sort(key=lambda b: b.confidence, reverse=True)
    return kept


def _touches_inner_edge(
    box: RawBox, tile: TilePlan, width: int, height: int, margin: float
) -> bool:
    """True when a box runs into a tile seam, meaning the object is cut in half.

    With enough overlap the same object is fully inside a neighbouring tile, so
    dropping the truncated copy is safer than trying to stitch it back together.
    """
    if tile.x > 0 and box.x1 - tile.x <= margin:
        return True
    if tile.y > 0 and box.y1 - tile.y <= margin:
        return True
    if tile.right < width and tile.right - box.x2 <= margin:
        return True
    if tile.bottom < height and tile.bottom - box.y2 <= margin:
        return True
    return False


def _chunks(items: Sequence[TilePlan], size: int) -> Iterable[Sequence[TilePlan]]:
    for start in range(0, len(items), size):
        yield items[start : start + size]


def predict_tiled(
    model,
    frame: np.ndarray,
    *,
    tile: int = 1024,
    overlap: float = 0.2,
    confidence: float = 0.25,
    iou: float = 0.45,
    batch: int = 8,
    merge_iou: float = 0.5,
    drop_cut_boxes: bool = True,
    edge_margin: float = 2.0,
    device: str | int | None = None,
    progress: Callable[[int, int], None] | None = None,
) -> list[RawBox]:
    """Run the model over overlapping tiles of an RGB frame.

    Returns boxes in full-frame pixel coordinates.
    """
    height, width = frame.shape[:2]
    plans = plan_tiles(width, height, tile, overlap)
    collected: list[RawBox] = []
    done = 0

    for chunk in _chunks(plans, max(1, batch)):
        # Ultralytics reads raw arrays as BGR, while the frame arrives as RGB.
        crops = [
            np.ascontiguousarray(
                frame[plan.y : plan.bottom, plan.x : plan.right][:, :, ::-1]
            )
            for plan in chunk
        ]

        predict_args = {
            "source": crops,
            "conf": confidence,
            "iou": iou,
            "imgsz": tile,
            "verbose": False,
        }
        if device is not None:
            predict_args["device"] = device

        for plan, result in zip(chunk, model.predict(**predict_args)):
            boxes = result.boxes
            if boxes is None:
                continue
            for entry in boxes:
                x1, y1, x2, y2 = (float(v) for v in entry.xyxy[0].tolist())
                box = RawBox(
                    class_id=int(entry.cls.item()),
                    confidence=float(entry.conf.item()),
                    x1=x1 + plan.x,
                    y1=y1 + plan.y,
                    x2=x2 + plan.x,
                    y2=y2 + plan.y,
                )
                if drop_cut_boxes and _touches_inner_edge(box, plan, width, height, edge_margin):
                    continue
                collected.append(box)

        done += len(chunk)
        if progress is not None:
            progress(done, len(plans))

    return merge_boxes(collected, merge_iou)
