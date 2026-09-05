"""Cut annotation-ready tiles out of very large field photographs.

The source frames are up to 50 MP. A lentil pod that is ~60 px wide in the
original shrinks to ~6 px once YOLO rescales a full frame to its input size,
which is far too small to annotate or to learn from. Slicing fixed-size tiles
at native resolution keeps pods at their true size.

Tiles are filtered so that out-of-focus frames and patches of bare soil stay
out of the annotation set. Colour alone cannot do this, because dry soil and
ripe pods are almost the same brown; the deciding signal is coarse-scale
structure: a canopy keeps strong light/shadow contrast when heavily
downscaled, whereas soil blurs into a flat surface.
"""

from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

Image.MAX_IMAGE_PIXELS = None

IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png"}
GOLDEN_RATIO = 0.6180339887498949
COARSE_GRID = 64
LUMA = np.array([0.299, 0.587, 0.114], dtype=np.float32)


@dataclass
class Tile:
    source: Path
    row: int
    col: int
    x: int
    y: int
    size: int
    sharpness: float
    foliage: float
    texture: float
    shadow: float
    bright: float

    @property
    def name(self) -> str:
        return f"{self.source.stem}_r{self.row}c{self.col}.jpg"


def coarse_view(gray: np.ndarray, grid: int = COARSE_GRID) -> np.ndarray:
    """Block-mean downscale, used to measure structure rather than fine noise."""
    height, width = gray.shape
    block_h, block_w = height // grid, width // grid
    trimmed = gray[: block_h * grid, : block_w * grid]
    return trimmed.reshape(grid, block_h, grid, block_w).mean(axis=(1, 3))


def measure(patch: np.ndarray) -> tuple[float, float, float, float, float]:
    gray = patch @ LUMA

    laplacian = (
        gray[:-2, 1:-1]
        + gray[2:, 1:-1]
        + gray[1:-1, :-2]
        + gray[1:-1, 2:]
        - 4.0 * gray[1:-1, 1:-1]
    )

    channels = patch.astype(np.int16)
    red, green, blue = channels[..., 0], channels[..., 1], channels[..., 2]
    foliage = float(((green > red + 8) & (green > blue + 8)).mean())
    bright = float((channels.max(axis=2) > 175).mean())

    coarse = coarse_view(gray)
    shadow = float((coarse < 0.65 * coarse.mean()).mean()) if coarse.mean() > 0 else 0.0

    return float(laplacian.var()), foliage, float(coarse.std()), shadow, bright


def score_tiles(image: Image.Image, source: Path, size: int) -> list[Tile]:
    width, height = image.size
    frame = np.asarray(image)

    tiles: list[Tile] = []
    for row, y in enumerate(range(0, height - size + 1, size)):
        for col, x in enumerate(range(0, width - size + 1, size)):
            sharp, foliage, texture, shadow, bright = measure(frame[y : y + size, x : x + size])
            tiles.append(
                Tile(
                    source=source,
                    row=row,
                    col=col,
                    x=x,
                    y=y,
                    size=size,
                    sharpness=sharp,
                    foliage=foliage,
                    texture=texture,
                    shadow=shadow,
                    bright=bright,
                )
            )
    return tiles


def holds_plants(tile: Tile, min_texture: float, min_shadow: float, min_bright: float) -> bool:
    if tile.foliage >= 0.5:
        return True
    if tile.bright < min_bright:
        return False
    return tile.texture >= min_texture and tile.shadow >= min_shadow


def scan_order(paths: list[Path], first_index: int) -> list[Path]:
    """Golden-ratio ordering: any prefix stays evenly spread over the season.

    That matters because sources get skipped when they are blurred or bare, and
    the run stops as soon as the tile target is met.
    """
    pool = [p for p in paths if not p.stem.isdigit() or int(p.stem) >= first_index]
    if not pool:
        pool = paths

    ordered: list[Path] = []
    seen: set[int] = set()
    for i in range(len(pool)):
        index = int(((i * GOLDEN_RATIO) % 1.0) * len(pool))
        if index not in seen:
            seen.add(index)
            ordered.append(pool[index])
    ordered.extend(p for i, p in enumerate(pool) if i not in seen)
    return ordered


