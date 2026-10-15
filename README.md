# receipt-router

Trying to replace expensive LLM API calls for receipt extraction with a small model I fine-tune myself, and a router that sends hard receipts back to the API.

Work in progress. Nothing runs end to end yet.

## Setup

```
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
python scripts/prepare_data.py
```

On Windows, activate with `.venv\Scripts\activate` instead.
