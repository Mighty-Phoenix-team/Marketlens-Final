"""Explicit Gemini adapter for the pinned Ragas 0.4.3 metric API.

Ragas generates and parses its own assessment prompts. This adapter only
transports them to Gemini; it neither invents scores nor uses OpenAI services.
"""
from __future__ import annotations

import json
import asyncio
import time
from google import genai
from google.genai import types
from langchain_core.outputs import Generation, LLMResult
from ragas.llms.base import BaseRagasLLM
from ragas.run_config import RunConfig
from .errors import provider_diagnostic


class JudgeBudgetExceeded(RuntimeError):
    pass


class GeminiJudge(BaseRagasLLM):
    def __init__(self, api_key, model, *, timeout=90, max_calls=30, client=None, retry_delay=1.5):
        super().__init__(run_config=RunConfig(timeout=timeout, max_retries=1, max_workers=1))
        self.model = model
        self.max_calls = max_calls
        self.calls = 0
        self.metric_calls = 0
        self.trace = []
        self.retry_delay = max(0, min(10, retry_delay))
        self.client = client or genai.Client(api_key=api_key, http_options=types.HttpOptions(
            timeout=int(timeout * 1000), retry_options=types.HttpRetryOptions(attempts=1)))

    def begin_metric(self):
        self.trace = []
        self.metric_calls = 0

    def _reserve(self):
        if self.calls >= self.max_calls or self.metric_calls >= 4:
            raise JudgeBudgetExceeded("Evaluator call budget reached")
        self.calls += 1
        self.metric_calls += 1

    def _config(self, stop):
        return types.GenerateContentConfig(
            temperature=0, max_output_tokens=32768,
            response_mime_type="application/json", stop_sequences=stop,
            automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
        )

    def _record_failure(self, exc, attempt):
        diagnostic = provider_diagnostic(exc)
        retry = (attempt == 0 and diagnostic["http_code"] in {500, 502, 503, 504}
                 and self.calls < self.max_calls and self.metric_calls < 4)
        self.trace.append({"provider_error": diagnostic, "retry_scheduled": retry})
        # The Google SDK warning is unrelated to the actual HTTP failure.
        print("  Evaluator request failed: " + diagnostic["type"]
              + f" HTTP={diagnostic['http_code'] or 'unavailable'}"
              + f" status={diagnostic['provider_status'] or 'unavailable'}"
              + ("; retry 1/1" if retry else "; no automatic retry"), flush=True)
        return retry

    def _generation(self, response):
        candidates = getattr(response, "candidates", None) or []
        reason = getattr(candidates[0], "finish_reason", None) if candidates else None
        finished = getattr(reason, "value", reason) == "STOP"
        text = response.text or ""
        try:
            parsed = json.loads(text)
        except (ValueError, TypeError):
            parsed = {"parse_error": True}
        self.trace.append({"output": parsed, "model_version": getattr(response, "model_version", None),
                           "finished": finished})
        return Generation(text=text, generation_info={"finished": finished})

    def generate_text(self, prompt, n=1, temperature=0, stop=None, callbacks=None):
        results = []
        for _ in range(n):
            for attempt in range(2):
                self._reserve()
                try:
                    result = self.client.models.generate_content(model=self.model, contents=prompt.to_string(),
                                                                 config=self._config(stop))
                    break
                except Exception as exc:
                    if not self._record_failure(exc, attempt):
                        raise
                    time.sleep(self.retry_delay)
            results.append(self._generation(result))
        return LLMResult(generations=[results])

    async def agenerate_text(self, prompt, n=1, temperature=0, stop=None, callbacks=None):
        results = []
        for _ in range(n):
            for attempt in range(2):
                self._reserve()
                try:
                    result = await self.client.aio.models.generate_content(
                        model=self.model, contents=prompt.to_string(), config=self._config(stop))
                    break
                except Exception as exc:
                    if not self._record_failure(exc, attempt):
                        raise
                    await asyncio.sleep(self.retry_delay)
            results.append(self._generation(result))
        return LLMResult(generations=[results])

    def is_finished(self, response):
        return all(g.generation_info.get("finished", False) for group in response.generations for g in group)

    async def close(self):
        try:
            await self.client.aio.aclose()
        finally:
            self.client.close()


def make_metrics(judge, *, include_profile=True):
    # Pinned API: explicit LLM, no default embedding/client and no implicit provider.
    from ragas.metrics import Faithfulness, AspectCritic
    from .criteria import LIMITATION_RETENTION, PROFILE_ALIGNMENT

    metrics = {
        "faithfulness": Faithfulness(llm=judge),
        "limitation_retention": AspectCritic(name="limitation_retention", definition=LIMITATION_RETENTION,
                                             llm=judge, strictness=1),
    }
    if include_profile:
        metrics["profile_alignment"] = AspectCritic(name="profile_alignment", definition=PROFILE_ALIGNMENT,
                                                    llm=judge, strictness=1)
    return metrics
