# receipt-router

Receipt text goes in and structured fields come out: line items, subtotal, tax, total. A small fine-tuned model does the reading. If its answer fails the checks, the receipt goes to a much bigger model. A decimal receipt that passes the checks stays with the small model.

Everything here ran on free tiers: Groq's free API for the big model, Kaggle's free GPU for training, and an ordinary laptop for inference. Nothing cost money.

## Headline numbers

Measured on 94 held-out receipts from CORD-v2. "Exact" means every extracted field matches the gold label.

| System | Exact match | Receipts answered without the big model |
|---|---|---|
| Big model (gpt-oss-120b) on every receipt | 61.7% | 0% |
| Mixed Q5 student | 68.1% | 100% |
| Mixed Q5 student plus the current router | 68.1% | 83% |

The mixed student is the file the server downloads. The current checks pass 78 of these 94 answers and send 16 to the big model. Two of those 16 big-model answers pass the same checks. Exact match stays 64 of 94 either way. With 94 receipts, 68.1% against the big model's 61.7% is about six receipts, which this report treats as noise. The router is not ahead of the student on Indonesian receipts. The rupiah-only arithmetic run, 62.8% for that student and 64.9% for that router, is in the results section. Four of the 94 looked decimal to the detector. The answers in this table were produced with the Indonesian instruction.

## Three things I found

1. Checking the big model's labels with arithmetic rules matters. Its answers that pass the checks are right far more often than the rest (81% exact against 62% overall), so I trained the small model only on the ones that pass.
2. Sending hard receipts back to the big model and training on them did not beat training on random receipts. That experiment is in the feedback loop section.
3. On Malaysian receipts, where prices look like `9.00`, the rupiah-only student got 12.7% of totals right and the arithmetic checks accepted 59 of 65 wrong answers. A second student, trained on both kinds of receipt, got 88.7% of those totals right. With the current checks, 0 of the 67 answers it passed had the wrong total.

The numbers come from the files in `results/` and from the scripts in `scripts/`. The mixed CORD rescore and the Malaysian tally are in `results/mixed/`. The Malaysian receipt text is not redistributed here.

## How it works

### Data

CORD-v2 from Hugging Face (`naver-clova-ix/cord-v2`): photos of Indonesian receipts with annotations, split 800 train, 100 validation, 100 test. I use the annotation lines, joined into plain text, as the input. A real deployment would get text from an OCR engine. I did not test that, so the numbers describe reading clean text, not reading photos.

29 of the 800 training receipts and 6 of the 100 test receipts are unusable (no total, or items without names) and are left out.

Each receipt becomes a small schema: a list of items (name, quantity, price, discount) plus subtotal, discount, service, tax and total.

### The checks

A few rules decide whether an answer looks believable:

- the item prices (minus item discounts) add up to the subtotal, or to the total on tax-inclusive receipts
- subtotal, minus discount, plus service, plus tax equals the total
- when the subtotal is missing and a tax is filled in, including a tax of zero, the items have to reach the total on their own or with the tax added. On a decimal receipt the price may be a unit price, so the quantity counts. A rupiah price is already the line total, so the quantity is not applied again
- there is a total, at least one item, and no blank item names
- when the receipt text is available, every non-zero amount also has to match a number printed on the page. `9.00` read as `900` fails this, because `900` is not on the page. Zero and null do not have to be printed
- a decimal total above one billion, or a rupiah total above one hundred billion, is rejected

The page is read as Indonesian when amounts look like `50.000`, and as decimal when they look like `9.00` or the text says RM or MYR. One dot-thousands group keeps the page Indonesian even if a stray `9.00` is also there.

Rounding tolerance is 0.05% of the total, with a floor of 1 on Indonesian receipts and 0.01 on decimal ones. On the usable training receipts, the gold labels themselves pass the arithmetic rules on 730 of 771 (94.7%). The rest are annotation quirks. I did not bend the rules to fit them. Training still filters on the checks that existed when the file was built. The later "items must reach the total" rule is used on live answers.

### The big model (teacher)

