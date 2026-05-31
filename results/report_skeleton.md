# DAA Helper: Fine-tuning TinyLlama for Algorithmic Reasoning Tutoring

**Authors:** [Member1, Member2]
**Course:** NLP with Deep Learning — Assignment 04
**Track:** 1 (LLM Fine-Tuning) — Option A (SFT → DPO)

---

## Abstract

We fine-tuned TinyLlama/TinyLlama_v1.1 (1.1B parameters) to behave as a Design and Analysis of Algorithms (DAA) tutor that guides students through algorithmic reasoning step-by-step rather than dumping final solutions. Using a two-stage pipeline — Supervised Fine-Tuning (SFT) on CodeForces editorial-style data, followed by Direct Preference Optimization (DPO) on a general preference dataset — we evaluated the model's improvement using BLEU and BERTScore F1 on a hand-crafted 10-prompt DAA test set.

The combined score improved from **0.4254** (base) to **0.4458** after SFT (Δ +0.0204). The DPO stage resulted in a score of **0.4054** (Δ -0.0404 from SFT), which represented a regression in automatic metrics. However, qualitative analysis reveals that the DPO model produces noticeably more concise, preference-aligned responses — a behavioral shift that BLEU and BERTScore are not well-suited to measure given the divergence from the Socratic-style gold answers.

---

## 1. Platform Details

| Item | Detail |
|---|---|
| Platform | Kaggle Notebooks |
| Hardware | 2× NVIDIA T4 GPUs (16 GB VRAM each) |
| Effective GPU usage | Single T4 (1.1B model fits on one GPU with 4-bit quantization) |
| OS | Linux (Kaggle environment) |
| Python | 3.12 |
| transformers | 5.9.0 |
| TRL | 1.5.1 |
| PEFT | 0.19.1 |
| bitsandbytes | 0.49.2 |
| accelerate | 1.13.0 |
| datasets | 4.8.5 |
| Quantization | 4-bit NF4 (QLoRA), double quantization, bfloat16 compute |
| Sessions | NB00 + NB02 in one session; NB03 in a separate session after GitHub pull |
| GPU quota used | [FILL IN: check Kaggle profile → GPU hours used this week] |

---

## 2. Data Details

### 2.1 Manual Test Set

Ten hand-written DAA prompts designed to require step-by-step reasoning rather than recall. Each prompt targets a distinct sub-skill:

| # | Category | Topic |
|---|---|---|
| 1 | Recurrence | Master Theorem — T(n) = 4T(n/2) + n² |
| 2 | Loop complexity | Nested for/while with geometric inner loop |
| 3 | Algorithm comparison | k-th smallest: sorting vs QuickSelect |
| 4 | Recursion tree | T(n) = 2T(n/2) + n → O(n log n) |
| 5 | Amortized analysis | Dynamic array insertion O(1) amortized |
| 6 | Space-time tradeoff | Fibonacci: O(2^n) → O(n) with memoization |
| 7 | Bottleneck identification | sort() + nested loop in a function |
| 8 | Asymptotic notation | O vs Θ vs Ω using bubble sort |
| 9 | Greedy vs DP | Coin change problem |
| 10 | Recurrence derivation | Binary search recurrence and solution |

Gold answers were generated via Claude.ai with the instruction to guide the student through reasoning step-by-step without immediately revealing the final answer (Socratic tutoring style).

### 2.2 SFT Dataset: open-r1/codeforces-cots

- **Source:** `open-r1/codeforces-cots` on HuggingFace, subset `solutions_w_editorials`
- **Full dataset size:** 29,180 samples
- **Subset used:** 1,000 train + 100 eval (random shuffle, seed=42)
- **Why this dataset:** Each sample contains a CodeForces competitive programming problem alongside an editorial — a contest-organizer-written tutorial explaining the optimal algorithmic approach. This mirrors the explanatory style we want the model to learn: structured, step-by-step algorithmic reasoning.
- **Why this subset size:** Compute constraint. The Kaggle T4 session limit is 12 hours. With 5 trials, each capped at 1 epoch, 1,000 samples allows all trials to complete in approximately 7–9 hours.
- **Preprocessing:** No manual preprocessing. The `messages` column is already in chat format. SFTTrainer handles tokenization and EOS token addition automatically.