def write_contact_sheets(tiles: list[Tile], images_dir: Path, out_dir: Path) -> int:
    thumb, cols, rows = 300, 6, 5
    per_sheet = cols * rows
    try:
        font = ImageFont.load_default(size=18)
    except TypeError:
        font = ImageFont.load_default()

    sheets = 0
    for start in range(0, len(tiles), per_sheet):
        chunk = tiles[start : start + per_sheet]
        sheet = Image.new("RGB", (cols * thumb, rows * (thumb + 22)), "black")
        draw = ImageDraw.Draw(sheet)
        for position, tile in enumerate(chunk):
            with Image.open(images_dir / tile.name) as handle:
                preview = handle.convert("RGB").resize((thumb, thumb))
            cx = (position % cols) * thumb
            cy = (position // cols) * (thumb + 22)
            sheet.paste(preview, (cx, cy + 22))
            draw.text((cx + 4, cy + 2), tile.name, fill="yellow", font=font)
        sheet.save(out_dir / f"review_{start // per_sheet + 1:02d}.jpg", quality=85)
        sheets += 1
    return sheets


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--tiles", type=int, default=300)
    parser.add_argument("--per-image", type=int, default=2)
    parser.add_argument("--tile-size", type=int, default=1024)
    parser.add_argument(
        "--first-index",
        type=int,
        default=4400,
        help="Skip earlier frames, which are still at the vegetative stage.",
    )
    parser.add_argument("--min-sharpness", type=float, default=40.0)
    parser.add_argument("--min-texture", type=float, default=35.0)
    parser.add_argument("--min-shadow", type=float, default=0.12)
    parser.add_argument("--min-bright", type=float, default=0.10)
    parser.add_argument("--jpeg-quality", type=int, default=92)
    parser.add_argument("--no-sheets", action="store_true")
    args = parser.parse_args()

    paths = sorted(p for p in args.dataset.iterdir() if p.suffix.lower() in IMAGE_SUFFIXES)
    if not paths:
        raise SystemExit(f"No images found in {args.dataset}")

    images_dir = args.out / "images"
    images_dir.mkdir(parents=True, exist_ok=True)

    selected: list[Tile] = []
    skipped_blur = 0
    skipped_bare = 0

    for visited, source in enumerate(scan_order(paths, args.first_index), start=1):
        if len(selected) >= args.tiles:
            break

        with Image.open(source) as handle:
            image = handle.convert("RGB")

        usable = [
            t
            for t in score_tiles(image, source, args.tile_size)
            if holds_plants(t, args.min_texture, args.min_shadow, args.min_bright)
        ]
        if not usable:
            skipped_bare += 1
            image.close()
            continue

        usable.sort(key=lambda t: t.sharpness, reverse=True)
        if usable[0].sharpness < args.min_sharpness:
            skipped_blur += 1
            image.close()
            continue

        room = args.tiles - len(selected)
        for tile in usable[: min(args.per_image, room)]:
            crop = image.crop((tile.x, tile.y, tile.x + tile.size, tile.y + tile.size))
            crop.save(images_dir / tile.name, quality=args.jpeg_quality)
            selected.append(tile)
        image.close()

        print(
            f"[{len(selected):>4}/{args.tiles}] {source.name}  "
            f"sharp={usable[0].sharpness:7.0f}  visited={visited}",
            flush=True,
        )

    manifest = args.out / "manifest.csv"
    with manifest.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "tile",
                "source",
                "x",
                "y",
                "size",
                "sharpness",
                "foliage",
                "texture",
                "shadow",
                "bright",
            ]
        )
        for tile in sorted(selected, key=lambda t: t.name):
            writer.writerow(
                [
                    tile.name,
                    tile.source.name,
                    tile.x,
                    tile.y,
                    tile.size,
                    round(tile.sharpness, 1),
                    round(tile.foliage, 3),
                    round(tile.texture, 1),
                    round(tile.shadow, 3),
                    round(tile.bright, 3),
                ]
            )

    print(f"\n{len(selected)} tiles from {len({t.source for t in selected})} source photos")
    print(f"Skipped: {skipped_blur} blurred, {skipped_bare} bare")
    print(f"Images:   {images_dir}")
    print(f"Manifest: {manifest}")

    if not args.no_sheets:
        count = write_contact_sheets(sorted(selected, key=lambda t: t.name), images_dir, args.out)
        print(f"Review sheets: {count} file(s) in {args.out}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
