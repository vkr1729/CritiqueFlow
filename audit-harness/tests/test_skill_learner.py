import json
import pytest
from unittest.mock import patch, MagicMock
from core.skill_learner import _extract_json_array, learn_from_sessions


def test_extract_json_array_direct():
    raw = json.dumps([
        {"skill_text": "Always cite SR 11-7.", "source_evidence": "Session 1"},
        {"skill_text": "Use quantitative thresholds.", "source_evidence": "Session 2"},
    ])
    result = _extract_json_array(raw)
    assert len(result) == 2
    assert result[0]["skill_text"] == "Always cite SR 11-7."
    assert result[1]["skill_text"] == "Use quantitative thresholds."


def test_extract_json_array_single_object():
    """Non-list JSON should be handled gracefully."""
    raw = json.dumps({"skill_text": "Test.", "source_evidence": "S1"})
    result = _extract_json_array(raw)
    assert result == []


def test_extract_json_array_fenced():
    raw = '```json\n[{"skill_text": "Check calibration.", "source_evidence": "S1"}]\n```'
    result = _extract_json_array(raw)
    assert len(result) == 1
    assert result[0]["skill_text"] == "Check calibration."


def test_extract_json_array_broader_find():
    raw = 'Here are the skills: [{"skill_text": "Validate inputs.", "source_evidence": "S3"}] done.'
    result = _extract_json_array(raw)
    assert len(result) == 1
    assert result[0]["skill_text"] == "Validate inputs."


def test_extract_json_array_unparseable():
    raw = "This is not JSON at all."
    result = _extract_json_array(raw)
    assert result == []


def test_extract_json_array_empty_string():
    result = _extract_json_array("")
    assert result == []


def test_learn_from_sessions_empty_history():
    """When there are fewer than 2 unprocessed sessions, return empty."""
    with patch("core.session_store.list_sessions", return_value=[]):
        result = learn_from_sessions()
        assert result == []


def test_learn_from_sessions_not_enough():
    """Only 1 session — not enough for learning."""
    with patch("core.session_store.list_sessions", return_value=[
        {"id": "s1", "title": "Test"}
    ]):
        with patch("core.session_store.list_learned_skills", return_value=[]):
            result = learn_from_sessions()
            assert result == []


def test_learn_from_sessions_skips_processed():
    """Sessions already in learned skills should be skipped."""
    sessions = [{"id": "s1", "title": "Already done"}, {"id": "s2", "title": "Also done"}]
    skills = [{"id": 1, "source_session_ids": "s1,s2"}]
    with patch("core.session_store.list_sessions", return_value=sessions):
        with patch("core.session_store.list_learned_skills", return_value=skills):
            result = learn_from_sessions()
            assert result == []