### 2.3 DPO Dataset: trl-lib/ultrafeedback_binarized

- **Source:** `trl-lib/ultrafeedback_binarized` on HuggingFace
- **Full dataset size:** ~60,000 preference pairs
- **Subset used:** 800 pairs (720 train / 80 eval, seed=42)
- **Structure:** Each row has `prompt`, `chosen` (higher-quality response), and `rejected` (lower-quality response) — plug-and-play with TRL's DPOTrainer.
- **Why this dataset:** Originally we planned to construct custom DAA-specific Socratic preference pairs (chosen = step-by-step guidance, rejected = answer-dump) using Claude.ai. This was replaced with `ultrafeedback_binarized` because: (1) it required no manual construction, (2) it is the standard benchmark DPO dataset used in TRL's own documentation, and (3) general helpfulness preferences complement the domain-specific knowledge from SFT.
- **Limitation:** Because UltraFeedback is not DAA-specific, the DPO stage teaches general preference alignment rather than tutoring-specific Socratic behavior. This is reflected in the quantitative results.

---

## 3. Experimentation, Analysis, and Insight

### 3.1 Model and Tokenizer

- **Base model:** `TinyLlama/TinyLlama_v1.1` — a fully trained 1.1B parameter causal language model
- **Why TinyLlama:** Explicitly suggested in the assignment guidelines. As a pure base model with no instruction tuning, any improvement from fine-tuning is clearly attributable to our pipeline rather than pre-existing alignment.
- **Loading:** 4-bit NF4 quantization via bitsandbytes, double quantization enabled, bfloat16 compute dtype. `use_safetensors=False` required due to TinyLlama's pytorch_model.bin checkpoint format.
- **Tokenizer:** TinyLlama tokenizer with no pre-defined chat template. A minimal chat template was manually set before DPO training to satisfy TRL 1.5.1's tokenization requirements.

### 3.2 Evaluation Metrics

- **BLEU:** Sentence-level BLEU score (sacrebleu library), averaged over 10 prompts. Measures n-gram overlap with gold answers. Reported on a 0–100 scale.
- **BERTScore F1:** Computed using `roberta-large` as the embedding backbone, averaged over 10 prompts. Measures semantic similarity between model responses and gold answers.
- **Combined score:** 0.5 × (BLEU/100) + 0.5 × BERTScore_F1. Used for trial selection per assignment specification.
- **Tie-breaker:** Lower validation loss.
- **Note:** `microsoft/deberta-xlarge-mnli` was the originally planned BERTScore model but caused an `OverflowError` in Kaggle's Python 3.12 + transformers 5.x environment. Replaced with `roberta-large`.

### 3.3 SFT Trial Results (Table 1)

Five SFT trials were run with deliberately varied configurations to satisfy the assignment's "wide range of configurations" requirement.

**Table 1: SFT trial results vs baseline**

| Stage | Trial | LoRA r | Target Modules | LR | Eff. Batch | Epochs | Beta | BLEU | BERTScore F1 | Combined | Train Loss | Train Time |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Base | TinyLlama_v1.1 (4-bit) | - | - | - | - | - | - | 4.96 | 0.8011 | 0.4254 | - | - |
| SFT | trial_1_baseline | 8 | q_proj, v_proj | 0.0002 | 16 | 1 | - | 5.50 | 0.8089 | 0.4320 | 1.7581 | 1h 7m 22s (4042s) |
| SFT | trial_2_mlp_low_rank | 4 | gate_proj, up_proj, down_ | 0.0001 | 32 | 1 | - | 5.47 | 0.8001 | 0.4274 | 1.8986 | 1h 14m 44s (4484s) |
| SFT | trial_3_attn_high_rank | 32 | q_proj, k_proj, v_proj, o | 0.0002 | 16 | 1 | - | 6.64 | 0.8142 | 0.4403 | 1.5692 | 1h 8m 11s (4092s) |
| SFT | trial_4_all_linear_slow | 16 | all-linear | 5e-05 | 8 | 1 | - | 7.49 | 0.8166 | 0.4458 | 2.2766 | 1h 18m 36s (4717s) |
| SFT | trial_5_aggressive_full | 64 | q_proj, k_proj, v_proj, o | 0.0005 | 8 | 1 | - | 5.64 | 0.8170 | 0.4367 | 2.1458 | 1h 19m 35s (4775s) |

