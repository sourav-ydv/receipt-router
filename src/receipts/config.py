import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data"
PROCESSED_DIR = DATA_DIR / "processed"
TEACHER_DIR = DATA_DIR / "teacher"

DATASET_NAME = os.getenv("DATASET_NAME", "naver-clova-ix/cord-v2")
SEED = int(os.getenv("SEED", "42"))

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
TEACHER_REASONING = os.getenv("TEACHER_REASONING", "")
TEACHER_PAUSE = float(os.getenv("TEACHER_PAUSE", "14"))