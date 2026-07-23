# RAZOR Auto Labeler

**YOLO tabanlı nesne tespiti modelleriyle görüntüleri otomatik etiketleyen masaüstü uygulaması.**

RAZOR Auto Labeler, eğitilmiş bir YOLO modelini yükleyip binlerce görüntüyü tek tıkla etiketlemenizi sağlar. Roboflow uyumlu geniş format desteği sayesinde çıktılarınızı doğrudan eğitim pipeline'ınıza aktarabilirsiniz.

![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![PyQt6](https://img.shields.io/badge/GUI-PyQt6-green)
![License](https://img.shields.io/badge/License-MIT-yellow)

---

## Özellikler

- **YOLO model desteği** — `.pt`, `.onnx`, `.engine`, `.torchscript`, `.xml`, `.tflite`
- **Open-vocabulary modeller** — YOLO-World ile özel sınıf isimleri tanımlayabilme
- **Toplu işleme** — Klasör veya çoklu görüntü seçimi, arka planda etiketleme
- **Sınıf yönetimi** — Model sınıflarını yeniden adlandırma, filtreleme, devre dışı bırakma
- **Güven eşiği** — Confidence ayarı (0.05 – 1.0)
- **20+ export formatı** — YOLOv8/v9/v11/v12, COCO, Pascal VOC, CSV ve daha fazlası
- **Önizleme görüntüleri** — Etiketlenmiş bounding box'lar ile kayıt
- **Modern arayüz** — PyQt6 tabanlı koyu tema

---

## Desteklenen Export Formatları

| Grup | Formatlar |
|------|-----------|
| **TXT (YOLO)** | YOLO Darknet, YOLOv5/v7/v8/v9/v11/v12, YOLO26, OBB, CSV |
| **JSON** | COCO, COCO-MMDetection, CreateML, PaliGemma, Florence 2, OpenAI |
| **XML** | Pascal VOC |

Varsayılan format: **YOLOv11**

---

## Gereksinimler

- **Python 3.10** veya üzeri
- **Windows 10/11** (Linux/macOS'ta da çalışır; `run.bat` yerine `python main.py` kullanın)
- Eğitilmiş bir YOLO model dosyası (`.pt` önerilir)
- İsteğe bağlı: NVIDIA GPU + CUDA (daha hızlı inference için)

---

## Kurulum

### 1. Depoyu klonlayın

```bash
git clone https://github.com/cihancinoglu/razor-labeler.git
cd razor-labeler
```

### 2. Sanal ortam oluşturun (önerilir)

**Windows (PowerShell):**

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

**Linux / macOS:**

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Bağımlılıkları yükleyin

```bash
pip install -r requirements.txt
```

> **Not:** İlk çalıştırmada Ultralytics, PyTorch'u otomatik indirebilir. Bu işlem birkaç dakika sürebilir.

### 4. (İsteğe bağlı) Uygulama ikonunu oluşturun

```bash
python scripts/build_logo_ico.py
```

---

## Kullanım

### Hızlı başlangıç

**Windows:**

```bat
run.bat
```

**veya doğrudan:**

```bash
python main.py
```

### Adım adım

1. **Load Model** — Eğitilmiş YOLO modelinizi seçin (`.pt`, `.onnx`, vb.)
2. **Edit Classes** — Etiketlenecek sınıfları seçin, yeniden adlandırın veya devre dışı bırakın
3. **Load Images** veya **Load Folder** — Etiketlenecek görüntüleri yükleyin
4. **FORMAT** — Çıktı formatını seçin (varsayılan: YOLOv11)
5. **CONFIDENCE** — Minimum güven eşiğini ayarlayın
6. **Auto Label** — Etiketlemeyi başlatın; çıktı klasörünü seçin

### Çıktı yapısı

Etiketleme tamamlandığında seçtiğiniz klasörde:

```
output/
├── labels/          # Seçilen formatta etiket dosyaları
├── images/          # Bounding box'lu önizleme görüntüleri
├── data.yaml        # YOLO eğitimi için sınıf tanımları (YOLO formatları)
└── classes.txt      # Sınıf isimleri listesi
```

---

## Desteklenen Görüntü Formatları

`.jpg`, `.jpeg`, `.png`, `.bmp`, `.webp`, `.tif`, `.tiff`

---

## Proje Yapısı

```
razor-labeler/
├── main.py                 # Uygulama giriş noktası
├── requirements.txt        # Python bağımlılıkları
├── run.bat                 # Windows hızlı başlatma
├── assets/
│   └── logo.svg            # Uygulama logosu
├── scripts/
│   └── build_logo_ico.py   # .ico dosyası oluşturucu
└── src/
    ├── main_window.py      # Ana pencere ve UI
    ├── model_manager.py    # YOLO model yükleme ve inference
    ├── worker.py           # Arka plan etiketleme iş parçacığı
    ├── label_exporter.py   # Çoklu format export
    ├── export_formats.py   # Format tanımları
    ├── class_config.py     # Sınıf eşleme mantığı
    ├── class_selector.py   # Sınıf seçim diyalogu
    ├── add_class_dialog.py # Yeni sınıf ekleme (open-vocab)
    ├── splash.py           # Açılış ekranı
    └── theme.py            # UI teması
```

---

## Bağımlılıklar

| Paket | Amaç |
|-------|------|
| PyQt6 | Masaüstü arayüz |
| ultralytics | YOLO model inference |
| opencv-python | Görüntü işleme ve çizim |
| Pillow | Görüntü okuma |
| numpy | Sayısal işlemler |

---

## Sorun Giderme

| Sorun | Çözüm |
|-------|-------|
| `ModuleNotFoundError` | Sanal ortamın aktif olduğundan emin olun; `pip install -r requirements.txt` çalıştırın |
| Model yüklenmiyor | Dosya uzantısının desteklenen listede olduğunu kontrol edin |
| Yavaş etiketleme | GPU sürücüleri ve CUDA kurulu PyTorch kullanın |
| Boş etiket dosyaları | Confidence eşiğini düşürün veya sınıf filtrelerini kontrol edin |

---

## Lisans

Bu proje [MIT Lisansı](LICENSE) altında yayınlanmıştır.

---

## Sahip

**Cihan Cinoğlu**

---

## Sürüm Geçmişi

### v1.0.0 (2026-07-23)

- İlk kararlı sürüm
- YOLO tabanlı otomatik etiketleme
- 20+ export formatı desteği
- YOLO-World open-vocabulary desteği
- PyQt6 modern arayüz
