import json
import logging
import uuid
from pathlib import Path
from core.interaction_chain import InteractionChain
from core.llm_client import call_llm, call_llm_raw
from core.evaluator import evaluate_response

logger = logging.getLogger(__name__)

_PROMPT_DIR = Path(__file__).parent.parent / "prompts"


def get_auditor_prompt() -> str:
    base = (_PROMPT_DIR / "system_auditor.md").read_text(encoding="utf-8")
    try:
        from core.session_store import list_learned_skills
        skills = list_learned_skills(active_only=True)
        if skills:
            base += "\n\n--- LEARNED SKILLS ---\n"
            for s in skills:
                base += f"- {s['skill_text']}\n"
    except Exception:
        logger.warning("Failed to load learned skills for auditor prompt", exc_info=True)
        pass
    return base


def run_harness(user_query: str, file_contents: dict = None,
                session_id: str = None, folder_path: str = "") -> InteractionChain:
    from config.settings import settings

    chain = InteractionChain(user_query)
    chain.add_step("user", user_query, 0)

    messages = [
        {"role": "system", "content": get_auditor_prompt()},
    ]

    chain.referenced_files = []
    compaction_summary = ""

    if session_id:
        try:
            from core.session_store import load_session
            prior = load_session(session_id)
            prior_chain = prior.get("chain", {})
            prior_final = prior_chain.get("final_output", "")
            if prior_final:
                compact_prompt = (
                    "Summarize the key findings and outstanding gaps from this "
                    "prior audit analysis in 500 words or less:\n\n"
                    f"{prior_final}"
                )
                compaction_summary = call_llm_raw(compact_prompt)
            prior_files = prior_chain.get("referenced_files", [])
            chain.referenced_files = list(prior_files)
            prior_folder = prior.get("folder_path", "")
            if prior_folder:
                folder_path = prior_folder
        except Exception as e:
            logger.warning("Failed to load prior session %s: %s", session_id, e)

    user_content = user_query
    prefix_parts = []

    if file_contents:
        ref_parts = ["REFERENCE DOCUMENTS:\n"]
        for fname, text in file_contents.items():
            chain.referenced_files.append(fname)
            ref_parts.append(f"[Document: {fname}]\n{text}\n")
        ref_parts.append("---\n")
        prefix_parts.append("".join(ref_parts))

    if compaction_summary:
        prefix_parts.insert(0, f"PRIOR AUDIT CONTEXT:\n{compaction_summary}\n\n---\n")

    if prefix_parts:
        user_content = "".join(prefix_parts) + user_query

    messages.append({"role": "user", "content": user_content})

    llm_response = ""
    for iteration in range(1, settings.MAX_ITERATION_DEPTH + 1):
        logger.info("Harness iteration %d/%d", iteration, settings.MAX_ITERATION_DEPTH)

        llm_response = call_llm(messages)
        chain.add_step("llm_response", llm_response, iteration)

        evaluation = evaluate_response(user_query, llm_response, iteration, chain.steps)
        chain.add_step("evaluator_judgment", json.dumps(evaluation, indent=2), iteration)

        if evaluation["sufficient"] is True or evaluation["confidence"] >= settings.EARLY_STOP_CONFIDENCE:
            chain.final_output = llm_response
            chain.early_stopped = (iteration < settings.MAX_ITERATION_DEPTH)
            chain.total_iterations = iteration
            logger.info("Harness converged at iteration %d (sufficient=%s, confidence=%.2f)",
                        iteration, evaluation["sufficient"], evaluation["confidence"])
            break

        follow_up = evaluation["follow_up_challenge"]
        if not follow_up:
            follow_up = "Please provide more specific detail with concrete examples, quantitative thresholds, and regulatory references."

        chain.add_step("harness_followup", follow_up, iteration)

        messages.append({"role": "assistant", "content": llm_response})
        messages.append({"role": "user", "content": follow_up})
    else:
        chain.final_output = llm_response
        chain.early_stopped = False
        chain.total_iterations = settings.MAX_ITERATION_DEPTH
        logger.info("Harness exhausted max iteration depth (%d)", settings.MAX_ITERATION_DEPTH)

    chain.add_step("final_output", chain.final_output, chain.total_iterations)

    effective_session_id = session_id or uuid.uuid4().hex
    chain.session_id = effective_session_id
    title = user_query[:50]
    try:
        from core.session_store import save_session, enforce_session_cap
        save_session(effective_session_id, title, folder_path,
                     chain.to_dict(), is_complete=True, summary=compaction_summary)
        enforce_session_cap(settings.MAX_SESSION_HISTORY)
    except Exception as e:
        logger.warning("Failed to persist session: %s", e)

    return chain
