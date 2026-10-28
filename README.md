# receipt-router

Receipt text goes in and structured fields come out: line items, subtotal, tax, total. A small fine-tuned model does the reading. If its answer fails simple arithmetic checks, the receipt goes to a much bigger model instead.

Everything here ran on free tiers: Groq's free API for the big model, Kaggle's free GPU for training, and an ordinary laptop for inference. Nothing cost money.

## Headline numbers

Measured on 94 held-out receipts from CORD-v2. "Exact" means every extracted field matches the gold label.

| System | Exact match | Receipts answered without the big model |
|---|---|---|
| Big model (gpt-oss-120b) on every receipt | 61.7% | 0% |
| Small model, 4-bit file for CPU (Q5_K_M) | 62.8% | 100% |
| Small model plus router | 64.9% | 81% |

With 94 receipts none of these gaps is statistically meaningful (router vs big model: +3.2 points, interval -4.3 to +10.6). What the numbers do support is narrower: the small model is in the same range as the big one, and the router uses about 22% of the big model's tokens.

## Three things I found

1. Checking the big model's labels with arithmetic rules matters. Its answers that pass the checks are right far more often than the rest (81% exact against 62% overall), so I trained the small model only on the ones that pass.
2. Sending hard receipts back to the big model and training on them did not beat training on random receipts. That experiment is in the feedback loop section.
3. On a different kind of receipt (Malaysian, prices written like 9.00) the small model's total accuracy fell from 99% to 13%, and the arithmetic checks accepted most of the wrong answers. A monitor that needs no labels noticed the change after about 20 receipts.

The numbers come from the files in `results/` and from the scripts in `scripts/`.

## How it works

### Data

CORD-v2 from Hugging Face (`naver-clova-ix/cord-v2`): photos of Indonesian receipts with annotations, split 800 train, 100 validation, 100 test. I use the annotation lines, joined into plain text, as the input. A real deployment would get text from an OCR engine. I did not test that, so the numbers describe reading clean text, not reading photos.

29 of the 800 training receipts and 6 of the 100 test receipts are unusable (no total, or items without names) and are left out.

Each receipt becomes a small schema: a list of items (name, quantity, price, discount) plus subtotal, discount, service, tax and total.

### The checks

A few arithmetic rules decide whether an answer looks believable:

- the item prices (minus item discounts) add up to the subtotal, or to the total on tax-inclusive receipts
- subtotal, minus discount, plus service, plus tax equals the total
- there is a total, at least one item, and no blank item names

I allow a small tolerance (0.05% of the total) for rounding. On the usable training receipts, the gold labels themselves pass 730 of 771 (94.7%). The rest are annotation quirks. I did not bend the rules to fit them.

### The big model (teacher)

`openai/gpt-oss-120b` through Groq's free tier, with one worked example in the prompt. The first prompt misread tax lines as discounts and item-count lines as item names, so I rewrote it. On the same 94 test receipts, exact match went from 39.4% to 59.6% and tax from 77.7% to 96.8%. Those numbers were taken before I fixed a bug in how I parsed the gold labels, which later moved the second prompt to 61.7%.

I wrote the second prompt after reading the first one's errors on the test split, so the test score is a little optimistic. I also ran it on the validation split, which I had not looked at: 66.7% exact, and about 82% of answers passed the checks.

### The small model (student)

`Qwen2.5-1.5B-Instruct`, fine-tuned with QLoRA (rank 16) using Unsloth on a free Kaggle T4. Three epochs take 6 to 8 minutes. The training data is the big model's labels on the 771 labeled training receipts: 590 passed the checks, 770 could be parsed. I trained one student on each set to see whether the filtering helps.

### Router and service

The student answers first. If the answer fails the checks, the receipt goes to the big model. A cap on big-model calls per hour keeps a public demo from using up the free quota. The service is a small FastAPI app:

```
python -m uvicorn receipts.server:app --port 8000
```

There is no live demo. On Hugging Face's free tier, Docker and CPU Spaces are paid, and the free option is a GPU-sharing Space that does not fit a CPU model.

### Layout

- `src/receipts/` the library: schema, parsing, checks, teacher client, router, API
- `scripts/` data preparation, labeling, scoring, comparison and report scripts
- `notebooks/` Kaggle notebooks for training, quantizing and the feedback experiment
- `results/` the raw results of the experiments
