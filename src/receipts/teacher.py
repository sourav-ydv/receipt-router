import json
import time

from groq import APIConnectionError, Groq, RateLimitError
from .config import GROQ_API_KEY, GROQ_MODEL, TEACHER_REASONING
from .validators import check, parse_receipt

MAX_WAIT = 90

SYSTEM_PROMPT = """You extract structured data from receipt text produced by OCR. Reply with one JSON object and nothing else.

Fields:
- items: a list of {name, quantity, price, discount}
- subtotal, discount, service, tax, total: numbers or null

Rules:
- Numbers are plain numbers with no currency symbol and no thousands separator. On these Indonesian receipts 12.500 and 12,500 both mean 12500.
- price is the amount printed on the item's line, before that item's own discount.
- discount on an item is a positive number, or 0 when the item has none.
- quantity is a whole number. Use 1 when it is not printed or is fractional.
- Use null for a receipt-level field that is not printed. Never calculate a value that is not on the receipt.
- Keep item names exactly as printed."""

EXAMPLE_TEXT = """WARUNG BU SARI
Nasi Ayam 2 x 25.000 50.000
Es Teh 1 x 5.000 5.000
SUBTOTAL 55.000
PB1 10% 5.500
TOTAL 60.500"""

EXAMPLE_ANSWER = json.dumps(
    {
        "items": [
            {"name": "Nasi Ayam", "quantity": 2, "price": 50000, "discount": 0},
            {"name": "Es Teh", "quantity": 1, "price": 5000, "discount": 0},
        ],
        "subtotal": 55000,
        "discount": None,
        "service": None,
        "tax": 5500,
        "total": 60500,
    }
)


class DailyLimit(Exception):
    def __init__(self, wait):
        super().__init__(f"rate limited for {wait:.0f}s")
        self.wait = wait


def make_client():
    if not GROQ_API_KEY:
        raise SystemExit("GROQ_API_KEY is not set in .env")
    return Groq(api_key=GROQ_API_KEY, max_retries=0)


def retry_after(error):
    try:
        return float(error.response.headers.get("retry-after", 30))
    except (AttributeError, TypeError, ValueError):
        return 30.0


def build_messages(text):
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": EXAMPLE_TEXT},
        {"role": "assistant", "content": EXAMPLE_ANSWER},
        {"role": "user", "content": text},
    ]


def call_teacher(client, text):
    options = {}
    if TEACHER_REASONING:
        options["reasoning_effort"] = TEACHER_REASONING
    for attempt in range(5):
        try:
            response = client.chat.completions.create(
                model=GROQ_MODEL,
                messages=build_messages(text),
                temperature=0,
                max_completion_tokens=2000,
                **options,
            )
            usage = getattr(response, "usage", None)
            tokens = getattr(usage, "total_tokens", 0)
            return response.choices[0].message.content, tokens
        except RateLimitError as error:
            wait = retry_after(error)
            if wait > MAX_WAIT:
                raise DailyLimit(wait) from error
            time.sleep(wait + 1)
        except APIConnectionError:
            time.sleep(2**attempt)
    return None, 0


def label(client, text):
    raw, tokens = call_teacher(client, text)
    if not raw:
        return None, None, None, tokens
    receipt = parse_receipt(raw)
    problems = check(receipt) if receipt else ["unparseable"]
    return raw, receipt, problems, tokens