`openai/gpt-oss-120b` through Groq's free tier, with one worked example in the prompt. The first prompt misread tax lines as discounts and item-count lines as item names, so I rewrote it. On the same 94 test receipts, exact match went from 39.4% to 59.6% and tax from 77.7% to 96.8%. Those numbers were taken before I fixed a bug in how I parsed the gold labels, which later moved the second prompt to 61.7%.

I wrote the second prompt after reading the first one's errors on the test split, so the test score is a little optimistic. I also ran it on the validation split, which I had not looked at: 66.7% exact, and about 82% of answers passed the checks.

There is a separate prompt for decimal amounts. It says `9.00` means 9 and `1,234.50` means 1234.50, and its worked example is a small decimal receipt. I used it to label the decimal training receipts. I have not scored the teacher itself on the 150 held-out SROIE receipts.

### The small model (student)

`Qwen2.5-1.5B-Instruct`, fine-tuned with QLoRA (rank 16) using Unsloth on a free Kaggle T4. Three epochs take 6 to 8 minutes.

The first student was trained on the big model's labels for the CORD training receipts: 590 passed the checks, 770 could be parsed. The deployed file on Hugging Face is still that model, quantized to Q5_K_M. Its instruction is one line, "Extract the receipt fields as JSON.", and it only saw rupiah text.

The second student was trained on those 590 Indonesian receipts plus 129 checked decimal receipts. Each example carries the instruction for its own locale. The Indonesian one says `12.500` means 12500. The decimal one says `9.00` means 9. The service now sends that same instruction, chosen from the text. The Q5 file from this run is what the server downloads, under the name `Qwen2.5-1.5B-Instruct-mixed.Q5_K_M.gguf`. The rupiah-only Q5 file is still in that repo under its original name.

### Router and service

The student answers first. Its answer is kept when the checks pass, on an Indonesian receipt and on a decimal one. A failing decimal receipt still goes to the big model on its own.

The drift window still watches the last 20 receipts and still trips when the rejection rate or the share of two-digit decimals moves away from the CORD baseline. The escalation log records that. The alarm no longer overrides an answer that passes the checks. It used to, because arithmetic alone accepted totals that were 100 times too big.

A cap on big-model calls per hour keeps a public demo from using up the free quota. If the big model is missing, over budget, or its answer still fails, the student answer is returned and marked for review. The service is a small FastAPI app:

```
python -m uvicorn receipts.server:app --port 8000
```

There is no live demo. On Hugging Face's free tier, Docker and CPU Spaces are paid, and the free option is a GPU-sharing Space that does not fit a CPU model.

### Layout

- `src/receipts/` the library: schema, parsing, checks, teacher client, router, API
- `scripts/` data preparation, labeling, scoring, comparison and report scripts
- `notebooks/` Kaggle notebooks for training, quantizing and the feedback experiment
- `results/` the raw results of the experiments

## Results

### Big model and small model

94 test receipts. This is the rupiah-only student.

| | Big model | Small model, trained on checked labels (590) | Small model, trained on all labels (770) |
|---|---|---|---|
| Exact match | 61.7% | 66.0% | 62.8% |
| Items F1 | 86.4% | 88.7% | 84.8% |
| Answers that pass the checks | 74.5% | 85.1% | 76.6% |

The paired differences are small next to the noise: checked student minus big model is +4.3 points (interval -5.3 to +13.8), and checked minus unchecked is +3.2 (interval -5.3 to +11.7). So I cannot say the small model beats the big one, and I did not show that filtering improves exact match. The one clear sign for filtering is how often the answers pass the checks, 85% against 77%, which matters because the router depends on it.

The "pass the checks" row is arithmetic only, from before amounts had to match the printed text.

### Shrinking it for CPU

| File | Size | Exact match | Median seconds per receipt |
|---|---|---|---|
| Q4_K_M | 0.99 GB | 56.4% | 7.2 |
| Q5_K_M | 1.13 GB | 62.8% | 9.1 |
| Q8_0 | 1.65 GB | 61.7% | 9.8 |

Speeds are from Kaggle's 4 CPU threads. Q4 lost 9.6 points against the unquantized model (interval -18.1 to 0.0), which is probably real. Q5 and Q8 cannot be told apart, so I deployed Q5_K_M. On my own Windows laptop the sample receipt took about 7 seconds. A free Hugging Face Space has only 2 cores, so expect it to be slower there.

