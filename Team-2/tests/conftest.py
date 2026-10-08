"""Test runs must never add mocked answers to the user's evaluation dataset."""
import pytest


@pytest.fixture(autouse=True)
def disable_production_sample_capture(monkeypatch):
    monkeypatch.setenv("MARKETLENS_EVAL_CAPTURE", "0")
