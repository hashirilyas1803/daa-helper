"""
Shared evaluation utilities for the DAA Helper project.
Computes BLEU and BERTScore for model responses vs gold answers.
"""

import json
import os
from pathlib import Path
from typing import List, Dict, Any
import torch
import gc


def compute_bleu(prediction: str, reference: str) -> float:
    """Compute corpus-level BLEU using sacrebleu (smoothed)."""
    from sacrebleu import sentence_bleu
    score = sentence_bleu(prediction, [reference]).score
    return float(score)


def compute_bertscore(predictions: List[str], references: List[str],
                     model_type: str = "roberta-large",
                     device: str = None) -> Dict[str, List[float]]:
    """Compute BERTScore P/R/F1 for a list of predictions vs references."""
    from bert_score import score as bert_score_fn

    if device is None:
        device = "cuda" if torch.cuda.is_available() else "cpu"

    P, R, F1 = bert_score_fn(
        predictions, references,
        model_type=model_type,
        device=device,
        verbose=False,
        rescale_with_baseline=False
    )
    return {
        "precision": P.tolist(),
        "recall": R.tolist(),
        "f1": F1.tolist()
    }


def evaluate_responses(predictions: List[str], references: List[str]) -> Dict[str, Any]:
    """
    Compute per-prompt BLEU + BERTScore and aggregate stats.

    Returns dict with:
      - per_prompt: list of {bleu, bertscore_f1} for each prompt
      - aggregate: {mean_bleu, mean_bertscore_f1, combined_score}
    """
    assert len(predictions) == len(references), \
        f"Mismatch: {len(predictions)} predictions vs {len(references)} references"

    # BLEU per prompt
    bleu_scores = [compute_bleu(p, r) for p, r in zip(predictions, references)]

    # BERTScore in one batch
    bs = compute_bertscore(predictions, references)
    f1_scores = bs["f1"]

    per_prompt = [
        {
            "bleu": bleu_scores[i],
            "bertscore_precision": bs["precision"][i],
            "bertscore_recall": bs["recall"][i],
            "bertscore_f1": f1_scores[i]
        }
        for i in range(len(predictions))
    ]

    mean_bleu = sum(bleu_scores) / len(bleu_scores)
    mean_f1 = sum(f1_scores) / len(f1_scores)
    # Combined score: weighted mean. BLEU is 0-100, BERTScore F1 is ~0-1, so normalize.
    # Tie-breaker rule per assignment uses validation loss separately.
    combined = 0.5 * (mean_bleu / 100.0) + 0.5 * mean_f1

    aggregate = {
        "mean_bleu": mean_bleu,
        "mean_bertscore_f1": mean_f1,
        "mean_bertscore_precision": sum(bs["precision"]) / len(bs["precision"]),
        "mean_bertscore_recall": sum(bs["recall"]) / len(bs["recall"]),
        "combined_score": combined,
        "n_prompts": len(predictions)
    }

    return {"per_prompt": per_prompt, "aggregate": aggregate}


def run_inference_on_prompts(model, tokenizer, prompts: List[str],
                              max_new_tokens: int = 512,
                              temperature: float = 0.7,
                              system_prompt: str = None) -> List[str]:
    """Run model inference on a list of prompts. Uses chat template if available."""
    model.eval()
    responses = []

    default_system = ("You are a Design and Analysis of Algorithms (DAA) tutor. "
                     "Guide the student through the problem step by step. "
                     "Help them understand the reasoning rather than just giving the final answer "
                     "unless explicitly asked for the solution.")
    sys = system_prompt or default_system

    for prompt in prompts:
        messages = [
            {"role": "system", "content": sys},
            {"role": "user", "content": prompt}
        ]
        try:
            input_text = tokenizer.apply_chat_template(
                messages, tokenize=False, add_generation_prompt=True
            )
        except Exception:
            input_text = f"{sys}\n\nUser: {prompt}\n\nAssistant:"

        inputs = tokenizer(input_text, return_tensors="pt", truncation=True,
                          max_length=2048).to(model.device)

        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                max_new_tokens=max_new_tokens,
                temperature=temperature,
                do_sample=(temperature > 0),
                pad_token_id=tokenizer.pad_token_id or tokenizer.eos_token_id,
                eos_token_id=tokenizer.eos_token_id
            )

        response = tokenizer.decode(
            outputs[0][inputs["input_ids"].shape[1]:],
            skip_special_tokens=True
        ).strip()
        responses.append(response)

    return responses


def free_memory():
    """Aggressively free GPU memory."""
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
        torch.cuda.synchronize()
