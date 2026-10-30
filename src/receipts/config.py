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

MODEL_PATH = os.getenv("MODEL_PATH", "")
MODEL_REPO = os.getenv("MODEL_REPO", "sourav-ydv25/receipt-student-gguf")
MODEL_FILE = os.getenv("MODEL_FILE", "Qwen2.5-1.5B-Instruct-mixed.Q5_K_M.gguf")
MAX_TEACHER_CALLS_PER_HOUR = int(os.getenv("MAX_TEACHER_CALLS_PER_HOUR", "30"))
MAX_INPUT_CHARS = int(os.getenv("MAX_INPUT_CHARS", "8000"))
ESCALATION_LOG = os.getenv("ESCALATION_LOG", "")