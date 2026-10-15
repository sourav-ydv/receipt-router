import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data"
PROCESSED_DIR = DATA_DIR / "processed"

DATASET_NAME = os.getenv("DATASET_NAME", "naver-clova-ix/cord-v2")
SEED = int(os.getenv("SEED", "42"))
