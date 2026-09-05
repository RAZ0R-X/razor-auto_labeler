import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PyQt6.QtWidgets import QApplication  # noqa: E402
from PIL import Image  # noqa: E402

from src.class_config import ClassMapping  # noqa: E402
from src.dataset_splitter import assign_splits, group_key  # noqa: E402
from src.model_manager import Detection  # noqa: E402
from src.worker import LabelOptions, LabelWorker  # noqa: E402

failures = []


def check(label, condition, detail=""):
    print(f"[{'OK  ' if condition else 'FAIL'}] {label} {detail}")
    if not condition:
        failures.append(label)


app = QApplication.instance() or QApplication([])

MAPPINGS = [
    ClassMapping(0, "olgunlasmis", "olgunlasmis", True),
    ClassMapping(1, "olgunlasmamis", "olgunlasmamis", True),
]


class StubManager:
    """Stands in for a trained model: two boxes per frame, nothing on frame 7."""

    def __init__(self):
        self.calls = []

    def get_image_size(self, path):
        return (400, 300)

    def predict(self, path, mappings, **kwargs):
        self.calls.append((Path(path).name, kwargs))
        if Path(path).stem == "0007":
            return []
        return [
            Detection(0, 0, "olgunlasmis", 0.91, 10, 10, 60, 60),
            Detection(1, 1, "olgunlasmamis", 0.82, 100, 90, 160, 150),
        ]


# --- group keys -------------------------------------------------------------
check("tile ayni kaynakta grupland", group_key(Path("5401_r3c2.jpg")) == "5401")
check("blok gruplama", group_key(Path("0007.jpg"), block=4) == "block1")
check("blok=1 kendi adi", group_key(Path("0007.jpg"), block=1) == "0007")

for count, block in ((400, 4), (8651, 4), (300, 1), (997, 7)):
    paths = [Path(f"{i:04d}.jpg") for i in range(1, count + 1)]
    assignment = assign_splits(paths, block=block, seed=17)
    tally = {s: sum(1 for v in assignment.values() if v == s) for s in ("train", "valid", "test")}
    shares = {s: tally[s] / count for s in tally}
    target = {"train": 0.70, "valid": 0.20, "test": 0.10}
    drift = max(abs(shares[s] - target[s]) for s in target)
    check(
        f"{count} kare blok={block} oran 70/20/10",
        drift < 0.01 and sum(tally.values()) == count,
        f"{tally} sapma={drift * 100:.2f}%",
    )

    by_group = {}
    for path, split in assignment.items():
        by_group.setdefault(group_key(path, block), set()).add(split)
    check(f"{count} kare blok={block} grup bolunmedi", all(len(v) == 1 for v in by_group.values()))

# --- end to end -------------------------------------------------------------
workdir = Path(tempfile.mkdtemp(prefix="razor_verify_"))
images_dir = workdir / "kaynak"
images_dir.mkdir()
for i in range(1, 13):
    Image.new("RGB", (400, 300), (40 + i * 5, 90, 60)).save(images_dir / f"{i:04d}.jpg")
image_paths = sorted(images_dir.glob("*.jpg"))

out = workdir / "cikti"
manager = StubManager()
options = LabelOptions(
    export_format="YOLOv11",
    tiled=True,
    tile=512,
    overlap=0.25,
    skip_empty=True,
    resume=False,
    make_split=True,
    split_block=1,
)
worker = LabelWorker(manager, image_paths, out, MAPPINGS, options)

messages = []
worker.finished_ok.connect(messages.append)
worker.failed.connect(lambda m: messages.append(f"FAILED: {m}"))
worker._label()

check("hata yok", messages and not messages[0].startswith("FAILED"), messages[:1])
check("tiling parametreleri modele gecti", manager.calls[0][1].get("tiled") is True)
check("tile boyutu gecti", manager.calls[0][1].get("tile") == 512, f"{manager.calls[0][1]}")

labels = sorted(p.stem for p in (out / "labels").glob("*.txt"))
check("bos kare etiketlenmedi", "0007" not in labels, f"{len(labels)} etiket")
check("kalan 11 kare etiketlendi", len(labels) == 11, f"{labels}")

first = (out / "labels" / "0001.txt").read_text().strip().splitlines()
check("kare basina 2 kutu", len(first) == 2, f"{first}")
check("yolo satiri normalize", all(0.0 <= float(v) <= 1.0 for v in first[0].split()[1:]), first[0])

dataset = out / "dataset"
counts = {s: len(list((dataset / s / "images").glob("*.jpg"))) for s in ("train", "valid", "test")}
check("bolme toplami 11", sum(counts.values()) == 11, f"{counts}")
check("bos kare veri setine girmedi", not (dataset / "train" / "images" / "0007.jpg").exists())
for split in ("train", "valid", "test"):
    imgs = {p.stem for p in (dataset / split / "images").glob("*.jpg")}
    lbls = {p.stem for p in (dataset / split / "labels").glob("*.txt")}
    check(f"{split}: goruntu-etiket eslesmesi", imgs == lbls, f"{len(imgs)} vs {len(lbls)}")

yaml_text = (dataset / "data.yaml").read_text()
check("data.yaml siniflari", "olgunlasmis" in yaml_text and "nc: 2" in yaml_text)

linked = next((dataset / "train" / "images").glob("*.jpg"))
original = images_dir / linked.name
check(
    "hardlink kuruldu (disk iki katina cikmadi)",
    linked.stat().st_ino == original.stat().st_ino and linked.stat().st_ino != 0,
    f"ino {linked.stat().st_ino}",
)

# --- resume -----------------------------------------------------------------
manager2 = StubManager()
worker2 = LabelWorker(manager2, image_paths, out, MAPPINGS, options)
worker2.options.resume = True
worker2.options.make_split = False
worker2._label()
check(
    "resume etiketli kareleri atladi",
    len(manager2.calls) == 1 and manager2.calls[0][0] == "0007.jpg",
    f"{[c[0] for c in manager2.calls]}",
)

shutil.rmtree(workdir, ignore_errors=True)

print()
if failures:
    print(f"{len(failures)} test BASARISIZ: {failures}")
    raise SystemExit(1)
print("Tum testler gecti.")
