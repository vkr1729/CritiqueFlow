import pytest
from unittest.mock import patch, MagicMock

import json


@pytest.fixture
def mock_llm_openai():
    """Mock urllib.request.urlopen to return an OpenAI-format response."""
    with patch("urllib.request.urlopen") as mock:
        mock_response = MagicMock()
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_response.read.return_value = json.dumps({
            "choices": [
                {
                    "message": {
                        "content": "The valuation model uses Black-Scholes framework."
                    }
                }
            ]
        }).encode("utf-8")
        mock.return_value = mock_response
        yield mock


@pytest.fixture
def mock_llm_anthropic():
    """Mock urllib.request.urlopen to return an Anthropic-format response."""
    with patch("urllib.request.urlopen") as mock:
        mock_response = MagicMock()
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_response.read.return_value = json.dumps({
            "content": [
                {
                    "text": "The model risk assessment identifies gaps in calibration."
                }
            ]
        }).encode("utf-8")
        mock.return_value = mock_response
        yield mock


@pytest.fixture
def mock_llm_retry_then_succeed():
    """Mock that fails once with 429 then succeeds."""
    from urllib.error import HTTPError

    fail_response = MagicMock()
    fail_response.code = 429
    fail_response.read.return_value = b'{"error": "rate limited"}'
    http_error = HTTPError("http://fake", 429, "Rate Limited", {}, fail_response)

    success_response = MagicMock()
    success_response.__enter__ = MagicMock(return_value=success_response)
    success_response.__exit__ = MagicMock(return_value=False)
    success_response.read.return_value = json.dumps({
        "choices": [{"message": {"content": "Success after retry."}}]
    }).encode("utf-8")

    with patch("urllib.request.urlopen") as mock:
        mock.side_effect = [http_error, success_response]
        yield mock


@pytest.fixture
def mock_llm_500_retry_then_succeed():
    """Mock that fails once with 500 then succeeds."""
    from urllib.error import HTTPError

    fail_response = MagicMock()
    fail_response.code = 500
    fail_response.read.return_value = b'{"error": "server error"}'
    http_error = HTTPError("http://fake", 500, "Server Error", {}, fail_response)

    success_response = MagicMock()
    success_response.__enter__ = MagicMock(return_value=success_response)
    success_response.__exit__ = MagicMock(return_value=False)
    success_response.read.return_value = json.dumps({
        "choices": [{"message": {"content": "Success after 500 retry."}}]
    }).encode("utf-8")

    with patch("urllib.request.urlopen") as mock:
        mock.side_effect = [http_error, success_response]
        yield mock


@pytest.fixture
def mock_evaluator_json():
    return json.dumps({
        "sufficient": True,
        "confidence": 0.92,
        "gaps_identified": [],
        "follow_up_challenge": None,
        "reasoning": "The response is specific and actionable."
    })


@pytest.fixture
def mock_evaluator_json_insufficient():
    return json.dumps({
        "sufficient": False,
        "confidence": 0.55,
        "gaps_identified": ["No specific regulatory framework cited", "Missing quantitative thresholds"],
        "follow_up_challenge": "Which specific regulatory framework (SR 11-7 / FRTB / PRA SS1/23) applies to this model?",
        "reasoning": "Response lacks regulatory grounding."
    })
