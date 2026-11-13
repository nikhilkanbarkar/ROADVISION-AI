"""
ROADVISION AI - Model Downloader and Candidate Research
Searches and downloads candidate Road Damage Detection (RDD2022) models.
"""
import os
import sys
import json
import urllib.request
import urllib.error

MODELS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "models")
PRIMARY_DIR = os.path.join(MODELS_DIR, "primary")
ALT_DIR = os.path.join(MODELS_DIR, "alternative")
BENCHMARK_DIR = os.path.join(MODELS_DIR, "benchmark")

os.makedirs(PRIMARY_DIR, exist_ok=True)
os.makedirs(ALT_DIR, exist_ok=True)
os.makedirs(BENCHMARK_DIR, exist_ok=True)

CANDIDATES = [
    {
        "id": "keremberke/yolov8n-pothole-segmentation",
        "name": "YOLOv8n-Pothole-Seg",
        "arch": "YOLOv8n-seg",
        "url": "https://huggingface.co/keremberke/yolov8n-pothole-segmentation/resolve/main/best.pt",
        "filename": "keremberke_yolov8n_pothole.pt",
        "classes": ["pothole"],
        "dataset": "Pothole Segmentation Dataset",
        "published_map50": 0.842,
        "license": "MIT"
    },
    {
        "id": "Ryukijano/Pothole-detection-yolov8",
        "name": "YOLOv8-Pothole-Detection",
        "arch": "YOLOv8s",
        "url": "https://huggingface.co/Ryukijano/Pothole-detection-yolov8/resolve/main/best.pt",
        "filename": "ryukijano_yolov8_pothole.pt",
        "classes": ["pothole"],
        "dataset": "Pothole Detection Dataset",
        "published_map50": 0.815,
        "license": "Apache-2.0"
    },
    {
        "id": "dronefreak/rdd2022-yolov8s",
        "name": "YOLOv8s-RDD2022",
        "arch": "YOLOv8s",
        "url": "https://huggingface.co/dronefreak/rdd2022-yolov8s/resolve/main/best.pt",
        "filename": "dronefreak_rdd2022_yolov8s.pt",
        "classes": ["D00", "D10", "D20", "D40"],
        "dataset": "RDD2022 Multi-Country Road Damage",
        "published_map50": 0.728,
        "license": "CC-BY-4.0"
    },
    {
        "id": "dronefreak/rdd2022-yolov8m",
        "name": "YOLOv8m-RDD2022",
        "arch": "YOLOv8m",
        "url": "https://huggingface.co/dronefreak/rdd2022-yolov8m/resolve/main/best.pt",
        "filename": "dronefreak_rdd2022_yolov8m.pt",
        "classes": ["D00", "D10", "D20", "D40"],
        "dataset": "RDD2022 Multi-Country Road Damage",
        "published_map50": 0.756,
        "license": "CC-BY-4.0"
    }
]

def download_file(url, destination, timeout=15):
    print(f"Attempting download: {url} -> {destination}")
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            total_size = int(response.info().get('Content-Length', -1))
            chunk_size = 1024 * 64
            downloaded = 0
            with open(destination, 'wb') as f:
                while True:
                    chunk = response.read(chunk_size)
                    if not chunk:
                        break
                    f.write(chunk)
                    downloaded += len(chunk)
            print(f"Downloaded successfully: {downloaded} bytes ({downloaded/(1024*1024):.2f} MB)")
            return True
    except Exception as e:
        print(f"Download failed: {e}")
        if os.path.exists(destination):
            try:
                os.remove(destination)
            except Exception:
                pass
        return False

def setup_weights():
    downloaded_any = False
    for candidate in CANDIDATES:
        dest = os.path.join(ALT_DIR, candidate["filename"])
        if not os.path.exists(dest):
            ok = download_file(candidate["url"], dest, timeout=12)
            if ok:
                downloaded_any = True

    # Save candidates metadata
    meta_path = os.path.join(MODELS_DIR, "models_metadata.json")
    with open(meta_path, "w") as f:
        json.dump(CANDIDATES, f, indent=2)
    print(f"Saved candidates metadata to {meta_path}")

if __name__ == "__main__":
    setup_weights()
