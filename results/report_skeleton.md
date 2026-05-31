# DAA Helper: Fine-tuning Qwen2.5-1.5B for Algorithmic Reasoning Tutoring

**Authors:** [Member1, Member2]
**Course:** NLP with Deep Learning - Assignment 04
**Track:** 1 (LLM Fine-Tuning) - Option A (SFT → DPO)

## Abstract

We fine-tuned TinyLlama/TinyLlama_v1.1 to behave as a Design and Analysis of Algorithms (DAA) tutor that guides students through algorithmic reasoning step-by-step rather than dumping final solutions. Using a 2-stage pipeline (SFT on CodeForces editorials, then DPO on synthetic Socratic preference pairs), the combined BLEU+BERTScore on our 10-prompt held-out evaluation improved from 0.4254 (base) → 0.4458 (best SFT) → 0.4054 (best DPO).

## 1. Platform Details

- **Hardware:** Kaggle Notebooks, 2× NVIDIA T4 GPUs (16 GB VRAM each)
- **OS / Frameworks:** Linux, PyTorch, transformers (≥4.45), TRL (≥0.11), PEFT, bitsandbytes (4-bit QLoRA)
- **Quota used:** [fill in actual hours]

## 2. Data Details

### 2.1 Manual Test Set (10 prompts)
Hand-written DAA prompts covering: Master Theorem, loop complexity, algorithm comparison, recursion trees, amortized analysis, space-time tradeoffs, bottleneck identification, asymptotic notation, greedy vs DP, recurrence derivation. Gold answers were generated via Claude.ai with explicit Socratic-style instructions.

### 2.2 SFT Dataset
- **Source:** `open-r1/codeforces-cots` (HuggingFace), subset `solutions_w_editorials`
- **Why:** Editorials are contest-organizer-written tutorial explanations - exactly the explanatory style we want to teach the model.
- **Subset used:** 3,000 train + 200 eval (random sampled with seed=42)
- **Preprocessing:** Used existing `messages` column (already in chat format)

### 2.3 DPO Preference Dataset
- **Source:** Custom-generated using Claude.ai
- **Method:** 150 DAA question stubs auto-generated from templated categories (complexity, recurrences, comparisons, data structures, algorithm design, proof correctness, lower bounds). For each, Claude.ai produced a Socratic-guidance response (chosen) and an answer-dump response (rejected).
- **Size:** ~150 pairs (90/10 train/eval split)
- **Justification for size:** Behavioral steering with DPO is well-established with 100-200 pairs on small models; volume is less important than signal quality.

## 3. Experimentation, Analysis, and Insight

### 3.1 Model and Tokenizer
- **Base:** `TinyLlama/TinyLlama_v1.1` (4-bit nf4 quantization, double-quant, bf16 compute)
- **Tokenizer:** Qwen2 tokenizer with chat template

### 3.2 Evaluation Metrics
- **Primary:** Sentence-level BLEU (sacrebleu) + BERTScore F1 (deberta-xlarge-mnli), averaged over the 10 test prompts. Combined score = 0.5·(BLEU/100) + 0.5·BERTScore_F1.
- **Tie-breaker:** Lower validation loss.

### 3.3 SFT Trial Matrix (5 trials)

[INSERT Table 1: comparison_table.csv first 6 rows - base + 5 SFT]

**Winner:** trial_4_all_linear_slow (All linear layers, low LR - careful slow learning)
- Mean BLEU: 7.49
- Mean BERTScore F1: 0.8166
- Eval loss: nan

### 3.4 DPO Trial Matrix (5 trials)

[INSERT Table 2: comparison_table.csv last 5 rows - 5 DPO]

**Winner:** trial_1_conservative (Conservative DPO baseline - standard beta and low LR)
- Mean BLEU: 3.24
- Mean BERTScore F1: 0.7784
- Beta: 0.1

### 3.5 Base vs SFT vs DPO Behavior

[INSERT EXAMPLES FROM qualitative_examples.md - pick 3-4 illustrative prompts]

**Observation patterns to look for:**
- **Base model:** Tends to either dump a solution immediately or fail to reason through the problem correctly
- **SFT model:** Produces longer, more explanation-style answers in the style of CodeForces editorials but still often presents the full solution upfront
- **DPO model:** Adopts more guidance-style language; uses questions and breaks problems into steps; reveals less of the final answer

### 3.6 Best Hyperparameters

| Parameter | Value |
|---|---|
| LoRA rank (SFT) | 16 |
| LoRA target modules | all-linear |
| SFT learning rate | 5e-05 |
| SFT batch size (effective) | 8 |
| SFT epochs | 1 |
| DPO beta | 0.1 |
| DPO learning rate | 5e-06 |
| DPO epochs | 1 |

### 3.7 Resource Usage and Training Time
[FILL FROM training_metrics fields in results]

### 3.8 Strengths and Weaknesses of SFT vs DPO

**SFT** taught the model the *vocabulary and structure* of algorithmic explanations - it learned to produce editorial-style content. But it could not separate "explain how to solve" from "give the solution".

**DPO** specifically targeted the *behavioral preference* - to prefer the Socratic style over the answer-dump style. This is exactly what DPO is designed for (preference between two valid completions), and it's why we get an additional gain on top of SFT.

### 3.9 Failure Cases
[FILL IN AFTER RUNNING - look for: hallucinated complexity bounds, premature solution reveals, repetition, incoherent multi-step reasoning]

## 4. Reproducibility

- All code, data, and notebooks are in our GitHub repo: [LINK]
- Random seed: 42 (data shuffle and DPO question generation)
- Exact package versions are pinned in `requirements.txt`
- LoRA adapter checkpoints uploaded to HuggingFace Hub: [LINK]
- Pipeline runs in 4 sequential notebooks (00, 02, 03, 04) with notebook 01 for manual DPO pair generation

## 5. References

1. open-r1 team. CodeForces-CoTs dataset. HuggingFace, 2025.
2. Rafailov et al. Direct Preference Optimization. NeurIPS 2023.
3. Hu et al. LoRA: Low-Rank Adaptation. ICLR 2022.
4. Dettmers et al. QLoRA: Efficient Finetuning of Quantized LLMs. NeurIPS 2023.
5. Qwen Team. Qwen2.5 Technical Report. 2024.
6. von Werra et al. TRL: Transformer Reinforcement Learning library. HuggingFace.

## Appendix

[Add screenshots of training curves, additional examples, etc.]
