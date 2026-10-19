import json
import threading
import time
from collections import deque

from pydantic import BaseModel

from .schema import Receipt
from .validators import check, parse_receipt


class Result(BaseModel):
    receipt: Receipt | None
    source: str
    needs_review: bool
    problems: list[str]
    student_seconds: float
    teacher_called: bool


class RateBudget:
    def __init__(self, limit, window=3600.0, clock=time.time):
        self.limit = limit
        self.window = window
        self.clock = clock
        self.calls = deque()
        self.lock = threading.Lock()

    def take(self):
        now = self.clock()
        with self.lock:
            while self.calls and now - self.calls[0] > self.window:
                self.calls.popleft()
            if len(self.calls) >= self.limit:
                return False
            self.calls.append(now)
            return True


class Router:
    def __init__(self, student, teacher=None, budget=None, log_path=None):
        self.student = student
        self.teacher = teacher
        self.budget = budget
        self.log_path = log_path

    def extract(self, text):
        raw, seconds, _ = self.student(text)
        receipt = parse_receipt(raw)
        problems = ["unparseable"] if receipt is None else check(receipt)
        if not problems:
            return Result(
                receipt=receipt,
                source="student",
                needs_review=False,
                problems=[],
                student_seconds=seconds,
                teacher_called=False,
            )
        return self.escalate(text, raw, receipt, problems, seconds)

    def ask_teacher(self, text):
        if self.teacher is None:
            return False, None, None, []
        if self.budget is not None and not self.budget.take():
            return False, None, None, []
        try:
            raw, receipt, problems, _ = self.teacher(text)
        except Exception:
            return False, None, None, []
        return True, raw, receipt, problems or []

    def escalate(self, text, raw, receipt, problems, seconds):
        called, teacher_raw, teacher_receipt, teacher_problems = self.ask_teacher(text)
        self.log(text, raw, problems, called, teacher_raw, teacher_problems)

        if teacher_receipt is not None and not teacher_problems:
            return Result(
                receipt=teacher_receipt,
                source="teacher",
                needs_review=False,
                problems=[],
                student_seconds=seconds,
                teacher_called=called,
            )
        if teacher_receipt is not None:
            return Result(
                receipt=teacher_receipt,
                source="teacher",
                needs_review=True,
                problems=teacher_problems,
                student_seconds=seconds,
                teacher_called=called,
            )
        return Result(
            receipt=receipt,
            source="student",
            needs_review=True,
            problems=problems,
            student_seconds=seconds,
            teacher_called=called,
        )

    def log(self, text, raw, problems, called, teacher_raw, teacher_problems):
        if not self.log_path:
            return
        record = {
            "time": time.time(),
            "text": text,
            "student_raw": raw,
            "student_problems": problems,
            "teacher_called": called,
            "teacher_raw": teacher_raw,
            "teacher_problems": teacher_problems,
        }
        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
