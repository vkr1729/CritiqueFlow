import json
import pytest
from unittest.mock import patch
from core.harness_engine import run_harness


def test_early_convergence_sufficient():
    with patch("core.harness_engine.call_llm", return_value="Black-Scholes analysis complete."), \
         patch("core.harness_engine.evaluate_response", return_value={
             "sufficient": True,
             "confidence": 0.92,
             "gaps_identified": [],
             "follow_up_challenge": None,
             "reasoning": "Comprehensive."
         }):
        chain = run_harness("Audit the options pricing model.")
        assert chain.total_iterations == 1
        assert chain.early_stopped is True
        assert "Black-Scholes" in chain.final_output


def test_max_depth_exhaustion():
    insufficient = {
        "sufficient": False,
        "confidence": 0.4,
        "gaps_identified": ["Missing regulatory citation"],
        "follow_up_challenge": "Which SR 11-7 section applies?",
        "reasoning": "Not specific enough."
    }

    with patch("core.harness_engine.call_llm", return_value="Generic model response."), \
         patch("core.harness_engine.evaluate_response", return_value=insufficient):
        chain = run_harness("Audit VaR model.")
        assert chain.total_iterations == 3
        assert chain.early_stopped is False
        assert len(chain.steps) > 3


def test_confidence_threshold_early_stop():
    """Confidence >= 0.85 with sufficient=False should still stop."""
    high_confidence = {
        "sufficient": False,
        "confidence": 0.90,
        "gaps_identified": ["Minor gap"],
        "follow_up_challenge": "Small refinement needed.",
        "reasoning": "Almost there."
    }

    with patch("core.harness_engine.call_llm", return_value="Detailed analysis."), \
         patch("core.harness_engine.evaluate_response", return_value=high_confidence):
        chain = run_harness("Audit credit risk model.")
        assert chain.total_iterations == 1
        assert chain.early_stopped is True


def test_confidence_below_threshold_continues():
    """Confidence < 0.85 with sufficient=False should continue."""
    low_confidence = {
        "sufficient": False,
        "confidence": 0.60,
        "gaps_identified": ["Significant gaps"],
        "follow_up_challenge": "More detail needed on calibration.",
        "reasoning": "Inadequate."
    }

    with patch("core.harness_engine.call_llm", return_value="Shallow analysis."), \
         patch("core.harness_engine.evaluate_response", return_value=low_confidence):
        chain = run_harness("Audit model.")
        assert chain.total_iterations == 3


def test_file_context_injection():
    file_contents = {
        "model_doc.md": "# Valuation Model v2.0\nThis document describes the pricing model.",
        "risk_data.xlsx": "Model | VaR | Status\nHeston | 0.05 | Pass",
    }

    class CapturingMock:
        def __init__(self):
            self.calls = []

        def __call__(self, messages):
            self.calls.append(messages)
            return "Analysis with documents."

    mock_llm = CapturingMock()

    with patch("core.harness_engine.call_llm", mock_llm), \
         patch("core.harness_engine.evaluate_response", return_value={
             "sufficient": True,
             "confidence": 0.95,
             "gaps_identified": [],
             "follow_up_challenge": None,
             "reasoning": "Good."
         }):
        chain = run_harness("Audit the valuation model.", file_contents=file_contents)
        assert chain.referenced_files == ["model_doc.md", "risk_data.xlsx"]
        first_call_messages = mock_llm.calls[0]
        user_messages = [m["content"] for m in first_call_messages if m["role"] == "user"]
        assert any("REFERENCE DOCUMENTS" in m for m in user_messages)
        assert any("[Document: model_doc.md]" in m for m in user_messages)
        assert any("[Document: risk_data.xlsx]" in m for m in user_messages)


def test_chain_completeness():
    sufficient = {
        "sufficient": True,
        "confidence": 0.92,
        "gaps_identified": [],
        "follow_up_challenge": None,
        "reasoning": "Complete."
    }

    with patch("core.harness_engine.call_llm", return_value="Full audit response."), \
         patch("core.harness_engine.evaluate_response", return_value=sufficient):
        chain = run_harness("Test query.")

        roles_seen = {step["role"] for step in chain.steps}
        assert "user" in roles_seen
        assert "llm_response" in roles_seen
        assert "evaluator_judgment" in roles_seen
        assert "final_output" in roles_seen

        iterations = {step["iteration"] for step in chain.steps}
        assert 0 in iterations


def test_last_iteration_convergence():
    """When it converges on the very last iteration, early_stopped should be False."""
    call_count = [0]

    def mock_evaluate(*args, **kwargs):
        call_count[0] += 1
        if call_count[0] == 2:
            return {
                "sufficient": True,
                "confidence": 0.95,
                "gaps_identified": [],
                "follow_up_challenge": None,
                "reasoning": "Now complete."
            }
        return {
            "sufficient": False,
            "confidence": 0.4,
            "gaps_identified": ["Incomplete"],
            "follow_up_challenge": "More detail needed.",
            "reasoning": "Not enough."
        }

    with patch("core.harness_engine.call_llm", return_value="Response."), \
         patch("core.harness_engine.evaluate_response", side_effect=mock_evaluate):
        chain = run_harness("Test.")
        assert chain.total_iterations == 2
        assert chain.early_stopped is True