This table is the rupiah-only student. The mixed Q5 file is the same size, 1.13 GB, and took a median 10.0 seconds on the same 4 threads.

### The router

I simulated the router on the same 94 receipts using the real big-model answers. With the rupiah-only Q5 student it reaches 64.9% exact, sends 18 of 94 receipts to the big model, and uses 22% of the big model's tokens compared with sending everything. Against the big model alone that is +3.2 points (interval -4.3 to +10.6).

That simulation used the arithmetic checks. An answer with a wrong item name or quantity but consistent totals passes. Among the answers the rupiah-only Q5 student passed, 76% were exact, not 100%.

## Does sending hard receipts back make the student better?

The idea: whenever the router escalates a receipt, the big model's answer (if it passes the checks) becomes a new training example. Over time the student should get better at exactly the receipts it found hard.

To test it I started from about 115 random training receipts and trained a student. The remaining receipts arrived in 4 batches of about 155. Each round, the current student answered a batch, the receipts that failed the checks counted as escalated, their checked big-model labels were added, and I retrained from scratch and measured. The control added the same number of random receipts from the same batch instead.

Exact match on 190 receipts the student never trains on (the test and validation splits), averaged over two seeds:

| Round | Escalated receipts added | Random receipts added |
|---|---|---|
| 0 (about 116 training receipts) | 50.8% | 50.8% |
| 1 | 53.4% | 54.7% |
| 2 | 50.0% | 53.4% |
| 3 | 56.8% | 56.8% |
| 4 (about 195 training receipts) | 57.1% | 57.9% |

![exact match against training receipts](docs/feedback_curve.png)

Escalated minus random is -0.8 points in the last round (interval -3.4 to +1.8) and -1.4 across rounds 2 to 4 (interval -3.0 to +0.2). The interval leaves out the variation between training runs, and the two seeds disagree in sign (+1.1 and -2.6), so the real uncertainty is wider than it looks. A first run with a third seed, scored on 94 test receipts only, had shown +4.3 points for escalation. That did not hold up.

Two side findings. Both arms gain about 6 points from roughly 116 to 195 training receipts, so more data helps whichever way it is chosen. And only about half of the escalated receipts get a big-model label that passes the checks (44% in the first run, against 77% for training receipts in general), because receipts the small model struggles with are hard for the big model too.

My conclusion: the loop gives you training data as a free by-product of routing, and the student improves with more of it. At this scale, choosing the escalated receipts did not beat choosing at random.

## What happens on a different kind of receipt

I ran the rupiah-only Q5 student on 150 receipts from SROIE, Malaysian receipts where prices look like `9.00`. That student only ever saw Indonesian ones, where a dot is a thousands separator (`25.000`). SROIE gives only the total, so only the total is scored.

| | CORD test (training domain) | SROIE (new domain) |
|---|---|---|
| Receipts | 94 | 150 |
| Total correct | 98.9% | 12.7% |
| Total off by a factor of 100 | 0% | 43.3% |
| Wrong or missing in another way | 1.1% | 44.0% |
| Rejected by the checks | 19.1% | 56.7% |
| Passed the checks but total wrong | 0 of 76 | 59 of 65 |

The last row is the important one for that model. On the new receipts the arithmetic checks accepted 65 answers, and 59 of them had the wrong total. A total that is consistently 100 times too big still adds up, so arithmetic cannot see it. One accepted answer had a total of 60 billion.

Looking at the totals more closely (see `results/drift/errors.txt`): 65 were off by exactly 100, 38 by exactly 1000, 23 in some other way, 19 were right and 5 could not be parsed. The student reads `9.00` as 900, which is what it learned from the rupiah receipts.

### After training on both kinds of receipt

The mixed student is the same base model, trained for 3 epochs on 719 examples: the 590 checked CORD receipts and 129 checked SROIE receipts. The other 150 SROIE receipts were held out and never entered training. Validation loss on the Indonesian validation split fell from 0.013 to 0.005. The run took about 8 minutes on a T4.

