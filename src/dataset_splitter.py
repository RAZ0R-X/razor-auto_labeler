"""Write auto-labeled results out as a YOLO train/valid/test dataset.

Uses Roboflow's default 70/20/10 ratios so the result lines up with datasets
generated there.

Two details matter for the split to be honest:

* Frames are assigned in groups, never individually. Field photos are shot in
  sequence, so neighbouring frames can show the same plant; if they land in
  different splits the model effectively sees the test set during training and
  the reported score is meaningless.
* Images are hard-linked rather than copied. The source set runs to tens of
  gigabytes and a copy would double that for no benefit.
"""

from __future__ import annotations

import os
import random
import shutil
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

from src.label_exporter import write_data_yaml

ROBOFLOW_RATIOS: dict[str, float] = {"train": 0.70, "valid": 0.20, "test": 0.10}
SPLIT_ORDER = ("train", "valid", "test")


@dataclass
class SplitReport:
    counts: dict[str, int] = field(default_factory=dict)
    groups: int = 0
    linked: int = 0
    copied: int = 0
    data_yaml: Path | None = None

    def summary(self) -> str:
        parts = [f"{name}={self.counts.get(name, 0)}" for name in SPLIT_ORDER]
        return f"{' '.join(parts)} ({self.groups} groups)"


def group_key(path: Path, block: int = 1) -> str:
    """Identify frames that must not be separated.

    Tiles carry their source frame in the name (``5401_r3c2``), so they collapse
    onto that frame. Plain sequential frames are bucketed into blocks of
    ``block`` so that a burst of near-identical shots stays together.
    """
    stem = path.stem
    if "_r" in stem:
        head = stem.split("_r")[0]
        if head:
            stem = head
    if block > 1 and stem.isdigit():
        return f"block{int(stem) // block}"
    return stem


def assign_splits(
    paths: list[Path],
    block: int = 1,
    seed: int = 17,
    ratios: dict[str, float] | None = None,
) -> dict[Path, str]:
    ratios = ratios or ROBOFLOW_RATIOS

    groups: dict[str, list[Path]] = defaultdict(list)
    for path in paths:
        groups[group_key(path, block)].append(path)

    keys = sorted(groups)
    random.Random(seed).shuffle(keys)

    # Groups rarely hold the same number of frames, so slicing the group list by
    # ratio skews the image counts. Handing each group to whichever split is
    # furthest below its target keeps the ratios close without splitting groups.
    targets = {name: ratios[name] * len(paths) for name in SPLIT_ORDER}
    filled = {name: 0 for name in SPLIT_ORDER}

    assignment: dict[Path, str] = {}
    for key in keys:
        members = groups[key]
        split = max(SPLIT_ORDER, key=lambda name: targets[name] - filled[name])
        for path in members:
            assignment[path] = split
        filled[split] += len(members)
    return assignment


def _place(source: Path, target: Path) -> bool:
    """Hard-link when possible, fall back to copying. True if a link was made."""
    if target.exists():
        return False
    try:
        os.link(source, target)
        return True
    except OSError:
        shutil.copy2(source, target)
        return False


def write_split_dataset(
    image_paths: list[Path],
    label_source: Path,
    output_dir: Path,
    class_names: dict[int, str],
    block: int = 1,
    seed: int = 17,
) -> SplitReport:
    """Lay out ``output_dir/{split}/{images,labels}`` plus ``data.yaml``.

    ``label_source`` holds the generated ``.txt`` files, named after the images.
    Images without a label file are skipped, which is what keeps frames holding
    no detections out of the dataset.
    """
    labelled = [p for p in image_paths if (label_source / f"{p.stem}.txt").exists()]
    assignment = assign_splits(labelled, block=block, seed=seed)

    report = SplitReport(groups=len({group_key(p, block) for p in labelled}))
    for split in SPLIT_ORDER:
        (output_dir / split / "images").mkdir(parents=True, exist_ok=True)
        (output_dir / split / "labels").mkdir(parents=True, exist_ok=True)
        report.counts[split] = 0

    for image_path in labelled:
        split = assignment[image_path]
        if _place(image_path, output_dir / split / "images" / image_path.name):
            report.linked += 1
        else:
            report.copied += 1
        shutil.copy2(
            label_source / f"{image_path.stem}.txt",
            output_dir / split / "labels" / f"{image_path.stem}.txt",
        )
        report.counts[split] += 1

    report.data_yaml = write_data_yaml(class_names, output_dir)
    return report
