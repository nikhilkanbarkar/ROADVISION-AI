"""
ROADVISION AI - Phase 2: Candidate Models Downloader
Downloads weights for researched candidate models from Hugging Face into models/alternative/
"""
import os
import urllib.request

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ALT_DIR = os.path.join(ROOT_DIR, "models", "alternative")
os.makedirs(ALT_DIR, exist_ok=True)

CANDIDATES_TO_DOWNLOAD = [
    {
        "id": "keremberke/yolov8m-pothole-segmentation",
        "url": "https://huggingface.co/keremberke/yolov8m-pothole-segmentation/resolve/main/best.pt",
        "filename": "keremberke_yolov8m_pothole_seg.pt"
    },
    {
        "id": "keremberke/yolov8s-pothole-segmentation",
        "url": "https://huggingface.co/keremberke/yolov8s-pothole-segmentation/resolve/main/best.pt",
        "filename": "keremberke_yolov8s_pothole_seg.pt"
    },
    {
        "id": "Th3Samaritan/rdd2022-yolo11s",
        "url": "https://huggingface.co/Th3Samaritan/rdd2022-yolo11s/resolve/main/best.pt",
        "filename": "th3samaritan_rdd2022_yolo11s.pt"
    },
    {
        "id": "Harisanth/Pothole-Finetuned-YOLOv8",
        "url": "https://huggingface.co/Harisanth/Pothole-Finetuned-YOLOv8/resolve/main/best.pt",
        "filename": "harisanth_yolov8_pothole.pt"
    },
    {
        "id": "RohithGangarapu/PotholeYolov8",
        "url": "https://huggingface.co/RohithGangarapu/PotholeYolov8/resolve/main/best.pt",
        "filename": "rohith_yolov8_pothole.pt"
    },
    {
        "id": "nehaMe123/yolov8-road-damage-detector",
        "url": "https://huggingface.co/nehaMe123/yolov8-road-damage-detector/resolve/main/best.pt",
        "filename": "neha_rdd_yolov8.pt"
    }
]

def download_candidates():
    headers = {'User-Agent': 'Mozilla/5.0'}
    for c in CANDIDATES_TO_DOWNLOAD:
        dest = os.path.join(ALT_DIR, c["filename"])
        if os.path.exists(dest) and os.path.getsize(dest) > 1000000:
            print(f"Skipping {c['filename']} (already downloaded, {os.path.getsize(dest)/(1024*1024):.1f} MB)")
            continue

        print(f"Downloading {c['id']} -> {c['filename']}...")
        req = urllib.request.Request(c["url"], headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = resp.read()
                with open(dest, "wb") as f:
                    f.write(data)
                print(f"  Successfully downloaded {len(data)/(1024*1024):.2f} MB")
        except Exception as e:
            print(f"  Failed to download {c['id']}: {e}")
            if os.path.exists(dest):
                os.remove(dest)

if __name__ == "__main__":
    download_candidates()
