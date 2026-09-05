"""Create the Roboflow project and upload annotation tiles into it.

Splits are decided here rather than by Roboflow, because two tiles cut from the
same source photograph show the same plants. Letting them land in different
splits would leak training data into validation and inflate the reported mAP,
so tiles are grouped by source frame and whole groups are assigned to a split.

The API key is read from the ROBOFLOW_API_KEY environment variable; it is never
written to disk or into the project files.
"""

from __future__ import annotations

import argparse
import os
import random
import sys
from collections import defaultdict
from pathlib import Path

ROBOFLOW_RATIOS = {"train": 0.70, "valid": 0.20, "test": 0.10}


def group_by_source(tiles: list[Path]) -> dict[str, list[Path]]:
    groups: dict[str, list[Path]] = defaultdict(list)
    for tile in tiles:
        groups[tile.stem.split("_r")[0]].append(tile)
    return dict(groups)


def assign_splits(groups: dict[str, list[Path]], seed: int) -> dict[Path, str]:
    keys = sorted(groups)
    random.Random(seed).shuffle(keys)

    train_end = round(len(keys) * ROBOFLOW_RATIOS["train"])
    valid_end = train_end + round(len(keys) * ROBOFLOW_RATIOS["valid"])

    assignment: dict[Path, str] = {}
    for position, key in enumerate(keys):
        if position < train_end:
            split = "train"
        elif position < valid_end:
            split = "valid"
        else:
            split = "test"
        for tile in groups[key]:
            assignment[tile] = split
    return assignment


def get_or_create_project(workspace, project_id: str, annotation_group: str):
    try:
        project = workspace.project(project_id)
        print(f"Using existing project: {project_id}")
        return project
    except Exception:
        pass

    print(f"Creating project: {project_id}")
    created = workspace.create_project(
        project_name=project_id,
        project_type="object-detection",
        project_license="MIT",
        annotation=annotation_group,
    )
    if isinstance(created, (list, tuple)):
        created = created[0]
    # Newly created projects are not always returned as a usable handle.
    try:
        return workspace.project(project_id)
    except Exception:
        return created


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tiles-dir", required=True, type=Path)
    parser.add_argument("--project", default="mercimek-olgunluk")
    parser.add_argument("--annotation-group", default="mercimek")
    parser.add_argument("--batch-name", default="tohum-seti")
    parser.add_argument("--seed", type=int, default=17)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    api_key = os.environ.get("ROBOFLOW_API_KEY")
    if not api_key:
        print("ROBOFLOW_API_KEY is not set.", file=sys.stderr)
        return 2

    tiles = sorted(p for p in args.tiles_dir.glob("*.jpg"))
    if not tiles:
        print(f"No tiles found in {args.tiles_dir}", file=sys.stderr)
        return 2

    groups = group_by_source(tiles)
    assignment = assign_splits(groups, args.seed)

    tally: dict[str, int] = defaultdict(int)
    for split in assignment.values():
        tally[split] += 1
    print(f"{len(tiles)} tiles from {len(groups)} source photos")
    for split in ("train", "valid", "test"):
        share = tally[split] / len(tiles) * 100
        print(f"  {split:5s}: {tally[split]:4d} tiles ({share:.0f}%)")

    if args.dry_run:
        print("\nDry run, nothing uploaded.")
        return 0

    from roboflow import Roboflow

    workspace = Roboflow(api_key=api_key).workspace()
    project = get_or_create_project(workspace, args.project, args.annotation_group)

    failures: list[str] = []
    for position, tile in enumerate(tiles, start=1):
        try:
            project.upload(
                str(tile),
                split=assignment[tile],
                batch_name=args.batch_name,
                num_retry_uploads=3,
            )
        except Exception as exc:
            failures.append(f"{tile.name}: {exc}")
            print(f"[{position}/{len(tiles)}] FAILED {tile.name}: {exc}", flush=True)
            continue

        if position % 10 == 0 or position == len(tiles):
            print(f"[{position}/{len(tiles)}] uploaded", flush=True)

    print(f"\nUploaded {len(tiles) - len(failures)}/{len(tiles)} tiles")
    if failures:
        print(f"{len(failures)} failure(s):")
        for line in failures[:20]:
            print(f"  {line}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