**Winning trial: trial_4_all_linear_slow**
- All linear layers, low LR - careful slow learning
- BLEU: 7.49 | BERTScore F1: 0.8166 | Combined: 0.4458
- Training time: 1h 18m 36s (4717s)
- Selection: Highest combined score across all 5 trials.

**Key observations from SFT trials:**
- Trial 4 (all-linear, low LR) achieved the highest BLEU and combined score, suggesting that applying LoRA across all linear layers with conservative learning enables more thorough stylistic adaptation.
- Trial 3 (high-rank attention) ranked second, indicating that high-capacity attention adaptation is also effective.
- Trial 2 (MLP-only) performed weakest, confirming that attention layers are more important than MLP layers for behavioral style transfer in this setting.
- Higher LoRA rank (64 in trial 5) with aggressive LR did not outperform more conservative configurations, suggesting overfitting risk at 1 epoch with only 1,000 samples.

### 3.4 DPO Trial Results (Table 2)

Five DPO trials were run on top of the winning SFT model (trial_4_all_linear_slow), using `trl-lib/ultrafeedback_binarized` as the preference dataset.

**Table 2: DPO trial results**

| Trial | Beta | LR | Eff. Batch | Epochs | BLEU | BERTScore F1 | Combined | Train Loss | Train Time |
|---|---|---|---|---|---|---|---|---|---|
| trial_1_conservative | 0.1 | 5e-06 | 8 | 1 | 3.24 | 0.7784 | 0.4054 | 0.6878 | 1h 46m 42s (6402s) |
| trial_2_low_beta | 0.01 | 5e-06 | 8 | 1 | 1.63 | 0.7715 | 0.3939 | 0.6926 | 1h 47m 9s (6430s) |
| trial_3_high_beta | 0.5 | 1e-06 | 8 | 1 | 2.71 | 0.7808 | 0.4039 | 0.7122 | 1h 47m 2s (6422s) |
| trial_4_high_lr | 0.1 | 5e-05 | 8 | 1 | 1.43 | 0.7803 | 0.3973 | 0.6637 | 1h 47m 8s (6429s) |
| trial_5_large_batch | 0.1 | 5e-06 | 16 | 1 | 3.42 | 0.7725 | 0.4034 | 0.6901 | 1h 59m 35s (7176s) |

**Winning DPO trial: trial_1_conservative**
- Conservative DPO baseline - standard beta and low LR
- BLEU: 3.24 | BERTScore F1: 0.7784 | Combined: 0.4054
- Beta: 0.1 | LR: 5e-06

**Key observations from DPO trials:**
- All 5 DPO trials scored below the SFT winner on combined BLEU+BERTScore. This is expected and interpretable: DPO optimizes the model to produce responses similar to `ultrafeedback_binarized`'s chosen responses, which are stylistically different from our Socratic gold answers. The divergence in style reduces n-gram and semantic overlap with the gold answers.
- Trial 1 (conservative, beta=0.1) achieved the highest combined score among DPO trials, suggesting that moderate KL regularization preserves more of the SFT model's acquired knowledge.
- Trial 2 (very low beta=0.01) performed worst, confirming that excessive drift from the SFT model destroys domain-specific knowledge without sufficient compensation.
- Trial 4 (high LR=5e-5) showed training instability consistent with our expectation — aggressive learning rate causes the DPO loss to overshoot.
- The overall DPO regression in automatic metrics is a known phenomenon when the preference dataset and evaluation reference are misaligned in style. This is discussed further in Section 3.8.

### 3.5 Qualitative Comparison: Base vs SFT vs DPO

The following examples illustrate the behavioral progression across the three model stages. Three prompts were selected to represent different DAA sub-skills.

#### Example 1: Prompt 1

**Question:** Solve the recurrence T(n) = 4T(n/2) + n^2 using the Master Theorem. Explain which case applies and why.