On the 94 CORD test receipts, the Q5 file scored 68.1% exact and 89.7% item F1, with the total right on 98.9%. The rupiah-only Q5 file scored 62.8% exact. The arithmetic checks passed 80 of 94. The current checks pass 78 of 94 and send 16 to the big model, and exact match stays 68.1%. The tally and the saved answers are in `results/mixed/`. The median time was 10.0 seconds. The unquantized mixed run scored 63.8% exact, so this quantization did not cost accuracy. A few receipts on a set of 94 is the same size of gap the rest of this report treats as noise. I am not claiming the mixed student is better on CORD. The CORD score held.

On the 150 held-out SROIE receipts, scored with the current checks:

| | Rupiah-only Q5 | Mixed Q5 |
|---|---|---|
| Receipts | 150 | 150 |
| Total correct | 12.7% | 88.7% |
| Total off by a factor of 100 | 43.3% | 0% |
| Wrong or missing in another way | 44.0% | 11.3% |
| Passed the checks | 65, arithmetic only | 67, current checks |
| Passed but total wrong | 59 of 65 | 0 of 67 |

The pass counts use different checks, so they are not a direct comparison. The last row is. Of the 150 mixed answers, 67 pass and would stay with the student, and all 67 totals are right. The other 83 fail and go to the big model. 66 of those 83 have the right total anyway: the items, the tax, or a printed number did not line up, so the checker refused an answer it could not add up. 148 of the 150 were given the decimal instruction. Two looked Indonesian to the detector and got the rupiah instruction.

### Noticing it without labels

Two signals that need no gold labels, each compared with the first half of the CORD test receipts over a rolling window of 20:

- the share of receipts the checks reject: 19% on CORD, 57% on the rupiah-only SROIE run. It fired after 23 SROIE receipts.
- the share of lines with two-digit decimals, an input feature: it fired after 20 SROIE receipts, which is the earliest a window of 20 allows.

Neither raised a false alarm on the second half of the CORD receipts. So the rejection rate is a poor safety net on a new domain but a good alarm.

The same window still runs inside the service, and an escalation records whether it has tripped. It no longer sends a passing answer to the big model. A decimal page that fails the checks still goes to the big model before the window fills.

On my laptop the rupiah-only SROIE run was slower than CORD: median 14.9 seconds, 95th percentile 34.4, maximum 99.2. Those receipts are longer, so the model writes more.

Caveats: 150 receipts, only the total is scored, and SROIE differs from CORD in layout and line order as well as in number format. The mixed pass rate depends on the current checks. The old column does not.

## Limits

- The test set is small. 94 receipts means a few points of noise, and every comparison above says so in its interval.
- The input is clean annotation text, not OCR output. I did not measure the gap.
- I wrote the second teacher prompt after reading test-split errors. I checked it on validation, but the test numbers for the big model are a little optimistic.
- The feedback experiment has two seeds with the full evaluation and one more with a smaller one.
- The drift test is one dataset, one student, 150 receipts, and scores only the total.
- The headline is the mixed Q5 file with the current checks. The rupiah-only arithmetic table is kept under Results.
- The server downloads the mixed Q5 file. The rupiah-only Q4, Q5, and Q8 files remain in the Hugging Face repo under their original names.
- Free tiers set the shape of the project: the big-model labels came from Groq's free quota, training from Kaggle's weekly GPU hours, and there is no live demo.

## What I would do next

- Re-run `scripts/drift_report.py` once the new predictions are in `data/`, and keep that output next to the table.
- Rerun the feedback loop on decimal receipts. On CORD, choosing escalated receipts did not beat choosing at random.
- Run a real OCR engine on the receipt photos and measure what it costs in accuracy.
- Get more test receipts so the intervals shrink.

## Running it

```
pip install -e ".[dev,data,serve]"
pip install llama-cpp-python --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cpu
pytest
python scripts/prepare_data.py
```

The big-model labeling needs a free Groq key in `.env` (see `.env.example`). Training and quantizing run in the Kaggle notebooks in `notebooks/`. The quantized model that the server downloads today is on Hugging Face at `sourav-ydv25/receipt-student-gguf`.

## Credits

Data: CORD-v2 and SROIE (used for evaluation only, not redistributed here). Models: Qwen2.5-1.5B-Instruct and gpt-oss-120b. Tooling: Unsloth, llama.cpp, Hugging Face, Kaggle, Groq.