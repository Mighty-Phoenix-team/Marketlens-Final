"""Validate recorded input/output pairs without importing Ragas or using a key."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import tempfile
from marketlens.evaluation_capture import ROOT, SCHEMA_VERSION, canonical, render_explanation


def sample_directory():
    path = Path(os.getenv("MARKETLENS_EVAL_SAMPLES_DIR", str(ROOT / "evaluation_data" / "samples")))
    return path if path.is_absolute() else ROOT / path


def validate_sample(sample):
    if sample.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("Unsupported sample version")
    if sample.get("explanation_source") != "gemini":
        raise ValueError("Only captured Gemini explanations are evaluated; fallback is excluded")
    request, answer = sample["request"], sample["structured_response"]
    expected_id = hashlib.sha256(canonical([request, answer]).encode()).hexdigest()
    if sample.get("sample_id") != expected_id:
        raise ValueError("Sample input/output fingerprint mismatch")
    task, separator, data = request["contents"].partition("\n")
    if not separator or sample.get("retrieved_contexts") != [data]:
        raise ValueError("Context must match the actual generation request")
    compact = json.loads(data)
    if not isinstance(compact.get("finding", {}).get("evidence"), list):
        raise ValueError("Missing evidence array")
    user_input = task + "\nTicker: " + compact["finding"]["symbol"] + "\nResearch profile: " + canonical(compact.get("research_profile", {}))
    if sample.get("user_input") != user_input or sample.get("response") != render_explanation(answer):
        raise ValueError("Task or response does not match the recorded request/answer")
    if not sample["response"].strip() or sample.get("generation_model") != request["model"]:
        raise ValueError("Missing response or inconsistent model metadata")
    if sample.get("symbol") != compact["finding"]["symbol"]:
        raise ValueError("Inconsistent ticker metadata")
    return sample


def load_samples(directory, limit=5):
    unique, invalid = {}, []
    for path in sorted(Path(directory).glob("*.json")):
        try:
            sample = validate_sample(json.loads(path.read_text(encoding="utf-8-sig")))
            unique.setdefault(sample["sample_id"], sample)
        except (ValueError, KeyError, TypeError, OSError) as exc:
            invalid.append({"file": path.name, "reason": type(exc).__name__})
    ordered = sorted(unique.values(), key=lambda s: s.get("captured_at", ""), reverse=True)
    return ordered[:limit], invalid, len(ordered)


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent,
                                         delete=False, suffix=".tmp") as handle:
            temporary = Path(handle.name)
            json.dump(value, handle, ensure_ascii=False, indent=2, allow_nan=False)
        temporary.replace(path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
