import json
import re
import logging
from core.llm_client import call_llm_raw

logger = logging.getLogger(__name__)

SKILL_EXTRACTION_PROMPT = """You are an AI prompt engineer. Analyze these audit session transcripts
and extract recurring patterns, preferences, domain-specific instructions,
and quality criteria that should be added to the auditor's system prompt
to improve future responses.

Return ONLY a JSON array of skill objects:
[{"skill_text": "...", "source_evidence": "..."}]

Each skill_text should be a concise instruction (1-2 sentences) that can be
appended to an auditor system prompt. source_evidence should briefly cite
which session(s) demonstrated this pattern.

If no meaningful patterns are found, return an empty array: []
"""


def _extract_json_array(response_text: str) -> list[dict]:
    if not response_text or not response_text.strip():
        return []

    # Strategy 1: direct parse
    try:
        result = json.loads(response_text)
        if isinstance(result, list):
            return result
    except json.JSONDecodeError:
        pass

    # Strategy 2: markdown code fences
    fence_match = re.search(r'```(?:json)?\s*(\[.*?\])\s*```', response_text, re.DOTALL)
    if fence_match:
        try:
            result = json.loads(fence_match.group(1))
            if isinstance(result, list):
                return result
        except json.JSONDecodeError:
            pass

    # Strategy 3: bracket-depth-aware JSON array extraction
    start_idx = response_text.find("[")
    while start_idx != -1:
        depth = 0
        in_string = False
        escape_next = False
        for i in range(start_idx, len(response_text)):
            ch = response_text[i]
            if escape_next:
                escape_next = False
                continue
            if ch == "\\":
                escape_next = True
                continue
            if ch == '"' and not escape_next:
                in_string = not in_string
                continue
            if in_string:
                continue
            if ch == "[":
                depth += 1
            elif ch == "]":
                depth -= 1
                if depth == 0:
                    candidate = response_text[start_idx:i + 1]
                    try:
                        result = json.loads(candidate)
                        if isinstance(result, list):
                            return result
                    except json.JSONDecodeError:
                        pass
                    break
        start_idx = response_text.find("[", start_idx + 1)

    logger.warning("All JSON array extraction strategies failed: %s", response_text[:200])
    return []


def learn_from_sessions(session_ids: list[str] = None) -> list[dict]:
    from core.session_store import list_sessions, load_session, list_learned_skills, save_learned_skill
    from config.settings import settings

    # Determine which sessions to process
    if session_ids is None:
        all_sessions = list_sessions(limit=settings.MAX_SESSION_HISTORY)
        existing_skills = list_learned_skills(active_only=False)
        processed_ids = set()
        for skill in existing_skills:
            for sid in (skill.get("source_session_ids") or "").split(","):
                sid = sid.strip()
                if sid:
                    processed_ids.add(sid)
        candidate_ids = [s["id"] for s in all_sessions if s["id"] not in processed_ids]
        if len(candidate_ids) < 2:
            logger.info("Not enough unprocessed sessions (need ≥2): %d found", len(candidate_ids))
            return []
        session_ids = candidate_ids

    if len(session_ids) < 2:
        logger.info("At least 2 sessions required for skill learning, got %d", len(session_ids))
        return []

    new_skills = []
    batch_size = 10

    for i in range(0, len(session_ids), batch_size):
        batch = session_ids[i:i + batch_size]
        formatted_sessions = ""

        for j, sid in enumerate(batch):
            try:
                sess = load_session(sid)
                chain = sess.get("chain", {})
                gaps = []
                followups = []
                for step in chain.get("steps", []):
                    if step.get("role") == "evaluator_judgment":
                        try:
                            judge = json.loads(step["content"])
                            gaps.extend(judge.get("gaps_identified", []))
                        except (json.JSONDecodeError, KeyError):
                            pass
                    elif step.get("role") == "harness_followup":
                        followups.append(step.get("content", ""))

                final_output = chain.get("final_output", "")
                formatted_sessions += (
                    f"--- Session {j + 1} (ID: {sid}) ---\n"
                    f"Query: {chain.get('user_query', '')}\n"
                    f"Gaps identified: {', '.join(gaps) if gaps else 'None'}\n"
                    f"Follow-up challenges: {' | '.join(followups) if followups else 'None'}\n"
                    f"Final output (excerpt): {final_output[:1000]}\n\n"
                )
            except Exception as e:
                logger.warning("Skipping session %s: %s", sid, e)
                continue

        if not formatted_sessions.strip():
            continue

        prompt = SKILL_EXTRACTION_PROMPT + "\n\n=== SESSION TRANSCRIPTS ===\n" + formatted_sessions

        try:
            raw = call_llm_raw(prompt)
            extracted = _extract_json_array(raw)
            for skill in extracted:
                skill_text = skill.get("skill_text", "").strip()
                if not skill_text:
                    continue
                skill_id = save_learned_skill(skill_text, ",".join(batch))
                new_skills.append({
                    "id": skill_id,
                    "skill_text": skill_text,
                    "source_evidence": skill.get("source_evidence", ""),
                })
        except Exception as e:
            logger.warning("Skill extraction failed for batch: %s", e)
            continue

    return new_skills