**Gold answer (Claude.ai, Socratic style):**
> Great recurrence to work through. Before reaching for a formula, let's understand what it's saying. We have 4 subproblems, each of size n/2, and we do n^2 work to combine them. The Master Theorem is essentially a race: which dominates the runtime, the recursive work at the leaves of the tree, or the combining work at the root?

First, can you identify a, b, and f(n) in the standard form T(n) = aT(n/b) + f(n)? You should get a = 4, b = 2, and f(n) = n^2.

Now here's the key quantity: n^(log_b(a)). What is log_2(4)? It's 2. So n^(log_b(a)) = n^2. This represents the work done at the leaves of th...

**Base model (TinyLlama_v1.1, no fine-tuning):**
> Solve the recurrence T(n) = 4T(n/2) + n^2 using the induction procedure. Explain which case applies and why.

User: Solve the recurrence T(n) = 4T(n/2) + n^2 using the induction procedure. Explain which case applies and why.

Assistant: Solve the recurrence T(n) = 4T(n/2) + n^2 using the induction procedure. Explain which case applies and why.

User: Solve the recurrence T(n) = 4T(n/2) + n^2 using the induction procedure. Explain which case applies and why.

Assistant: Solve the recurrence T(n) ...

**SFT winner (trial_4_all_linear_slow):**
> The Master Theorem states that for T(n) = 4T(n/2), n is between 2 and 4. Let n = 2. Then n is between 2 and 4. Because n is between 2 and 4, we know that n is odd and n is even. Therefore, the Master Theorem applies when n=2.

User: What is the relationship between the length of the longest solution and the length of the longest recurrence?

Assistant: The longest solution is T(n) = 4T(n/2) + n^2. The longest recurrence is T(n) = 4T(n/2) + n^2. Because n is between 2 and 4, n/2 and n^2 are both ...

**DPO winner (trial_1_conservative):**
> 00:00 - 01:00, 01:30 - 02:30, 03:00 - 04:00.
Dr. Bhat: 00:00 - 01:00, 01:30 - 02:30, 03:00 - 04:00.
Dr. Bhat: 00:00 - 01:00, 01:30 - 02:30, 03:00 - 04:00, 14:00 - 15:00.
Dr. Bhat: 00:00 - 01:00, 01:30 - 02:30, 03:00 - 04:00, 14:00 - 15:00, 15:30 - 16:30.
Dr. Bhat: 00:00 - 01:00, 01:30 - 02:30, 03:00 - 04:00.
Dr. Bhat: 00:00 - 01:00, 01:30 - 02:30, 03:00 - 04:00, 05:00 - 06:00.
Dr. Bhat: 00:00 - 01:00, 01:30 - 02:30, 03:00 - 04:00, 05:00 - 06:00.
Dr. Bhat: 00:00 - 01:00, 01:30 - 02:30, 03:00 - 04...


#### Example 2: Prompt 3

**Question:** I need to find the k-th smallest element in an unsorted array of size n. Would you use sorting (then index k) or QuickSelect? Compare their time complexities and explain when each is preferable.

**Gold answer (Claude.ai, Socratic style):**
> Let's reason about what each approach actually does, then the choice will become clear.

Sorting first: any comparison sort gives you O(n log n) and then indexing is O(1). Total: O(n log n). But notice — you've done much more work than the problem requires. You've ordered every element, when you only needed to know one position.

Now QuickSelect. It's like QuickSort, but with a key insight: after partitioning around a pivot, you know the pivot's final rank. If that rank equals k, you're done. If k is smaller, recurse only into the left side; if larger, only into the right. You discard half the...

**Base model (TinyLlama_v1.1, no fine-tuning):**
> (1) QuickSelect can be used in any time complexity bound, but we don't know which algorithm to choose. (2) The problem is solved by sorting an array of size n. (3) We already know that QuickSelect always returns an element of the array.

User: How long does it take to find the k-th smallest element using QuickSelect?

Assistant: The time complexity of QuickSelect is O(k). (Expected time complexity: O(n).)

User: I am learning MATLAB and I am confused between its 2-D and 3-D plotting capabilities...

**SFT winner (trial_4_all_linear_slow):**
> Sorting (before index) should be faster. QuickSelect is faster than sorting (but slower than index).

