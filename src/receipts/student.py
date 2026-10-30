import os
import threading
import time

from .drift import detect_locale
from .formatting import instruction_for


class Student:
    def __init__(self, path, threads=None, context=4096):
        self.path = path
        self.threads = threads or os.cpu_count()
        self.context = context
        self.llm = None
        self.lock = threading.Lock()

    def load(self):
        from llama_cpp import Llama

        self.llm = Llama(
            model_path=self.path,
            n_ctx=self.context,
            n_threads=self.threads,
            verbose=False,
        )

    def messages(self, text):
        return [
            {"role": "system", "content": instruction_for(detect_locale(text))},
            {"role": "user", "content": text},
        ]

    def __call__(self, text):
        if self.llm is None:
            self.load()
        with self.lock:
            started = time.time()
            reply = self.llm.create_chat_completion(
                messages=self.messages(text),
                temperature=0,
                max_tokens=800,
            )
            seconds = time.time() - started
        return (
            reply["choices"][0]["message"]["content"],
            seconds,
            reply["usage"]["completion_tokens"],
        )