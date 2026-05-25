# DAA Helper — Fine-tuning Qwen2.5-1.5B for Algorithmic Reasoning

NLP Assignment 04: Track 1, Option A (SFT → DPO)

This pipeline fine-tunes Qwen2.5-1.5B-Instruct into a Design and Analysis of Algorithms (DAA) tutor that **guides students through reasoning step by step** rather than dumping the final answer. We do this in two stages: Supervised Fine-Tuning (SFT) on CodeForces editorials, then Direct Preference Optimization (DPO) on Socratic-vs-answer-dump preference pairs.

## Project Structure

```
daa-helper/
├── README.md                          (this file)
├── requirements.txt
├── data/
│   ├── test_prompts.json              10 DAA test prompts (provided)
│   ├── gold_answers_template.json     fill from Claude.ai → rename to gold_answers.json
│   ├── gold_answers.json              (you create this)
│   ├── dpo_questions.json             (auto-generated in notebook 01)
│   ├── dpo_responses_batch_*.json     (you create these from Claude.ai)
│   └── dpo_pairs.json                 (auto-generated in notebook 01)
├── configs/
│   ├── sft_trials.json                5 SFT configurations (wide range as required)
│   └── dpo_trials.json                5 DPO configurations (vary beta/LR/epochs)
├── utils/
│   ├── evaluation.py                  BLEU + BERTScore + inference helpers
│   └── io_helpers.py                  JSON save/load + HF Hub push
├── notebooks/
│   ├── 00_setup_and_baseline.ipynb    setup + base model eval
│   ├── 01_generate_dpo_pairs.ipynb    helper to build DPO pairs via Claude.ai
│   ├── 02_sft_trials.ipynb            run 5 SFT trials
│   ├── 03_dpo_trials.ipynb            run 5 DPO trials on the SFT winner
│   └── 04_final_evaluation.ipynb      aggregate, build comparison table, report skeleton
├── results/                           (auto-populated; back this up!)
│   ├── baseline_base_model.json
│   ├── sft_<trial>.json × 5
│   ├── sft_winner.json
│   ├── dpo_<trial>.json × 5
│   ├── dpo_winner.json
│   ├── final_comparison.json
│   ├── comparison_table.csv
│   ├── qualitative_examples.md
│   └── report_skeleton.md
└── models/                            (LoRA adapters, ~50MB each)
    ├── sft_<trial>/ × 5
    └── dpo_<trial>/ × 5
```

## Why this structure (vs one big notebook)

1. **Crash recovery.** Kaggle sessions die after 12h or random disconnects. Each notebook saves to disk at every meaningful step. If notebook 02 dies after 3 of 5 SFT trials, just re-run it — the existing trials are skipped automatically.
2. **Cost discipline.** You can re-run notebook 03 (DPO) without redoing the expensive SFT trials.
3. **Submittable.** Each notebook tells one chunk of the story for the report ("Table 1 from Notebook 02 …").
4. **No accidental overwrites.** Cell outputs are ephemeral. Everything that matters is JSON on disk.

## Persistence Strategy

Three layers of redundancy so you don't lose work:

1. **Disk (Kaggle working dir):** Every trial writes to `results/*.json` immediately. JSON files are atomic — they don't get corrupted by interrupted writes.
2. **GitHub:** After each notebook completes, commit and push. Code + results JSONs are tiny.
3. **HuggingFace Hub:** Model adapters get pushed to your account as private model repos. Free, versioned, recoverable from anywhere.

## Setup Instructions