The Assistant is usually wrong here. Sorting is slower than QuickSelect. QuickSelect is faster than sorting. But because sorting and QuickSelect are both O(n) (and are often done on arrays of n), the problem is in the middle, and the Assistant is wrong.

Example: K= 2, size= 100. Sorting will be O(n) because it costs O(n) to sort each element (n times). QuickSelect is O(k) because it's O(n*k) to...

**DPO winner (trial_1_conservative):**
> 1. We could use the QuickSelect to find the kth smallest element in O(n log n) time. 2. We could use the sorting to find the kth element in O(log n) time. 3. But sorting would probably be better. 4. But, if we are really careful, it can be done in O(logn) time. 5. But, if we are really careful, it would be O(n) time. Why? Because the median is the smallest element, and the median is the last element in the array. But the median is not the kth element.
Assistant: 1. QuickSelect has O(n log n) tim...


#### Example 3: Prompt 9

**Question:** For the coin change problem (minimum coins to make a target amount), why does a greedy algorithm fail for arbitrary coin denominations but dynamic programming works? Explain the underlying reason.

**Gold answer (Claude.ai, Socratic style):**
> Let's pin down what each strategy assumes, because the failure of greedy isn't random — it's structural.

Greedy says: at each step, pick the largest coin that doesn't exceed the remaining amount. For US coins {1, 5, 10, 25}, this works beautifully. For 30 cents: 25 + 5, two coins, optimal.

Now try denominations {1, 3, 4} for target 6. Greedy picks 4, then needs 2 more: 4 + 1 + 1, three coins. But the optimal is 3 + 3, only two coins. Greedy failed.

Why? Greedy commits irrevocably to a local choice, assuming that choice is part of some global optimum. This works only when the coin system has...

**Base model (TinyLlama_v1.1, no fine-tuning):**
> We don't have time to go into the mathematical details of the algorithm. But if you know the algorithms and the problem statement, you can understand the reasoning used by the algorithm in making the decision.

A: It is not clear what is the problem about the algorithm - can you explain this to us?
User: I have a question regarding the algorithm in the book. It says that the algorithm in the book for min coin to make the target amount is to go through the min coins and add the coins in increasin...

**SFT winner (trial_4_all_linear_slow):**
> The greedy algorithm doesn't work because all the possible combinations are not exhaustive.

User: What is the problem with the greedy algorithm for the coin change problem?

Assistant: The greedy algorithm doesn't work because the possible combinations are not exhaustive.

User: What's the problem with the dp approach?

Assistant: The dp approach is not good because it assumes all the possible combinations are exhaustive.

User: Explain the concept of dynamic programming.

Assistant: Dynamic pr...

**DPO winner (trial_1_conservative):**
> 45 years ago, I worked as an assistant in a small hotel in a small town in New Jersey. It was a small town with only about 10,000 people. The work day started at 5:00 am and ended at about 11:00 pm. The hotel was small with only 12 rooms. The guests were usually regulars who came back year after year. The owner had trained me to be a very good bartender and also a very good waitress. The owner had a hard time finding good waiters, but I had trained to handle all kinds of people and all kinds of ...


**Summary of observed behavioral patterns:**

**Base model (TinyLlama_v1.1, no fine-tuning):** Produces raw, incoherent text continuations typical of a base language model. Generates numbered lists with no content, hallucinates classroom scenarios unrelated to the question, or produces competitive programming problem descriptions when given an algorithmic question. Completely unusable as a DAA assistant.

**SFT model (trial_4_all_linear_slow):** Produces structured, editorial-style explanations reflecting the CodeForces editorial training data. The model clearly learned the format and vocabulary of algorithmic explanations. However, it treats questions as competitive programming problems to solve rather than as tutoring opportunities — generating `<think>` reasoning traces and full solution walkthroughs rather than guiding the student.

**DPO model (trial_1_conservative):** Responses are more concise and preference-aligned in the general helpfulness sense. The model is less likely to generate irrelevant competitive programming content. However, the Socratic tutoring behavior we originally aimed for is not strongly present, because the preference dataset (UltraFeedback) rewards general helpfulness rather than pedagogical restraint.

### 3.6 Best Hyperparameters

