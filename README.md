# Code-Switched Intent Classifier (Hinglish / Tanglish)

An intent classifier for code-mixed Indian customer-support text — Hindi-English (Hinglish) and Tamil-English (Tanglish) written in Roman script — built on **MuRIL**, served via **FastAPI**, containerised with **Docker**, and judged by a **real evaluation harness** rather than a single accuracy number.

---

## The problem

Real Indian users don't type clean English into support chats. They type things like:

- `mera order kahan hai bhai` (Hinglish)
- `enaku refund venum` (Tanglish)
- `payment ho gaya but order confirm nahi hua`
- `cancel pannunga please`

An off-the-shelf English NLU model breaks on this. The grammar is mixed, the vocabulary spans two languages, and most of the tokens aren't English words at all — they're Hindi or Tamil written in the Latin alphabet, so the model has never seen them in this form. Word boundaries and morphology don't match what an English tokenizer expects.

**Intent classification** here means: take one user utterance and map it to exactly one of a small, fixed set of intents (plus a catch-all). That's the whole job — no slot-filling, no generation, no dialogue state. One sentence in, one label out.

### Intent set (v1 — to be finalised)

| Intent | Example |
|---|---|
| `greeting` | "hi bro", "hello anna" |
| `check_order_status` | "mera order kahan hai" |
| `track_delivery` | "kab tak ayega delivery" |
| `request_refund` | "enaku refund venum" |
| `cancel_order` | "cancel pannunga please" |
| `payment_issue` | "paisa cut gaya but order nahi hua" |
| `complaint` | "product damaged aaya yaar" |
| `talk_to_agent` | "kisi insaan se baat karni hai" |
| `other` | anything outside the above (the reject class) |

The `other` class matters. A classifier that confidently labels every garbage input as *something* is worse than useless in production. Handling "I don't know" well is part of the point.

---

## Why this project (portfolio rationale)

- **It's a genuinely hard, India-specific problem.** Code-switching is the norm here, not the exception, and most published NLU work quietly assumes monolingual clean text.
- **MuRIL is the right tool, and using it shows that.** It's Google's encoder trained on 17 Indian languages *including transliterated (Roman-script) data*. Reaching for it instead of vanilla BERT signals domain awareness.
- **The evaluation is the centrepiece, and that's my edge.** I come from a QA / reliability / eval background. Most ML repos ship a model with one accuracy figure and call it done. This one ships per-intent precision/recall/F1, a confusion matrix, and a written error analysis of what the model actually gets wrong and why. That's the differentiator — lead with it.
- **It actually runs.** FastAPI + Docker means it's a service, not a notebook that only works on my laptop.

---

## Architecture

```
raw utterances
      │
      ▼
  data_prep.py      clean, label, split (train / val / test)
      │
      ▼
   tokenizer        MuRIL tokenizer (handles the Roman-script Indian text)
      │
      ▼
   train.py         fine-tune MuRIL + a classification head
      │
      ▼
  evaluate.py       per-intent F1, confusion matrix, error analysis  ◄── the point
      │
      ▼
  predict.py        single function: text → {intent, confidence}
      │
      ▼
   api.py           FastAPI: POST /predict
      │
      ▼
  Dockerfile        one container that serves the model
```

---

## Planned project structure

```
code-switch-classifier/
├── README.md
├── CLAUDE.md              # how we work together (read this first, Claude Code)
├── requirements.txt
├── .gitignore
├── data/
│   ├── intents.md         # intent definitions + example utterances
│   ├── raw/               # hand-written + augmented utterances
│   └── processed/         # train / val / test splits
├── src/
│   ├── data_prep.py
│   ├── train.py
│   ├── evaluate.py        # the evaluation harness
│   ├── predict.py
│   └── api.py
├── models/                # saved fine-tuned model (gitignored — too big for git)
├── tests/                 # pytest — most ML repos skip this; this one won't
└── Dockerfile
```

A `tests/` folder is deliberate. It plays to my actual strength and almost no ML side-project has one — another small thing that makes this stand out.

---

## Tech stack

- **MuRIL** (`google/muril-base-cased`) — base encoder
- **PyTorch** + **HuggingFace `transformers`** / `datasets` — fine-tuning
- **scikit-learn** — evaluation metrics (F1, confusion matrix)
- **FastAPI** + **uvicorn** + **Pydantic** — serving, with typed request/response contracts
- **pytest** — tests
- **Docker** — packaging

---

## Scope — v1 (keep it shippable)

**In:**
- ~8 intents + an `other` class
- Hinglish first; Tanglish folded in once the pipeline works
- Fine-tuned MuRIL
- A real evaluation harness
- `POST /predict` endpoint returning intent + confidence
- A Dockerfile that runs the whole thing
- Basic tests

**Out (for now — resist the urge):**
- Any frontend / UI
- Comparing multiple models
- Hyperparameter sweeps
- Slot-filling, multi-turn dialogue, generation
- Cloud deployment

v1 is done when: *it runs locally inside Docker, and I can show an honest evaluation of how good it actually is.*

---

## Data plan (the hard part — be honest about it)

Public code-mixed **intent** datasets are scarce, and Tanglish ones especially so. Model quality will be gated by data quality, and that's a real lesson, not a footnote.

Realistic path:
1. Lock the intent set and write definitions in `data/intents.md`.
2. Hand-write ~10 seed utterances per intent (mix of Hinglish and Tanglish, Roman script).
3. Augment from there — templates and/or LLM-generated variants — then **hand-verify the labels**. Garbage labels = garbage model.
4. Search for existing starting points (e.g. GLUECoS, public Hinglish datasets) but treat them as raw material to clean, not plug-and-play.

Start tiny. A working pipeline on 80 examples beats a stalled one waiting for 8,000.

---

## Evaluation (do not skip — this is the showcase)

Accuracy alone lies, especially when intents are imbalanced. The harness reports:

- **Per-intent precision, recall, F1**
- **Macro-F1** (so a rare intent can't be hidden by a common one)
- **Confusion matrix** — which intents get mistaken for which
- **Error analysis** — pull the actual misclassified utterances and write down *why* they failed

That last one is the part most people skip and the part that proves I understand the model rather than just ran it.

---

## Working approach

This repo is being built to **learn ML engineering by doing it**, not to ship as fast as possible. I have a Python/QA background but haven't trained an ML model before. The detailed collaboration rules live in **`CLAUDE.md`** — read that before writing code.

---

## Build order (start here, in order)

1. Finalise the intent set → write `data/intents.md`.
2. Hand-write ~10 utterances per intent → first tiny dataset.
3. Get **tokenization** working on those few examples (smallest end-to-end piece).
4. Get a training loop that **overfits the tiny set** — if it can't memorise 80 examples, the pipeline is broken. This is a sanity check before scaling anything.
5. Expand the dataset.
6. Real train + the evaluation harness.
7. `predict.py`.
8. FastAPI endpoint.
9. Dockerfile.
10. Tests alongside, not at the end.