### Prerequisites
- A HuggingFace account with a write token (https://huggingface.co/settings/tokens)
- A GitHub repo (push your daa-helper folder there)
- A Kaggle account (free tier: 2× T4, 30 hr/week)

### Kaggle Setup
1. Create a new Kaggle Notebook.
2. Add your HF token as a Kaggle Secret named `HF_TOKEN` (Settings → Add-ons → Secrets).
3. In the first cell, clone this repo:
   ```python
   !git clone https://github.com/YOUR_USERNAME/daa-helper.git /kaggle/working/daa-helper
   ```
4. Open the notebooks from `/kaggle/working/daa-helper/notebooks/`.
5. Edit `HF_USERNAME` and `GITHUB_REPO` placeholders in each notebook to your values.
6. Run notebooks **in order**: 00 → 01 → 02 → 03 → 04.

## Pipeline Workflow (chronological)

### Step 1 — Gold Answers (manual, ~1 hour)
Open `data/gold_answers_template.json`. Rename to `gold_answers.json`. Open Claude.ai web UI in your browser. Use the system instruction from notebook 00 step 1. Paste each of the 10 prompts, copy the response back into the corresponding `gold_answer` field. Commit the filled file to your repo.

### Step 2 — Baseline (~10 min)
Run **notebook 00**. This loads Qwen2.5-1.5B-Instruct in 4-bit, runs it on the 10 prompts, scores against gold answers, saves `results/baseline_base_model.json`.

### Step 3 — DPO Pair Generation (manual + automated, ~2 hours)
Run **notebook 01**. It generates 150 DAA question stubs and prints copy-paste-ready batch prompts. Send each batch to Claude.ai with the system instruction provided. Save Claude's JSON responses as `data/dpo_responses_batch_<N>.json`. Re-run the final cell of notebook 01 to compile them into `data/dpo_pairs.json`.

### Step 4 — SFT Trials (~3-8 hours)
Run **notebook 02**. Loads `open-r1/codeforces-cots` (3k samples), runs 5 SFT trials with the configs in `configs/sft_trials.json`, evaluates each on your 10 prompts, picks the winner. If session dies, just re-run — already-finished trials are auto-skipped.

### Step 5 — DPO Trials (~2-5 hours)
Run **notebook 03**. Loads the winning SFT adapter, runs 5 DPO trials on the preference pairs, evaluates each, picks the winner.

### Step 6 — Final Aggregation (~5 min)
Run **notebook 04**. Builds `comparison_table.csv`, `qualitative_examples.md`, and `report_skeleton.md`. Open the skeleton, fill in the bracketed sections, convert to docx.

### Step 7 — Submit
1. Report: rename `report.docx` → `<MemberName1>_<MemberName2>.docx`
2. Upload to LMS (NOT Google Drive)
3. Push code to GitHub, include link in report
4. Large files (model adapters) → Dropbox or HF Hub link in report

## Time Budget (Kaggle's 30 hr/week limit)

| Step | Time | Cumulative |
|---|---|---|
| Notebook 00 | 0.2 hr | 0.2 hr |
| Notebook 01 (compute only) | 0.1 hr | 0.3 hr |
| Notebook 02 (5 SFT trials) | ~6 hr | 6.3 hr |
| Notebook 03 (5 DPO trials) | ~3 hr | 9.3 hr |
| Notebook 04 | 0.1 hr | 9.4 hr |
| Buffer for OOMs / restarts | ~5 hr | ~14 hr |

**Comfortable inside 30 hours.** Manual work (gold answers + DPO pair generation) happens off-Kaggle and doesn't count against the GPU quota.

## Selection Rule (per assignment rubric)

For both SFT and DPO winner selection:
1. **Primary:** highest combined BLEU + BERTScore F1 on the 10 test prompts
2. **Tie-breaker:** lower validation loss

This is implemented in the ranking cells of notebooks 02 and 03.

## Failure Modes to Watch For

1. **OOM on T4 with SFT trial 5** (rank 64 + all modules) — if it happens, reduce `per_device_train_batch_size` to 1 and increase `gradient_accumulation_steps` to 8.
2. **Trial 2 (MLP-only) may underperform** — this is a real signal worth reporting, not a bug. Attention layers carry more of the behavioral signal in our setup.
3. **DPO trial 4 (high LR=5e-5) may diverge** — also a real signal. If you see exploding loss or NaN rewards, that IS the result; report it.
4. **`open-r1/codeforces-cots` is large** — full download is ~2GB. The notebook only uses the first 3200 samples; HF datasets streams what's needed.
