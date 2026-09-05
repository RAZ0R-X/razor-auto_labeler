import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.tiled_predict import (  # noqa: E402
    RawBox,
    TilePlan,
    merge_boxes,
    plan_tiles,
    predict_tiled,
)

failures = []


def check(label, condition, detail=""):
    status = "OK  " if condition else "FAIL"
    print(f"[{status}] {label} {detail}")
    if not condition:
        failures.append(label)


# --- tile layout ---
plans = plan_tiles(6144, 8192, 1024, 0.2)
check("6144x8192 -> 80 tile", len(plans) == 80, f"got {len(plans)}")

covered = np.zeros((8192, 6144), dtype=bool)
for p in plans:
    covered[p.y : p.bottom, p.x : p.right] = True
check("tam kaplama", covered.all(), f"kapsanmayan={int((~covered).sum())} px")

check("son tile sag kenara yetisiyor", max(p.right for p in plans) == 6144)
check("son tile alt kenara yetisiyor", max(p.bottom for p in plans) == 8192)

small = plan_tiles(500, 400, 1024, 0.2)
check("kucuk goruntu -> 1 tile", len(small) == 1 and small[0].width == 500, f"{small}")

exact = plan_tiles(2048, 2048, 1024, 0.0)
check("ortusmesiz 2048 -> 4 tile", len(exact) == 4, f"got {len(exact)}")

# --- merging ---
same = [RawBox(0, 0.9, 10, 10, 60, 60), RawBox(0, 0.7, 12, 12, 62, 62)]
merged = merge_boxes(same, 0.5)
check("ayni nesnenin kopyasi birlesti", len(merged) == 1 and merged[0].confidence == 0.9)

different_class = [RawBox(0, 0.9, 10, 10, 60, 60), RawBox(1, 0.7, 12, 12, 62, 62)]
check("farkli sinif birlesmedi", len(merge_boxes(different_class, 0.5)) == 2)

far_apart = [RawBox(0, 0.9, 10, 10, 60, 60), RawBox(0, 0.8, 500, 500, 560, 560)]
check("ayri nesneler korundu", len(merge_boxes(far_apart, 0.5)) == 2)

check("bos giris", merge_boxes([], 0.5) == [])


# --- end to end plumbing with a stub model ---
class StubResult:
    class Boxes:
        def __init__(self, rows):
            self._rows = rows

        def __iter__(self):
            for cls, conf, xyxy in self._rows:
                yield type(
                    "B",
                    (),
                    {
                        "cls": type("V", (), {"item": lambda s, c=cls: c})(),
                        "conf": type("V", (), {"item": lambda s, c=conf: c})(),
                        "xyxy": [type("T", (), {"tolist": lambda s, v=xyxy: v})()],
                    },
                )()

    def __init__(self, rows):
        self.boxes = self.Boxes(rows)


class StubModel:
    """Puts one box dead centre of every tile, plus one glued to the left seam."""

    def __init__(self):
        self.seen = 0

    def predict(self, source, **kwargs):
        out = []
        for _ in source:
            self.seen += 1
            out.append(StubResult([(0, 0.9, [500, 500, 540, 540]), (0, 0.8, [0, 200, 30, 240])]))
        return out


frame = np.zeros((2048, 2048, 3), dtype=np.uint8)
stub = StubModel()
boxes = predict_tiled(stub, frame, tile=1024, overlap=0.0, batch=4, drop_cut_boxes=True)
check("stub 4 tile gordu", stub.seen == 4, f"seen={stub.seen}")

coords = sorted((int(b.x1), int(b.y1)) for b in boxes)
centres = [c for c in coords if c[0] in (500, 1524)]
check("her tile merkez kutusunu verdi", len(centres) == 4, f"{centres}")
check(
    "kutular global koordinata tasindi",
    centres == [(500, 500), (500, 1524), (1524, 500), (1524, 1524)],
    f"{centres}",
)

# The stub also emits a box glued to each tile's left edge. For the x=0 column
# that edge is the real image border, so those must survive; for x=1024 it is a
# seam between tiles and the truncated copy must be dropped.
seam = [c for c in coords if c[0] == 1024]
border = [c for c in coords if c[0] == 0]
check("dikisteki kesik kutular atildi", seam == [], f"{seam}")
check("goruntu kenarindaki kutular korundu", border == [(0, 200), (0, 1224)], f"{border}")

stub2 = StubModel()
kept_all = predict_tiled(stub2, frame, tile=1024, overlap=0.0, batch=4, drop_cut_boxes=False)
check("drop_cut_boxes=False daha fazla kutu tutuyor", len(kept_all) > len(boxes), f"{len(kept_all)}")

print()
if failures:
    print(f"{len(failures)} test BASARISIZ: {failures}")
    raise SystemExit(1)
print("Tum testler gecti.")