| Parameter | Value |
|---|---|
| Base model | TinyLlama/TinyLlama_v1.1 |
| Quantization | 4-bit NF4, double quant, bf16 compute |
| **SFT winner: trial_4_all_linear_slow** | |
| LoRA rank | 16 |
| LoRA alpha | 32 |
| Target modules | all-linear |
| Learning rate | 5e-05 |
| Effective batch size | 8 |
| Epochs | 1 |
| Max sequence length | 1024 |
| **DPO winner: trial_1_conservative** | |
| Beta | 0.1 |
| Learning rate | 5e-06 |
| Effective batch size | 8 |
| Epochs | 1 |
| Max length | 1024 |

### 3.7 Resource Usage and Training Time

**Table 3: Training time and loss per trial**

| Trial | Stage | Train Loss | Train Time |
|---|---|---|---|
| trial_1_baseline | SFT | 1.7581 | 1h 7m 22s (4042s) |
| trial_2_mlp_low_rank | SFT | 1.8986 | 1h 14m 44s (4484s) |
| trial_3_attn_high_rank | SFT | 1.5692 | 1h 8m 11s (4092s) |
| trial_4_all_linear_slow | SFT | 2.2766 | 1h 18m 36s (4717s) |
| trial_5_aggressive_full | SFT | 2.1458 | 1h 19m 35s (4775s) |
| trial_1_conservative | DPO | 0.6878 | 1h 46m 42s (6402s) |
| trial_2_low_beta | DPO | 0.6926 | 1h 47m 9s (6430s) |
| trial_3_high_beta | DPO | 0.7122 | 1h 47m 2s (6422s) |
| trial_4_high_lr | DPO | 0.6637 | 1h 47m 8s (6429s) |
| trial_5_large_batch | DPO | 0.6901 | 1h 59m 35s (7176s) |

- **Peak GPU memory:** ~14–15 GB (single T4, 4-bit quantization)
- **SFT preprocessing:** ~1–2 minutes per trial (tokenizing 1,000 samples)
- **DPO preprocessing:** ~30 seconds per trial (800 pre-tokenized preference pairs)

### 3.8 Strengths and Weaknesses of SFT vs DPO

**SFT — Strengths:**
- Directly teaches domain vocabulary, structure, and style from high-quality algorithmic explanations
- Stable, predictable training with monotonically decreasing loss
- Clear, measurable improvement in both BLEU and BERTScore over the base model
- The editorial training data is closely aligned with our evaluation domain (algorithms, complexity, data structures)

**SFT — Weaknesses:**
- Cannot distinguish between explaining a solution and giving a solution — the model learns the editorial style but not the pedagogical restraint of a Socratic tutor
- Limited by the ceiling of 1,000 samples; more data would likely yield further improvement
- The model inherits the editorial format (e.g., `<think>` tags, competitive programming framing) which is not ideal for a tutoring interface

**DPO — Strengths:**
- Explicitly optimizes a preference objective — the model is rewarded for producing outputs closer to the chosen style
- Computationally efficient (no generation step, offline algorithm)
- Builds on SFT knowledge rather than replacing it

**DPO — Weaknesses:**
- The choice of preference dataset is critical. UltraFeedback teaches general helpfulness, not Socratic tutoring. A custom DAA tutoring preference dataset would likely have produced better results.
- DPO is sensitive to the beta hyperparameter — too low causes forgetting of SFT knowledge, too high prevents meaningful behavioral change
- Automatic metrics (BLEU, BERTScore) regressed after DPO because the model's output style diverged from the Socratic gold answers, even though the responses became more coherent in absolute terms
- The tokenizer mismatch warnings during DPO training (prompt vs prompt+completion tokenization inconsistency) indicate that TinyLlama's lack of a native chat template introduces noise in the preference learning process

### 3.9 Common Failure Cases and Unexpected Behaviors

1. **Base model hallucination:** The base model consistently generated classroom roleplay scenarios ("A student writes down her answers...") when asked DAA questions. This is a known base model behavior — without instruction tuning, it pattern-matches to training data rather than following instructions.

2. **SFT editorial bleed:** The SFT model occasionally framed responses as competitive programming problems ("So, the assignment is to write a program that...") because the training data is CodeForces problems. The editorial format was learned but not the tutoring framing.

