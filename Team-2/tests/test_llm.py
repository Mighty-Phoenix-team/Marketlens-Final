import json
from unittest.mock import MagicMock

import pytest

from marketlens import llm


CONTEXT = {
    "research_profile": {
        "sectors": ["Financials"],
        "research_focus": ["growth"],
        "horizon_days": 30,
    },
    "finding": {
        "symbol": "BBCA",
        "research_relevance": 6.5,
        "evidence": [
            {
                "metric": "revenue_growth",
                "value": 0.18,
                "period": "year-over-year quarter",
            }
        ],
        "limitations": [
            "Co-movement does not establish causality."
        ],
    },
}


def fake_response():
    response = MagicMock()
    response.text = json.dumps({
        "summary": "BBCA has fundamental evidence relevant to the selected research focus.",
        "why_relevant": "Revenue growth matches the selected growth focus.",
        "evidence_summary": [
            "Revenue growth is 0.18."
        ],
        "limitations": [
            "The evidence does not establish causality."
        ],
        "next_research_questions": [
            "How has revenue changed across previous periods?"
        ],
    })
    return response


def test_explain_finding(monkeypatch):
    client = MagicMock()
    client.models.generate_content.return_value = fake_response()

    monkeypatch.setattr(llm, "get_client", lambda: client)

    result = llm.explain_finding(CONTEXT)

    assert result.summary
    assert result.why_relevant
    assert result.evidence_summary
    assert result.limitations

    client.models.generate_content.assert_called_once()


def test_context_is_sent_to_model(monkeypatch):
    client = MagicMock()
    client.models.generate_content.return_value = fake_response()

    monkeypatch.setattr(llm, "get_client", lambda: client)

    llm.explain_finding(CONTEXT)

    prompt = client.models.generate_content.call_args.kwargs["contents"]

    assert "BBCA" in prompt
    assert "revenue_growth" in prompt
    assert "0.18" in prompt


def test_invalid_context():
    with pytest.raises(ValueError):
        llm.explain_finding({})


def test_empty_model_response(monkeypatch):
    client = MagicMock()
    response = MagicMock()
    response.text = ""

    client.models.generate_content.return_value = response

    monkeypatch.setattr(llm, "get_client", lambda: client)

    with pytest.raises(RuntimeError):
        llm.explain_finding(CONTEXT)


def test_parsed_response_without_text(monkeypatch):
    client = MagicMock()
    response = MagicMock()
    response.text = ""
    response.parsed = {"summary": "Recorded evidence", "why_relevant": "Matches growth focus"}
    client.models.generate_content.return_value = response
    monkeypatch.setattr(llm, "get_client", lambda: client)
    result = llm.explain_finding(CONTEXT)
    assert result.summary == "Recorded evidence"
