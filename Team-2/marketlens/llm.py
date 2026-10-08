from __future__ import annotations 

import json 
import os 
from google import genai 
from google.genai import types
from marketlens.schemas import MarketLensExplanation 
from .runtime import explanation_timeout, MissingGeminiKey
from .grounding import compact_explanation_context
import hashlib
import asyncio
from .evaluation_capture import record_generation


SYSTEM_PROMPT = """
You are the explanation layer for MarketLens, an evidence-based
market research decision-support system.

Your task is to explain a structured finding produced by the
MarketLens deterministic intelligence engine.

Rules:

1. Use ONLY information contained in the supplied context.
2. Never invent numbers, facts, events, companies, or causes.
3. Numerical claims must come directly from supplied evidence.
4. Research Relevance represents relevance to the user's research
   context. It is NOT investment quality, expected return, or
   investment suitability.
5. Do not provide buy, sell, hold, or trading instructions.
6. Do not provide price targets or return predictions.
7. Do not claim that one measured variable caused another unless
   causality is explicitly established in the supplied context.
8. Explicitly communicate important limitations or unavailable data.
9. Keep the explanation concise and suitable for a research dashboard.
10. Follow the requested structured response schema.
11. Preserve the source period and unit of each metric. Decimal ratio changes
    become percentage points, not percent growth. Valuation years, financial
    years, retrieval timestamps, and associated close dates are distinct.
12. Forward PE is an estimate. Provider peer/historical differences are
    descriptive context, not proof of under/overvaluation or a winning stock.

13. Describe profitability using measured values and changes. Do not call it
    high, low, strong, weak, healthy or improving overall without an explicit
    relevant benchmark in the evidence.
14. For historical-median and peer-average comparisons use above or below.
    Reserve increased/decreased for chronological observations of one metric.
15. Use an as-of date only if that specific metric has an explicit observation
    date. Never borrow a close date, ex-dividend date or retrieval timestamp.
    For forward PE without an observation date, say that date is unavailable.
16. Report Research Relevance numerically, without strong/moderate/weak labels
    unless those categories are explicitly defined in the supplied methodology.
17. Keep TTM dividend yield, provider average yield and year-labelled totals
    separate. Do not annualize incomplete years or infer future dividends.
18. Payout and cash payout periods and denominators may be unavailable.
    Values above 100% do not alone establish sustainability or dividend safety.
    Null upcoming dividends is unavailable data, not proof of no dividend.
19. Describe matched research groups using only
    finding.relevance_reason.matched_groups.
    Available evidence groups are not necessarily matched groups.

20. Keep the summary to two sentences and why_relevant to one sentence.
    Use at most five evidence_summary bullets, prioritizing the selected
    research groups. Preserve numerical values, units and source periods.
    Consolidate overlapping limitations without dropping important
    uncertainties. Provide at most three next research questions.
21. Always retain the limitation that TTM dividend yield has an
    unavailable precise window end and price basis, when stated
    in the supplied context.

The user remains responsible for any investment decision.
"""
def model_name():
    return os.getenv("GEMINI_MODEL", "gemini-flash-latest")


def explanation_namespace():
    # Changes to the model, prompt, schema or compact input version invalidate cache.
    schema = json.dumps(MarketLensExplanation.model_json_schema(), sort_keys=True)
    return "compact-v1:" + model_name() + ":" + hashlib.sha256((SYSTEM_PROMPT + schema).encode()).hexdigest()


def get_client() -> genai.Client:
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise MissingGeminiKey("GEMINI_API_KEY environment variable is not set.")
    return genai.Client(
        api_key=api_key,
        http_options=types.HttpOptions(
            timeout=int(explanation_timeout() * 1000),
            retry_options=types.HttpRetryOptions(attempts=1),
        ),
    )


def request_arguments(context):
    if not isinstance(context, dict) or "finding" not in context:
        raise ValueError("Explanation context must contain a finding.")
    compact = compact_explanation_context(context)
    prompt = (
        "Explain this MarketLens finding. Do not perform new analysis or recalculate Research Relevance. "
        "Resolve each evidence source_ref using evidence_sources; keep its source period distinct from retrieval time.\n"
        + json.dumps(compact, ensure_ascii=False, separators=(",", ":"))
    )
    return dict(model=model_name(), contents=prompt, config=types.GenerateContentConfig(
        system_instruction=SYSTEM_PROMPT, response_mime_type="application/json",
        response_schema=MarketLensExplanation, temperature=0.2,
    ))


def parse_response(response):
    if isinstance(response.parsed, MarketLensExplanation):
        return response.parsed
    if isinstance(response.parsed, dict):
        return MarketLensExplanation.model_validate(response.parsed)
    if not response.text:
        raise RuntimeError("No response received from the model.")
    return MarketLensExplanation.model_validate_json(response.text)


def explain_finding(context: dict):
    """Synchronous compatibility entry point for existing callers."""
    arguments = request_arguments(context)
    client = get_client()
    try:
        explanation = parse_response(client.models.generate_content(**arguments))
        record_generation(context, arguments, explanation)
        return explanation
    finally:
        client.close()


async def explain_finding_async(context: dict):
    """Native async API path; the service deadline cancels the local request."""
    arguments = request_arguments(context)
    client = get_client()
    async_client = client.aio
    try:
        response = await async_client.models.generate_content(**arguments)
        explanation = parse_response(response)
        await asyncio.to_thread(record_generation, context, arguments, explanation)
        return explanation
    finally:
        try:
            await async_client.aclose()
        finally:
            client.close()
