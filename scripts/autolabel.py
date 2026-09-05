"""Run the auto-labeler over a folder without the GUI.

Uses the same LabelWorker the application does, so behaviour matches exactly,
but survives long unattended runs and writes a log that can be tailed.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PyQt6.QtCore import QCoreApplication  # noqa: E402

from src.class_config import build_mappings_from_model  # noqa: E402
from src.label_exporter import IMAGE_EXTENSIONS  # noqa: E402
from src.model_manager import ModelManager  # noqa: E402
from src.worker import LabelOptions, LabelWorker  # noqa: E402


def collect_images(dataset: Path, first_index: int, limit: int | None) -> list[Path]:
    paths = sorted(p for p in dataset.iterdir() if p.suffix.lower() in IMAGE_EXTENSIONS)
    if first_index > 0:
        paths = [p for p in paths if not p.stem.isdigit() or int(p.stem) >= first_index]
    return paths[:limit] if limit else paths


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", required=True, type=Path)
    parser.add_argument("--model", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--first-index", type=int, default=0)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--confidence", type=float, default=0.40)
    parser.add_argument("--iou", type=float, default=0.45)
    parser.add_argument("--tile", type=int, default=1024)
    parser.add_argument("--overlap", type=float, default=0.2)
    parser.add_argument("--batch", type=int, default=16)
    parser.add_argument("--format", default="YOLOv11")
    parser.add_argument("--split-block", type=int, default=4)
    parser.add_argument("--no-split", action="store_true")
    parser.add_argument("--no-resume", action="store_true")
    parser.add_argument("--keep-empty", action="store_true")
    args = parser.parse_args()

    QCoreApplication(sys.argv)

    manager = ModelManager()
    class_names = manager.load(args.model)
    print(f"Model: {args.model.name}")
    print(f"Siniflar: {class_names}")
    print(f"Cihaz: {ModelManager.device_label()}")

    images = collect_images(args.dataset, args.first_index, args.limit)
    if not images:
        print("Goruntu bulunamadi.", file=sys.stderr)
        return 2
    print(f"Goruntu: {len(images)} ({images[0].name} ... {images[-1].name})")

    options = LabelOptions(
        export_format=args.format,
        confidence=args.confidence,
        iou=args.iou,
        tiled=True,
        tile=args.tile,
        overlap=args.overlap,
        batch=args.batch,
        skip_empty=not args.keep_empty,
        resume=not args.no_resume,
        make_split=not args.no_split,
        split_block=args.split_block,
    )
    print(
        f"Ayarlar: conf={options.confidence} tile={options.tile} "
        f"overlap={options.overlap} batch={options.batch} "
        f"skip_empty={options.skip_empty} split={options.make_split}\n",
        flush=True,
    )

    worker = LabelWorker(manager, images, args.output, build_mappings_from_model(class_names), options)

    state = {"last": -1}

    def on_progress(percent: int, message: str) -> None:
        # The worker reports every frame; only surface whole percentage steps.
        if percent != state["last"]:
            state["last"] = percent
            print(f"  {percent:3d}%  {message}", flush=True)

    worker.progress.connect(on_progress)
    worker.finished_ok.connect(lambda text: print(f"\n{text}", flush=True))
    worker.failed.connect(lambda text: print(f"\nHATA: {text}", file=sys.stderr, flush=True))

    worker._label()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
