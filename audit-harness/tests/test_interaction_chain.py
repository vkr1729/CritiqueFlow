import json
import pytest
from core.interaction_chain import InteractionChain


def test_chain_creation():
    chain = InteractionChain("Is this model validated?")
    assert chain.user_query == "Is this model validated?"
    assert chain.steps == []
    assert chain.total_iterations == 0
    assert chain.early_stopped is False
    assert chain.final_output == ""
    assert chain.referenced_files == []


def test_chain_empty_query_raises():
    with pytest.raises(ValueError):
        InteractionChain("")
    with pytest.raises(ValueError):
        InteractionChain("   ")


def test_add_step_includes_timestamp():
    chain = InteractionChain("test query")
    chain.add_step("llm_response", "model uses Black-Scholes", 1)
    step = chain.steps[0]
    assert step["role"] == "llm_response"
    assert step["content"] == "model uses Black-Scholes"
    assert step["iteration"] == 1
    assert "timestamp" in step
    assert isinstance(step["timestamp"], str)


def test_add_step_validates_role():
    chain = InteractionChain("test")
    with pytest.raises(ValueError, match="Invalid role"):
        chain.add_step("invalid_role", "content", 1)


def test_to_dict_json_serializable():
    chain = InteractionChain("test query")
    chain.add_step("user", "hello", 1)
    chain.add_step("llm_response", "response", 1)
    chain.total_iterations = 1
    chain.final_output = "response"
    chain.referenced_files = ["doc1.xlsx", "doc2.pdf"]

    d = chain.to_dict()
    result = json.dumps(d)
    parsed = json.loads(result)
    assert parsed["user_query"] == "test query"
    assert len(parsed["steps"]) == 2
    assert parsed["total_iterations"] == 1
    assert parsed["final_output"] == "response"
    assert parsed["referenced_files"] == ["doc1.xlsx", "doc2.pdf"]


def test_to_markdown_produces_expected_sections():
    chain = InteractionChain("Audit valuation model")
    chain.add_step("llm_response", "Model uses Heston stochastic volatility.", 1)
    chain.final_output = "Model uses Heston stochastic volatility."
    chain.total_iterations = 1
    chain.early_stopped = True

    md = chain.to_markdown()
    assert "# Audit Harness" in md
    assert "Audit valuation model" in md
    assert "Total Iterations" in md
    assert "Early Stopped" in md
    assert "Yes" in md
    assert "Model uses Heston stochastic volatility" in md
    assert "Final Audit Output" in md


def test_to_markdown_includes_referenced_files():
    chain = InteractionChain("test")
    chain.referenced_files = ["risk_model.xlsx", "validation.docx"]
    chain.final_output = "done"

    md = chain.to_markdown()
    assert "Referenced Files" in md
    assert "risk_model.xlsx" in md
    assert "validation.docx" in md


def test_multiple_iterations_in_markdown():
    chain = InteractionChain("multi-iteration test")
    chain.add_step("llm_response", "response 1", 1)
    chain.add_step("evaluator_judgment", '{"sufficient": false}', 1)
    chain.add_step("harness_followup", "follow up 1", 1)
    chain.add_step("llm_response", "response 2", 2)
    chain.final_output = "response 2"
    chain.total_iterations = 2

    md = chain.to_markdown()
    assert "Step 1" in md
    assert "Step 2" in md
    assert "Step 3" in md
    assert "Step 4" in md
    assert "response 1" in md
    assert "response 2" in md
    assert "follow up 1" in md


def test_all_valid_roles_accepted():
    chain = InteractionChain("test")
    for role in ["user", "llm_response", "evaluator_judgment", "harness_followup", "final_output"]:
        chain.add_step(role, f"content for {role}", 1)
    assert len(chain.steps) == 5


def test_final_output_role_label_correct():
    chain = InteractionChain("test")
    chain.add_step("final_output", "This is the final audit result.", 1)

    md = chain.to_markdown()
    assert "Final Output" in md
