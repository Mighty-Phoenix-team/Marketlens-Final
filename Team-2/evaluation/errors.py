"""Safe provider diagnostics. Never persist raw exception messages or bodies."""
from __future__ import annotations

ALLOWED_STATUS = {
    "INTERNAL", "UNAVAILABLE", "DEADLINE_EXCEEDED", "RESOURCE_EXHAUSTED",
    "INVALID_ARGUMENT", "FAILED_PRECONDITION", "NOT_FOUND", "PERMISSION_DENIED",
    "UNAUTHENTICATED", "ABORTED", "CANCELLED", "UNKNOWN", "UNIMPLEMENTED",
}


def provider_diagnostic(exc):
    code = getattr(exc, "code", None)
    try:
        code = int(code) if not isinstance(code, bool) else None
    except (ValueError, TypeError):
        code = None
    if code is not None and not 100 <= code <= 599:
        code = None
    status = getattr(exc, "status", None)
    status = status if isinstance(status, str) and status in ALLOWED_STATUS else None
    return {"type": type(exc).__name__, "http_code": code, "provider_status": status}


def error_label(exc):
    diagnostic = provider_diagnostic(exc)
    code, status = diagnostic["http_code"], diagnostic["provider_status"]
    if code == 429:
        return "rate_limited"
    if code in (401, 403):
        return "authentication"
    if code == 404:
        return "model_unavailable"
    if code is not None and 500 <= code <= 599:
        return f"server_error_{code}" + (f"_{status}" if status else "")
    if isinstance(exc, TimeoutError):
        return "timeout"
    if type(exc).__name__ == "JudgeBudgetExceeded":
        return "call_budget_reached"
    if type(exc).__name__ == "ServerError":
        return "server_error"
    if code is not None:
        return f"provider_error_{code}" + (f"_{status}" if status else "")
    return type(exc).__name__


def stops_run(reason):
    return reason in {"rate_limited", "authentication", "model_unavailable", "call_budget_reached"} or (
        isinstance(reason, str) and (reason.startswith("server_error") or reason.startswith("provider_error_4")))
