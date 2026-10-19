FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*

RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user PATH=/home/user/.local/bin:$PATH
WORKDIR /home/user/app

RUN pip install --no-cache-dir llama-cpp-python \
    --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cpu
RUN pip install --no-cache-dir fastapi uvicorn huggingface-hub groq pydantic python-dotenv
RUN pip install --no-cache-dir --no-deps git+https://github.com/sourav-ydv/receipt-router.git

EXPOSE 7860
CMD ["uvicorn", "receipts.server:app", "--host", "0.0.0.0", "--port", "7860"]
