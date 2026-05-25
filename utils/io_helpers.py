"""
IO helpers - all results persist to JSON on disk + optionally pushed to HF Hub.
This guards against Kaggle session loss and accidental cell re-runs.
"""

import json
import os
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, Optional


def get_project_root() -> Path:
    """Return the project root, working both locally and on Kaggle."""
    candidates = [
        Path("/kaggle/working/daa-helper"),  # Kaggle
        Path.cwd().parent,                    # If running from notebooks/
        Path.cwd()                            # If running from root
    ]
    for c in candidates:
        if (c / "configs").exists():
            return c
    # Fallback: create in cwd
    return Path.cwd()


def save_json(data: Any, relative_path: str, results_dir: str = "results") -> Path:
    """
    Save data as JSON under the project's results directory.
    Returns the full path saved to. Adds a timestamp inside the JSON.
    """
    root = get_project_root()
    full_dir = root / results_dir
    full_dir.mkdir(parents=True, exist_ok=True)
    full_path = full_dir / relative_path

    # Add metadata if dict
    if isinstance(data, dict):
        data = {**data, "_saved_at": datetime.utcnow().isoformat()}

    full_path.parent.mkdir(parents=True, exist_ok=True)
    with open(full_path, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"[saved] {full_path}")
    return full_path


def load_json(relative_path: str, base_dir: str = "results") -> Dict:
    """Load a JSON file from the project."""
    root = get_project_root()
    full_path = root / base_dir / relative_path
    if not full_path.exists():
        # Try data dir too
        alt = root / "data" / Path(relative_path).name
        if alt.exists():
            full_path = alt
        else:
            raise FileNotFoundError(f"Not found: {full_path}")
    with open(full_path, "r") as f:
        return json.load(f)


def push_to_hf_hub(local_dir: str, repo_id: str, repo_type: str = "model",
                   commit_message: str = "Update", private: bool = True) -> str:
    """
    Push a local folder (model adapter or results) to the HuggingFace Hub.
    Requires HF_TOKEN env var or prior huggingface-cli login.
    """
    from huggingface_hub import HfApi, create_repo

    api = HfApi()
    try:
        create_repo(repo_id, repo_type=repo_type, private=private, exist_ok=True)
    except Exception as e:
        print(f"[hf hub] repo create note: {e}")

    api.upload_folder(
        folder_path=local_dir,
        repo_id=repo_id,
        repo_type=repo_type,
        commit_message=commit_message
    )
    url = f"https://huggingface.co/{repo_id}"
    print(f"[hf hub] pushed -> {url}")
    return url


def save_trial_result(trial_name: str, stage: str, config: Dict,
                      eval_results: Dict, train_metrics: Dict,
                      sample_responses: list) -> Path:
    """
    Standardized format for saving any trial result (SFT or DPO).
    stage: 'baseline', 'sft', or 'dpo'
    """
    record = {
        "trial_name": trial_name,
        "stage": stage,
        "config": config,
        "evaluation": eval_results,
        "training_metrics": train_metrics,
        "sample_responses": sample_responses,
        "_saved_at": datetime.utcnow().isoformat()
    }
    return save_json(record, f"{stage}_{trial_name}.json")


def list_existing_results(stage: str = None) -> list:
    """List which results files already exist - useful for resuming."""
    root = get_project_root()
    results_dir = root / "results"
    if not results_dir.exists():
        return []
    pattern = f"{stage}_*.json" if stage else "*.json"
    return sorted([p.name for p in results_dir.glob(pattern)])
