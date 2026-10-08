"""Offline installation smoke check; never calls Sectors or Gemini."""
import asyncio
import json
import os
from pathlib import Path
import tempfile
from unittest.mock import AsyncMock, MagicMock, patch

from marketlens import llm
from marketlens.schemas import MarketLensExplanation
from marketlens.explanation_service import ExplanationService
from evaluation.dataset import load_samples


async def verify():
    context = {"research_profile": {"research_focus": ["income"], "horizon_days": 30}, "finding": {
        "symbol": "TEST", "research_relevance": 4.17, "relevance_reason": {"matched_groups": ["income"]},
        "evidence": [{"metric": "dividend_yield_ttm", "value": .0625, "unit": "decimal_ratio", "source": "offline-test"}],
        "limitations": ["TTM exact window end and price basis unavailable."]}}
    explanation = MarketLensExplanation(summary="Offline test only.", why_relevant="Offline test only.")
    client = MagicMock()
    client.aio.models.generate_content = AsyncMock(return_value=MagicMock(parsed=explanation))
    client.aio.aclose = AsyncMock()
    with tempfile.TemporaryDirectory() as folder:
        with patch.dict(os.environ, {"MARKETLENS_EVAL_CAPTURE": "1", "MARKETLENS_EVAL_SAMPLES_DIR": folder}):
            with patch.object(llm, "get_client", return_value=client):
                service = ExplanationService()
                first = await service.get(context, llm.explain_finding_async, namespace="offline")
                second = await service.get(context, llm.explain_finding_async, namespace="offline")
                await service.close()
        samples, invalid, count = load_samples(Path(folder))
        if count != 1 or invalid or client.aio.models.generate_content.await_count != 1:
            raise RuntimeError("Capture or cache verification failed")
        if not second["explanation_meta"]["cache_hit"] or first["explanation"] != second["explanation"]:
            raise RuntimeError("Explanation cache changed")
        if samples[0]["retrieved_contexts"][0] != llm.request_arguments(context)["contents"].split("\n", 1)[1]:
            raise RuntimeError("Evidence snapshot mismatch")
        if samples[0]["request"]["system_instruction"] != llm.SYSTEM_PROMPT:
            raise RuntimeError("System prompt mismatch")
    print("PASS: exact input/output capture; cached answer is not a new sample; prompt preserved.")
    print("Sectors calls: 0; Gemini calls: 0. Temporary mock sample deleted; no quality score claimed.")


if __name__ == "__main__":
    asyncio.run(verify())
