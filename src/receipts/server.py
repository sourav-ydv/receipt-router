from huggingface_hub import hf_hub_download

from . import config
from .api import create_app
from .pipeline import RateBudget, Router
from .student import Student
from .teacher import label, make_client


def resolve_model():
    if config.MODEL_PATH:
        return config.MODEL_PATH
    return hf_hub_download(repo_id=config.MODEL_REPO, filename=config.MODEL_FILE)


def build_router():
    student = Student(resolve_model())
    student.load()
    teacher = None
    if config.GROQ_API_KEY:
        client = make_client()
        teacher = lambda text: label(client, text)
    budget = RateBudget(config.MAX_TEACHER_CALLS_PER_HOUR)
    return Router(student, teacher, budget, config.ESCALATION_LOG or None)


app = create_app(build_router)
