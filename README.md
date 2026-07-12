# DAA Helper: Fine-Tuning TinyLlama for Algorithmic Reasoning

**NLP with Deep Learning | Assignment 04 | Track 1, Option A (SFT → DPO)**

**Authors:** Muhammad Hashir Ilyas (26972), Muhammad Imad Raza (26953), Saad Imam (27079)  
**Institute:** Institute of Business Administration (IBA), Karachi

This pipeline fine-tunes `TinyLlama/TinyLlama_v1.1` (1.1B parameters) into a Design and Analysis of Algorithms (DAA) tutor that guides students through reasoning step-by-step using a Socratic style. The pipeline executes in two stages: Supervised Fine-Tuning (SFT) on CodeForces editorials for domain adaptation, followed by Direct Preference Optimization (DPO) on Socratic-vs-direct-answer preference pairs.

## Model Links
* **SFT Winner Adapter:** [hashirilyas18/daa-helper-tinyllama-sft-winner](https://huggingface.co/hashirilyas18/daa-helper-tinyllama-sft-winner)
* **DPO Winner Adapter:** [hashirilyas18/daa-helper-tinyllama-dpo-winner](https://huggingface.co/hashirilyas18/daa-helper-tinyllama-dpo-winner)

## Project Structure

```text
daa-helper/
├── README.md
├── requirements.txt
├── data/
│   ├── test_prompts.json              # 10 DAA test prompts
│   ├── gold_answers.json              # Socratic reference answers (via Claude.ai)
│   ├── dpo_questions.json             # Auto-generated DPO prompt stubs
│   └── dpo_pairs.json                 # Compiled chosen/rejected pairs for DPO
├── configs/
│   ├── sft_trials.json                # 5 SFT configurations (varying Rank, LR, Modules)
│   └── dpo_trials.json                # 5 DPO configurations (varying Beta, LR, Epochs)
├── utils/
│   ├── evaluation.py                  # BLEU + BERTScore evaluation pipeline
│   └── io_helpers.py                  # JSON state persistence & HF Hub integration
├── notebooks/
│   ├── 00_setup_and_baseline.ipynb    # Base model instantiation and evaluation
│   ├── 02_sft_trials.ipynb            # Execution of SFT trials
│   ├── 03_dpo_trials.ipynb            # Execution of DPO trials on the SFT winner
│   └── 04_final_evaluation.ipynb      # Metric aggregation and reporting
└── results/                           # Evaluation metrics (JSON/CSV)
```

## System Architecture & Persistence Strategy

The pipeline is designed to be highly resilient to ephemeral compute environments (e.g., Kaggle's 12-hour session limits) and strict VRAM constraints (16GB T4 GPU). 
1. **Atomic Disk Writes:** Trial results are written to `results/*.json` immediately. If a notebook disconnects mid-execution, existing trials are skipped upon restart.
2. **Remote State Persistence:** Winning model adapters are pushed dynamically to the HuggingFace Hub, allowing subsequent pipeline stages (like DPO) to pull the checkpoint without relying on local disk storage.

## Setup & Installation

### Prerequisites
* Python 3.12+
* HuggingFace Account with a Write Token
* GPU environment (1x NVIDIA T4 is sufficient under 4-bit quantization)

### Environment Setup
1. Clone the repository:
   ```bash
   git clone https://github.com/hashirilyas1803/daa-helper.git
   cd daa-helper
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Ensure your HuggingFace token is accessible in your environment (or set as a Kaggle Secret named `HF_TOKEN`).

## Pipeline Reproduction Workflow

The dataset for preference optimization (`data/dpo_pairs.json`) is provided pre-compiled so reproduction does not require manual LLM API calls. Execute the notebooks sequentially to reproduce the pipeline:

1. **Baseline Evaluation (`00_setup_and_baseline.ipynb`):** Loads the base TinyLlama model in 4-bit QLoRA, processes the test prompts, scores against gold answers, and establishes baseline metrics.
2. **SFT Trials (`02_sft_trials.ipynb`):** Loads `open-r1/codeforces-cots`, executes 5 varied SFT trial configurations, evaluates each against the baseline, and selects the winner based on combined BLEU/BERTScore metrics.
3. **DPO Trials (`03_dpo_trials.ipynb`):** Pulls the winning SFT adapter, loads the pre-compiled preference pairs from the `data/` directory, executes 5 DPO trials, and selects the final optimized model.
4. **Evaluation & Aggregation (`04_final_evaluation.ipynb`):** Aggregates all JSON results, compiles `comparison_table.csv`, and generates the qualitative metrics report.

## Known Issues & Technical Observations

* **OOM Constraints:** Trial 5 (Rank 64 across all modules) pushes the T4 GPU to its 16GB limit. If OOM errors occur during reproduction, reduce `per_device_train_batch_size` to 1 and increase `gradient_accumulation_steps` to 8.
* **Architecture Impact:** During SFT, MLP-only targeted trials underperformed compared to Attention-only trials, indicating that attention layers carry more stylistic adaptation signal for this specific domain.
* **DPO Divergence:** Aggressive learning rates (e.g., `5e-5` in DPO Trial 4) can lead to metric collapse and severe hallucination, which is documented as part of the hyperparameter analysis.