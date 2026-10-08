"""Capture successful generations locally. No evaluator or network calls here."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import logging
import os
from pathlib import Path
import tempfile

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_VERSION = "marketlens-evaluation-v1"
logger = logging.getLogger("uvicorn.error")


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def render_explanation(explanation):
    """The whole user-visible explanation, including follow-up questions."""
    parts = [explanation.get("summary", ""), "Why it is relevant", explanation.get("why_relevant", "")]
    for key, title in [("evidence_summary", "Evidence used"), ("limitations", "Limitations"),
                       ("next_research_questions", "Further research")]:
        parts.append(title)
        parts.extend("- " + item for item in explanation.get(key, []))
    return "\n".join(parts)


def build_sample(context, arguments, explanation):
    # Extract from the ACTUAL request body, rather than fetching/rebuilding data later.
    task, separator, data = arguments["contents"].partition("\n")
    if not separator:
        raise ValueError("Missing structured generation context")
    compact = json.loads(data)
    system_prompt = arguments["config"].system_instruction
    if not isinstance(system_prompt, str):
        raise ValueError("Expected text system instruction")
    answer = explanation.model_dump() if hasattr(explanation, "model_dump") else dict(explanation)
    original_request = {"model": arguments["model"], "system_instruction": system_prompt,
                        "contents": arguments["contents"]}
    sample_id = hashlib.sha256(canonical([original_request, answer]).encode()).hexdigest()
    finding = compact["finding"]
    # This describes the pre-existing task; it is not inferred from the answer.
    user_input = (task + "\nTicker: " + finding["symbol"] + "\nResearch profile: "
                  + canonical(compact.get("research_profile", {})))
    return {
        "schema_version": SCHEMA_VERSION, "sample_id": sample_id,
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "explanation_source": "gemini", "symbol": finding["symbol"],
        "generation_model": arguments["model"],
        "methodology_version": finding.get("methodology_version"),
        "user_input": user_input, "retrieved_contexts": [data],
        "response": render_explanation(answer), "structured_response": answer,
        "request": original_request,
    }


def record_generation(context, arguments, explanation):
    """Best effort: recording failure must never turn a Gemini answer into fallback."""
    if os.getenv("MARKETLENS_EVAL_CAPTURE", "1").lower() in {"0", "false", "no", "off"}:
        return None
    temporary = None
    try:
        sample = build_sample(context, arguments, explanation)
        directory = Path(os.getenv("MARKETLENS_EVAL_SAMPLES_DIR", str(ROOT / "evaluation_data" / "samples")))
        if not directory.is_absolute():
            directory = ROOT / directory
        directory.mkdir(parents=True, exist_ok=True)
        target = directory / (sample["sample_id"] + ".json")
        if target.exists():
            return sample["sample_id"]
        # Atomic replacement: an evaluator never sees a half-written sample.
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=directory,
                                         suffix=".tmp", delete=False) as handle:
            temporary = Path(handle.name)
            handle.write(json.dumps(sample, ensure_ascii=False, indent=2, allow_nan=False))
        temporary.replace(target)
        logger.info("MarketLens evaluation sample saved: symbol=%s id=%s", sample["symbol"], sample["sample_id"][:12])
        return sample["sample_id"]
    except Exception as exc:
        logger.warning("MarketLens evaluation capture failed: type=%s; explanation preserved", type(exc).__name__)
        return None
    finally:
        if temporary is not None:
            try:
                temporary.unlink(missing_ok=True)
            except OSError:
                pass
