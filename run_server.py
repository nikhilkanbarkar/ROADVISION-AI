"""
ROADVISION AI - Production Server Launcher
Initializes the database, checks model checkpoints, and launches Uvicorn.
"""
import os
import sys
import uvicorn

# Ensure project root is in python path
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from backend.config import HOST, PORT, PRIMARY_MODEL_PATH
from backend.database import init_db

def main():
    print("=" * 60)
    print("  ROADVISION AI - Intelligent Road Infrastructure Platform")
    print("  'Detect Road Damage. Predict Risk. Prioritize Repairs.'")
    print("=" * 60)

    # 1. Initialize SQLite Database
    print("\n[1/3] Initializing persistent database...")
    init_db()

    # 2. Verify Models
    print("[2/3] Checking primary RDD2022 model weights...")
    if os.path.exists(PRIMARY_MODEL_PATH):
        print(f"  Found primary model: {PRIMARY_MODEL_PATH}")
    else:
        print(f"  WARNING: Primary model not found at {PRIMARY_MODEL_PATH}")

    # 3. Launch Server
    print(f"[3/3] Starting web server on http://{HOST}:{PORT}")
    print(f"  Frontend Dashboard: http://{HOST}:{PORT}/")
    print(f"  REST API Docs:      http://{HOST}:{PORT}/docs")
    print("=" * 60)
    print("Press Ctrl+C to stop the server.\n")

    uvicorn.run("backend.app:app", host=HOST, port=PORT, reload=False, access_log=True)

if __name__ == "__main__":
    main()
