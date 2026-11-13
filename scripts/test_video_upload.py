"""
Test video upload of ~10MB video to ROADVISION AI backend
"""
import os
import cv2
import numpy as np
import requests
import time

# Create a 10MB dummy road inspection video (100 frames, 1280x720)
test_vid_path = "data/uploads/test_10mb_sample.mp4"
width, height = 1280, 720
fps = 25
fourcc = cv2.VideoWriter_fourcc(*'mp4v')
out = cv2.VideoWriter(test_vid_path, fourcc, fps, (width, height))

print("Generating synthetic 10MB road inspection video...")
# Generate frames simulating asphalt road with moving potholes
for i in range(120):
    frame = np.full((height, width, 3), 60, dtype=np.uint8) # Dark asphalt
    # Add road lane markings
    cv2.line(frame, (width//2, 0), (width//2, height), (255, 255, 255), 8)
    # Add road defect/pothole
    pothole_y = (100 + i * 4) % (height - 100)
    cv2.ellipse(frame, (width//2 - 120, pothole_y), (60, 35), 0, 0, 360, (20, 20, 20), -1)
    # Add texture noise
    noise = np.random.randint(-15, 15, (height, width, 3), dtype=np.int16)
    frame = np.clip(frame.astype(np.int16) + noise, 0, 255).astype(np.uint8)
    out.write(frame)

out.release()
fsize = os.path.getsize(test_vid_path) / (1024 * 1024)
print(f"Generated video size: {fsize:.2f} MB ({test_vid_path})")

# Test upload to backend
print("Uploading video to http://127.0.0.1:8000/api/inspect/video...")
t0 = time.time()
try:
    with open(test_vid_path, "rb") as f:
        res = requests.post(
            "http://127.0.0.1:8000/api/inspect/video",
            files={"file": ("test_10mb_sample.mp4", f, "video/mp4")},
            data={
                "road_name": "NH-48 Expressway",
                "road_type": "Highway",
                "speed_limit": 80,
                "stride": 3
            },
            timeout=120
        )
    dt = time.time() - t0
    print(f"Response status: {res.status_code} in {dt:.2f} seconds")
    print(f"Response body preview: {res.text[:300]}")
except Exception as e:
    print(f"Upload failed: {e}")
