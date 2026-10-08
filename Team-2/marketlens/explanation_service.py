"""Bounded explanation calls, identical-request coalescing, and safe diagnostics."""
from __future__ import annotations

import asyncio
from collections import OrderedDict
import copy
from datetime import datetime, timezone
import hashlib
import inspect
import json
import logging
import time

import httpx
from pydantic import ValidationError

from .fallback import build_fallback_explanation
from .schemas import MarketLensExplanation
from .runtime import explanation_timeout, explanation_ttl, MissingGeminiKey

logger = logging.getLogger("uvicorn.error")


def failure_reason(exc):
    code = getattr(exc, "code", None)
    code = int(code) if str(code).isdigit() else None
    if isinstance(exc, MissingGeminiKey):
        return "missing_api_key", code
    if isinstance(exc, (TimeoutError, httpx.TimeoutException)):
        return "timeout", code
    if code == 429:
        return "rate_limited", code
    if code in (401, 403):
        return "authentication", code
    if code == 404:
        return "model_unavailable", code
    if isinstance(exc, ValidationError):
        return "invalid_response", code
    if isinstance(exc, httpx.RequestError):
        return "connection_error", code
    return "provider_error", code


class ExplanationService:
    def __init__(self, *, clock=time.monotonic):
        self.clock = clock
        self.cache = OrderedDict()
        self.inflight = {}

    @staticmethod
    def key(context, namespace):
        # All evidence, timestamps, profile choices, methodology, prompt and model
        # participate: a new source observation must invalidate its explanation.
        data = json.dumps([namespace, context], sort_keys=True, ensure_ascii=False,
                          separators=(",", ":"), allow_nan=False)
        return hashlib.sha256(data.encode()).hexdigest()

    def _fallback(self, context, reason, started, code=None):
        return {
            "explanation": build_fallback_explanation(context).model_dump(),
            "explanation_source": "deterministic_fallback",
            "explanation_meta": {
                "reason": reason, "provider_status": code,
                "generation_seconds": round(self.clock() - started, 3),
                "generated_at": datetime.now(timezone.utc).isoformat(),
            },
        }

    async def get(self, context, generate, *, namespace, timeout=None):
        key = self.key(context, namespace)
        now = self.clock()
        for old in [k for k, (expiry, _) in self.cache.items() if expiry <= now]:
            self.cache.pop(old, None)
        cached = self.cache.get(key)
        if cached:
            self.cache.move_to_end(key)
            result = copy.deepcopy(cached[1])
            result["explanation_meta"].update(cache_hit=True, coalesced=False)
            return result
        shared = key in self.inflight
        if not shared:
            if len(self.inflight) >= 4:
                result = self._fallback(context, "busy", now)
                result["explanation_meta"].update(cache_hit=False, coalesced=False)
                return result
            self.inflight[key] = asyncio.create_task(self._run(
                key, context, generate, timeout if timeout is not None else explanation_timeout()))
        # A disconnected browser must not cancel another caller's identical job.
        result = copy.deepcopy(await asyncio.shield(self.inflight[key]))
        result["explanation_meta"].update(cache_hit=False, coalesced=shared)
        return result

    async def _run(self, key, context, generate, timeout):
        started = self.clock()
        try:
            async def invoke():
                if inspect.iscoroutinefunction(generate):
                    return await generate(context)
                # Retained for existing synchronous integrations and offline tests.
                value = await asyncio.to_thread(generate, context)
                return await value if inspect.isawaitable(value) else value
            try:
                explanation = await asyncio.wait_for(invoke(), timeout)
                if not isinstance(explanation, MarketLensExplanation):
                    explanation = MarketLensExplanation.model_validate(explanation)
                result = {
                    "explanation": explanation.model_dump(), "explanation_source": "gemini",
                    "explanation_meta": {
                        "reason": None, "provider_status": None,
                        "generation_seconds": round(self.clock() - started, 3),
                        "generated_at": datetime.now(timezone.utc).isoformat(),
                    },
                }
                ttl = explanation_ttl()
            except Exception as exc:
                reason, code = failure_reason(exc)
                result = self._fallback(context, reason, started, code)
                # Brief cooldown avoids repeated billable/erroring provider calls.
                ttl = min(30, explanation_ttl())
                logger.warning("MarketLens explanation fallback: symbol=%s reason=%s type=%s code=%s",
                               context["finding"].get("symbol"), reason, type(exc).__name__, code)
            if ttl > 0:
                self.cache[key] = (self.clock() + ttl, result)
                while len(self.cache) > 256:
                    self.cache.popitem(last=False)
            return result
        finally:
            self.inflight.pop(key, None)

    async def close(self):
        tasks = list(self.inflight.values())
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        self.cache.clear()
