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
