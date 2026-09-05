"""Time sliced inference on a real frame to size up a full-dataset run."""

import argparse
import sys
import time
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.tiled_predict import plan_tiles, predict_tiled  # noqa: E402

Image.MAX_IMAGE_PIXELS = None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image", required=True, type=Path)
    parser.add_argument("--model", default="yolo11m.pt")
    parser.add_argument("--tile", type=int, default=1024)
    parser.add_argument("--overlap", type=float, default=0.2)
    parser.add_argument("--batches", type=int, nargs="+", default=[2, 4, 8])
    parser.add_argument("--total-images", type=int, default=8651)
    args = parser.parse_args()

    import torch
    from ultralytics import YOLO

    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Cihaz: {device}")
    if device == "cuda":
        print(f"GPU: {torch.cuda.get_device_name(0)}")

    decode_start = time.time()
    with Image.open(args.image) as handle:
        frame = np.asarray(handle.convert("RGB"))
    decode = time.time() - decode_start

    height, width = frame.shape[:2]
    tiles = len(plan_tiles(width, height, args.tile, args.overlap))
    print(f"\nGoruntu: {width}x{height} ({width * height / 1e6:.0f} MP)")
    print(f"JPEG cozme: {decode:.2f} sn")
    print(f"Parca sayisi: {tiles} ({args.tile}px, %{args.overlap * 100:.0f} ortusme)\n")

    model = YOLO(args.model)
    print(f"{'batch':>6} {'cikarim':>9} {'kare/sn':>8} {'kutu':>6}   {args.total_images} kare icin")
    print("-" * 62)

    for batch in args.batches:
        try:
            predict_tiled(model, frame, tile=args.tile, overlap=args.overlap, batch=batch)
            if device == "cuda":
                torch.cuda.synchronize()

            start = time.time()
            boxes = predict_tiled(model, frame, tile=args.tile, overlap=args.overlap, batch=batch)
            if device == "cuda":
                torch.cuda.synchronize()
            inference = time.time() - start
        except RuntimeError as exc:
            reason = "bellek yetmedi" if "out of memory" in str(exc).lower() else str(exc)[:40]
            print(f"{batch:>6}  {reason}")
            if device == "cuda":
                torch.cuda.empty_cache()
            continue

        per_image = decode + inference
        total_hours = per_image * args.total_images / 3600
        print(
            f"{batch:>6} {inference:8.2f}s {per_image:7.2f}s {len(boxes):>6}   "
            f"{total_hours:.1f} saat"
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
