import json
import pytest
from unittest.mock import patch, MagicMock
from core.evaluator import evaluate_response, _extract_json, get_evaluator_criteria


def test_extract_json_direct():
    raw = '{"sufficient": true, "confidence": 0.9, "gaps_identified": [], "follow_up_challenge": null, "reasoning": "good"}'
    result = _extract_json(raw)
    assert result["sufficient"] is True
    assert result["confidence"] == 0.9


def test_extract_json_fenced_with_lang():
    raw = '```json\n{"sufficient": false, "confidence": 0.5, "gaps_identified": ["gap1"], "follow_up_challenge": "detail needed", "reasoning": "not enough"}\n```'
    result = _extract_json(raw)
    assert result["sufficient"] is False
    assert result["confidence"] == 0.5


def test_extract_json_fenced_no_lang():
    raw = '```\n{"sufficient": true, "confidence": 0.95, "gaps_identified": [], "follow_up_challenge": null, "reasoning": "excellent"}\n```'
    result = _extract_json(raw)
    assert result["sufficient"] is True
    assert result["confidence"] == 0.95


def test_extract_json_fallback_unparseable():
    raw = "This is not JSON at all. Just random text."
    result = _extract_json(raw)
    assert result["sufficient"] is False
    assert result["confidence"] == 0.0
    assert "unparseable" in result["gaps_identified"][0]


def test_evaluate_response_sufficient():
    evaluator_json = json.dumps({
        "sufficient": True,
        "confidence": 0.92,
        "gaps_identified": [],
        "follow_up_challenge": None,
        "reasoning": "Comprehensive and specific."
    })

    with patch("core.llm_client.call_llm_raw", return_value=evaluator_json):
        result = evaluate_response(
            "Audit the VaR model",
            "The VaR model uses historical simulation...",
            1,
            []
        )
        assert result["sufficient"] is True
        assert result["confidence"] == 0.92
        assert "sufficient" in result
        assert "confidence" in result
        assert "gaps_identified" in result
        assert "follow_up_challenge" in result
        assert "reasoning" in result


def test_evaluate_response_insufficient():
    evaluator_json = json.dumps({
        "sufficient": False,
        "confidence": 0.55,
        "gaps_identified": ["No regulatory citation"],
        "follow_up_challenge": "Which SR 11-7 section applies?",
        "reasoning": "Missing regulatory grounding."
    })

    with patch("core.llm_client.call_llm_raw", return_value=evaluator_json):
        result = evaluate_response(
            "Audit VaR model",
            "Generic response...",
            1,
            []
        )
        assert result["sufficient"] is False
        assert result["confidence"] == 0.55


def test_evaluate_response_prior_steps_in_prompt():
    evaluator_json = json.dumps({
        "sufficient": True,
        "confidence": 0.91,
        "gaps_identified": [],
        "follow_up_challenge": None,
        "reasoning": "Good."
    })

    prior = [
        {"role": "llm_response", "iteration": 1, "content": "Prior response content here."},
    ]

    with patch("core.llm_client.call_llm_raw") as mock_llm:
        mock_llm.return_value = evaluator_json
        evaluate_response("test query", "current response", 2, prior)

        call_args = mock_llm.call_args[0][0]
        assert "test query" in call_args
        assert "current response" in call_args
        assert "Prior steps" in call_args
        assert "Prior response content" in call_args


def test_prompt_file_loaded():
    criteria = get_evaluator_criteria()
    assert len(criteria) > 100
    assert "sufficient" in criteria


def test_extract_json_fallback_returns_copy():
    """BF-1: Verify _extract_json returns a copy of FALLBACK_EVALUATION, not the global."""
    from core.evaluator import FALLBACK_EVALUATION
    result1 = _extract_json("completely unparseable garbage text")
    result2 = _extract_json("also unparseable text here")
    # Must be different objects
    assert result1 is not FALLBACK_EVALUATION
    assert result2 is not FALLBACK_EVALUATION
    assert result1 is not result2
    # Mutating result must not corrupt global
    result1["confidence"] = 999
    assert FALLBACK_EVALUATION["confidence"] == 0.0