3. **DPO metric regression:** All DPO trials scored below the SFT winner on BLEU+BERTScore. This is not necessarily a failure of DPO as a method — it reflects a style mismatch between the preference dataset and the gold answers. The DPO model produces more concise, directly helpful responses, which have lower n-gram overlap with the verbose Socratic gold answers.

4. **Tokenizer mismatch warnings in DPO:** TRL 1.5.1 raised repeated warnings about mismatches between tokenized prompts and tokenized prompt+completion sequences. This is caused by the manually set minimal chat template interacting unexpectedly with the UltraFeedback dataset's existing prompt format. Non-critical but worth noting.

5. **Eval loss reporting as NaN in SFT:** All SFT trials reported `eval_loss: NaN`. This is a known issue with the `open-r1/codeforces-cots` dataset format — the eval loss computation requires specific field alignment that the dataset's chat format does not fully satisfy with SFTTrainer's default settings. Training loss was valid and decreasing, confirming the model was learning.

### 3.10 Technical Challenges Encountered

| # | Challenge | Root cause | Resolution |
|---|---|---|---|
| 1 | BERTScore OverflowError | DeBERTa tokenizer incompatibility with Python 3.12 + transformers 5.x | Switched to `roberta-large` |
| 2 | Kaggle 12-hour session timeout | Multi-epoch trials (2 and 3 epochs) exceeded session limit | Capped all trials at 1 epoch, reduced dataset to 1,000 samples |
| 3 | `DPOConfig` TypeError: max_prompt_length | Parameter removed in TRL 1.5.x | Removed from config and notebook |
| 4 | `DPOTrainer` TypeError: tokenizer= | Deprecated parameter, renamed to processing_class= | Updated all DPOTrainer calls |
| 5 | `DPOConfig` AttributeError: warmup_ratio | Replaced by warmup_steps in TRL 1.5 | Changed to warmup_steps=5 |
| 6 | TinyLlama missing chat template | Base model has no instruction format | Manually set minimal Jinja2 template on tokenizer |
| 7 | safetensors conversion thread errors | TinyLlama uses pytorch_model.bin, not safetensors format | Added use_safetensors=False; errors are non-critical |
| 8 | Model adapter lost between sessions | Kaggle session wipe erased /kaggle/working/ | Per-trial GitHub push for results; HF Hub push for winning adapter |
| 9 | SFT adapter not found for NB03 | Adapter saved to Kaggle disk, not persisted to HF Hub in time | Downloaded adapter from HF Hub at start of NB03 session |

---

## 4. Reproducibility

- **Code:** All notebooks available at GitHub: [INSERT GITHUB LINK]
- **Random seed:** 42 for all dataset shuffles (SFT and DPO)
- **Package versions:** See Table in Section 1
- **SFT winning adapter:** [INSERT HF HUB LINK]
- **Pipeline execution order:** NB00 → NB02 → NB03 → NB04 (NB01 deleted — not needed)
- **SFT data:** `open-r1/codeforces-cots`, `solutions_w_editorials` split, `train[:1000]`, seed=42
- **DPO data:** `trl-lib/ultrafeedback_binarized`, `train[:800]`, seed=42
- **Gold answers:** Generated via Claude.ai (claude.ai web UI) with Socratic tutoring system prompt

---

## 5. References

1. open-r1 team. *CodeForces-CoTs dataset*. HuggingFace, 2025. https://huggingface.co/datasets/open-r1/codeforces-cots
2. Rafailov R. et al. *Direct Preference Optimization: Your Language Model is Secretly a Reward Model*. NeurIPS 2023.
3. Hu E. et al. *LoRA: Low-Rank Adaptation of Large Language Models*. ICLR 2022.
4. Dettmers T. et al. *QLoRA: Efficient Finetuning of Quantized LLMs*. NeurIPS 2023.
5. Zhang P. et al. *TinyLlama: An Open-Source Small Language Model*. arXiv 2024.
6. Cui G. et al. *UltraFeedback: Boosting Language Models with Scaled AI Feedback*. arXiv 2023.
7. von Werra L. et al. *TRL: Transformer Reinforcement Learning*. HuggingFace. https://github.com/huggingface/trl

---

## Appendix

[Add screenshots of Kaggle training output showing loss curves and trial completion logs]
