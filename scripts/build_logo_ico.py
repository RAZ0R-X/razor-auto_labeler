from pathlib import Path
from PIL import Image

ASSETS = Path(__file__).resolve().parent.parent / "assets"

img = Image.open(ASSETS / "logo_256.png")

img.save(
    ASSETS / "logo.ico",
    format="ICO",
    sizes=[(16,16), (32,32), (48,48), (64,64), (128,128), (256,256)]
)

print("logo.ico oluşturuldu.")
