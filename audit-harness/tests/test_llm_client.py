import json
import pytest
from unittest.mock import patch, MagicMock
from urllib.error import HTTPError
from core.llm_client import call_llm, call_llm_raw, _extract_content


def test_call_llm_openai_format(mock_llm_openai):
    result = call_llm([{"role": "user", "content": "Test"}])
    assert "Black-Scholes" in result


def test_call_llm_anthropic_format(mock_llm_anthropic):
    result = call_llm([{"role": "user", "content": "Test"}])
    assert "calibration" in result


def test_call_llm_raw(mock_llm_openai):
    result = call_llm_raw("Direct prompt test")
    assert "Black-Scholes" in result


def test_retry_on_429(mock_llm_retry_then_succeed):
    result = call_llm([{"role": "user", "content": "Test"}])
    assert "Success after retry" in result


def test_retry_on_500(mock_llm_500_retry_then_succeed):
    result = call_llm([{"role": "user", "content": "Test"}])
    assert "Success after 500 retry" in result


def test_timeout_raises_runtime_error():
    with patch("urllib.request.urlopen", side_effect=TimeoutError("timed out")):
        with pytest.raises(RuntimeError, match="timed out"):
            call_llm([{"role": "user", "content": "Test"}])


def test_oserror_raises_runtime_error():
    with patch("urllib.request.urlopen", side_effect=OSError("connection reset")):
        with pytest.raises(RuntimeError, match="connection reset"):
            call_llm([{"role": "user", "content": "Test"}])


def test_http_error_non_retryable():
    fail_response = MagicMock()
    fail_response.code = 400
    fail_response.read.return_value = b'{"error": "bad request"}'
    http_error = HTTPError("http://fake", 400, "Bad Request", {}, fail_response)

    with patch("urllib.request.urlopen", side_effect=http_error):
        with pytest.raises(RuntimeError, match="LLM HTTP 400"):
            call_llm([{"role": "user", "content": "Test"}])


def test_json_parse_failure():
    with patch("urllib.request.urlopen") as mock:
        mock_response = MagicMock()
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_response.read.return_value = b"not valid json"
        mock.return_value = mock_response

        with pytest.raises(RuntimeError, match="Failed to parse"):
            call_llm([{"role": "user", "content": "Test"}])


def test_unknown_response_format():
    with patch("urllib.request.urlopen") as mock:
        mock_response = MagicMock()
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_response.read.return_value = b'{"weird_key": "no choices or content here"}'
        mock.return_value = mock_response

        with pytest.raises(RuntimeError, match="Unknown LLM response format"):
            call_llm([{"role": "user", "content": "Test"}])


def test_extract_content_openai():
    body = json.dumps({"choices": [{"message": {"content": "test output"}}]})
    result = _extract_content(body)
    assert result == "test output"


def test_extract_content_anthropic():
    body = json.dumps({"content": [{"text": "anthropic output"}]})
    result = _extract_content(body)
    assert result == "anthropic output"


def test_call_llm_evaluator_client_type_uses_evaluator_endpoint():
    with patch("urllib.request.urlopen") as mock:
        mock_response = MagicMock()
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_response.read.return_value = json.dumps({
            "choices": [{"message": {"content": "evaluator output"}}]
        }).encode("utf-8")
        mock.return_value = mock_response

        from config.settings import settings
        settings.EVALUATOR_ENDPOINT = "https://api.groq.com/openai/v1/chat/completions"
        settings.EVALUATOR_API_KEY = "gsk_secret_evaluator_key"
        settings.EVALUATOR_MODEL = "llama-3.3-70b"

        result = call_llm([{"role": "user", "content": "Evaluate this."}], client_type="evaluator")

        assert "evaluator output" in result
        req = mock.call_args[0][0]
        assert "api.groq.com" in req.full_url
        assert "Bearer gsk_secret_evaluator_key" in req.headers.get("Authorization", "")

        settings.EVALUATOR_ENDPOINT = ""
        settings.EVALUATOR_API_KEY = ""
        settings.EVALUATOR_MODEL = ""


def test_call_llm_evaluator_falls_back_to_generator():
    with patch("urllib.request.urlopen") as mock:
        mock_response = MagicMock()
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_response.read.return_value = json.dumps({
            "choices": [{"message": {"content": "fallback output"}}]
        }).encode("utf-8")
        mock.return_value = mock_response

        from config.settings import settings
        settings.EVALUATOR_ENDPOINT = ""
        settings.EVALUATOR_API_KEY = ""
        settings.EVALUATOR_MODEL = ""

        result = call_llm([{"role": "user", "content": "Evaluate this."}], client_type="evaluator")

        assert "fallback output" in result
        req = mock.call_args[0][0]
        assert settings.LLM_ENDPOINT in req.full_url


def test_call_llm_includes_response_format():
    with patch("urllib.request.urlopen") as mock:
        mock_response = MagicMock()
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_response.read.return_value = json.dumps({
            "choices": [{"message": {"content": "structured output"}}]
        }).encode("utf-8")
        mock.return_value = mock_response

        result = call_llm([{"role": "user", "content": "Test."}],
                          response_format={"type": "json_object"})

        assert "structured output" in result
        req = mock.call_args[0][0]
        body = json.loads(req.data.decode("utf-8"))
        assert body.get("response_format") == {"type": "json_object"}
