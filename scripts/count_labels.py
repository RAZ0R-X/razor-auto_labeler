"""Report per-class box counts by reading the written YOLO label files.

Scanning the files is authoritative: a run that resumed earlier work would
otherwise only report the boxes it produced in that session.
"""

from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path


def read_class_names(data_yaml: Path) -> dict[int, str]:
    if not data_yaml.exists():
        return {}
    names: list[str] = []
    in_names = False
    for line in data_yaml.read_text(encoding="utf-8").splitlines():
        if line.startswith("names:"):
            in_names = True
            continue
        if in_names:
            stripped = line.strip()
            if stripped.startswith("- "):
                names.append(stripped[2:].strip())
            elif stripped:
                break
    return dict(enumerate(names))


def tally(labels_dir: Path) -> tuple[int, int, Counter[int]]:
    """Return (label files, empty files, per-class box counts)."""
    counts: Counter[int] = Counter()
    files = 0
    empty = 0
    for path in labels_dir.glob("*.txt"):
        files += 1
        found = 0
        for line in path.read_text(encoding="utf-8").splitlines():
            parts = line.split()
            if parts:
                try:
                    counts[int(parts[0])] += 1
                    found += 1
                except ValueError:
                    pass
        if found == 0:
            empty += 1
    return files, empty, counts


def report(title: str, labels_dir: Path, names: dict[int, str]) -> None:
    files, empty, counts = tally(labels_dir)
    total = sum(counts.values())
    print(f"\n{title}")
    print(f"  goruntu : {files}  ({empty} tanesi bos)")
    print(f"  kutu    : {total}")
    for class_id in sorted(counts):
        name = names.get(class_id, f"sinif {class_id}")
        share = 100 * counts[class_id] / total if total else 0
        print(f"    [{class_id}] {name:<22} {counts[class_id]:>7}  (%{share:.1f})")
    if files:
        print(f"  goruntu basina ortalama: {total / files:.1f} kutu")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path, help="labeling output folder")
    args = parser.parse_args()

    labels_dir = args.output / "labels"
    if not labels_dir.is_dir():
        print(f"Etiket klasoru yok: {labels_dir}")
        return 2

    names = read_class_names(args.output / "data.yaml")
    report("TOPLAM", labels_dir, names)

    dataset = args.output / "dataset"
    split_names = read_class_names(dataset / "data.yaml") or names
    for split in ("train", "valid", "test"):
        split_labels = dataset / split / "labels"
        if split_labels.is_dir():
            report(split.upper(), split_labels, split_names)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
