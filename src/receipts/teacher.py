import json
import time

from groq import APIConnectionError, Groq, RateLimitError
from .config import GROQ_API_KEY, GROQ_MODEL, TEACHER_REASONING
from .drift import detect_locale
from .validators import check, parse_receipt

MAX_WAIT = 90

NUMBER_RULE_IDR = (
    "Numbers are plain numbers with no currency symbol and no thousands separator. "
    "On these Indonesian receipts 12.500 and 12,500 both mean 12500."
)
NUMBER_RULE_DECIMAL = (
    "Numbers are plain numbers with no currency symbol and no thousands separator. "
    "A separator followed by exactly two digits is the decimal point: 9.00 means 9 "
    "and 1,234.50 means 1234.50. Do not multiply a printed amount by 100 or 1000."
)

PROMPT = """You extract structured data from receipt text produced by OCR. Reply with one JSON object and nothing else.

Fields:
- items: a list of {name, quantity, price, discount}
- subtotal, discount, service, tax, total: numbers or null

Rules:
- __NUMBER_RULE__
- Copy each item name exactly as printed, including trailing words or numbers. Lines such as "ITEMS 2" or "QTY 3" only count items and are not item names.
- price is the amount printed for the item's line, before that item's own discount.
- quantity is a whole number. It may be printed before the item name, after it, or as "2 x 25.000". A line holding only a small whole number right before an item name is that item's quantity. Use 1 only when no quantity is printed.
- tax is the tax line: PB1, PB-1, PPN, PAJAK, TAX or VAT. Never put it in discount.
- service is a service charge line such as SERVICE or SVC.
- discount is only a reduction of the bill (DISC, DISKON, POTONGAN, or an amount shown with a minus sign). On an item use a positive number, or 0 when the item has none.
- Use null for a receipt-level field that is not printed. Never calculate a value that is not on the receipt."""

EXAMPLE_TEXT = """WARUNG BU SARI
2
Nasi Ayam
50.000
1
Es Teh
5.000
ITEMS 2
SUBTTL 55.000
PB-1 10% 5.500
TOTAL 60.500
CASH 100.000"""

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

EXAMPLE_TEXT_DECIMAL = """KEDAI MAJU
Pen
9.00
Pencil
1.50
SUBTOTAL 10.50
TAX 0.60
TOTAL 11.10"""

EXAMPLE_ANSWER_DECIMAL = json.dumps(
    {
        "items": [
            {"name": "Pen", "quantity": 1, "price": 9, "discount": 0},
            {"name": "Pencil", "quantity": 1, "price": 1.5, "discount": 0},
        ],
        "subtotal": 10.5,
        "discount": None,
        "service": None,
        "tax": 0.6,
        "total": 11.1,
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


def prompt_for(locale):
    rule = NUMBER_RULE_DECIMAL if locale == "decimal" else NUMBER_RULE_IDR
    return PROMPT.replace("__NUMBER_RULE__", rule)


def build_messages(text, locale=None):
    if locale is None:
        locale = detect_locale(text)
    if locale == "decimal":
        example_text = EXAMPLE_TEXT_DECIMAL
        example_answer = EXAMPLE_ANSWER_DECIMAL
    else:
        locale = "idr"
        example_text = EXAMPLE_TEXT
        example_answer = EXAMPLE_ANSWER
    return [
        {"role": "system", "content": prompt_for(locale)},
        {"role": "user", "content": example_text},
        {"role": "assistant", "content": example_answer},
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
    locale = detect_locale(text)
    problems = check(receipt, text=text, locale=locale) if receipt else ["unparseable"]
    return raw, receipt, problems, tokens

def cord_tasks(rows):
    return [
        {"id": i, "text": row["text"]}
        for i, row in enumerate(rows)
        if row["usable"] and row.get("text")
    ]


def file_tasks(rows):
    return [{"id": row["id"], "text": row["text"]} for row in rows if row.get("text")]


def remaining(rows, done_ids, limit=None):
    done = set(done_ids)
    todo = [row for row in rows if row["id"] not in done]
    if limit:
        return todo[:limit]
    return todo