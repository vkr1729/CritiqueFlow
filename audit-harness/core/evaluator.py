import json
import re
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

_PROMPT_DIR = Path(__file__).parent.parent / "prompts"

FALLBACK_EVALUATION = {
    "sufficient": False,
    "confidence": 0.0,
    "gaps_identified": ["Evaluator response unparseable"],
    "follow_up_challenge": "Please provide more specific detail with concrete examples, quantitative thresholds, and regulatory references where applicable.",
    "reasoning": "Parse failure - defaulting to challenge.",
}

REQUIRED_KEYS = {"sufficient", "confidence", "gaps_identified", "follow_up_challenge", "reasoning"}


def get_evaluator_criteria() -> str:
    return (_PROMPT_DIR / "evaluator_criteria.md").read_text(encoding="utf-8")


def _extract_json(response_text: str) -> dict:
    # Strategy 1: direct parse
    try:
        return json.loads(response_text)
    except json.JSONDecodeError:
        pass

    # Strategy 2: markdown code fences (with or without json tag)
    fence_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', response_text, re.DOTALL)
    if fence_match:
        try:
            return json.loads(fence_match.group(1))
        except json.JSONDecodeError:
            pass

    # Strategy 3: find JSON-like substring containing "sufficient"
    json_match = re.search(r'\{[^{}]*"sufficient"[^{}]*\}', response_text)
    if json_match:
        try:
            return json.loads(json_match.group(0))
        except json.JSONDecodeError:
            pass

    # Strategy 4: broader JSON find
    json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group(0))
        except json.JSONDecodeError:
            pass

    logger.warning("All JSON extraction strategies failed for evaluator response: %s", response_text[:200])
    return FALLBACK_EVALUATION.copy()


def evaluate_response(original_query: str, llm_response: str, iteration: int, prior_steps: list) -> dict:
    from core.llm_client import call_llm

    prior_summary = ""
    if prior_steps:
        recent = prior_steps[-4:]
        prior_summary = "\n\nPrior steps in the chain:\n"
        for step in recent:
            prior_summary += f"- [{step['role']}] (iteration {step['iteration']}): {step['content'][:300]}\n"

    messages = [
        {"role": "system", "content": get_evaluator_criteria()},
        {"role": "user", "content": (
            f"=== ORIGINAL QUERY ===\n"
            f"{original_query}\n\n"
            f"=== CURRENT LLM RESPONSE (Iteration {iteration}) ===\n"
            f"{llm_response}"
            f"{prior_summary}"
        )},
    ]

    raw = call_llm(messages, client_type="evaluator", response_format={"type": "json_object"})
    parsed = _extract_json(raw)

    for key in REQUIRED_KEYS:
        if key not in parsed:
            parsed[key] = FALLBACK_EVALUATION[key]

    return parsed
