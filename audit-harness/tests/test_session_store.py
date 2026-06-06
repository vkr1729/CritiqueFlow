import json
import pytest
from core.session_store import (
    init_db, save_session, load_session, list_sessions,
    delete_session, clear_all_sessions, enforce_session_cap,
    save_learned_skill, list_learned_skills, update_learned_skill,
    delete_learned_skill, _get_connection
)


@pytest.fixture(autouse=True)
def clean_db(monkeypatch, tmp_path):
    """Redirect DB to temp path and clean between tests."""
    db_path = tmp_path / "test_sessions.db"
    monkeypatch.setattr("core.session_store._DB_PATH", db_path)
    monkeypatch.setattr("core.session_store._DB_DIR", tmp_path)
    init_db()


def test_init_db_creates_tables():
    import sqlite3
    from core.session_store import _get_connection
    with _get_connection() as conn:
        tables = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
        table_names = [t["name"] for t in tables]
        assert "sessions" in table_names
        assert "learned_skills" in table_names


def test_save_and_load_session():
    chain = {"user_query": "test", "steps": []}
    save_session("s1", "Test Session", "/tmp", chain)
    loaded = load_session("s1")
    assert loaded["title"] == "Test Session"
    assert loaded["folder_path"] == "/tmp"
    assert loaded["chain"]["user_query"] == "test"


def test_save_session_upsert():
    chain1 = {"user_query": "q1", "steps": []}
    chain2 = {"user_query": "q2", "steps": [{"role": "user"}]}
    save_session("s1", "First", "/a", chain1)
    save_session("s1", "Second", "/b", chain2, is_complete=True, summary="changed")
    loaded = load_session("s1")
    assert loaded["title"] == "Second"
    assert loaded["folder_path"] == "/b"
    assert loaded["is_complete"] == 1
    assert loaded["summary"] == "changed"


def test_load_session_not_found():
    with pytest.raises(ValueError, match="Session not found"):
        load_session("nonexistent")


def test_list_sessions():
    save_session("s1", "Alpha", "/a", {"steps": []})
    save_session("s2", "Beta", "/b", {"steps": []})
    sessions = list_sessions()
    assert len(sessions) == 2
    assert sessions[0]["title"] == "Beta"  # newest first
    assert sessions[1]["title"] == "Alpha"
    # No chain_json in list
    assert "chain_json" not in sessions[0]


def test_list_sessions_limit_offset():
    for i in range(5):
        save_session(f"s{i}", f"Session {i}", "/tmp", {"steps": []})
    page = list_sessions(limit=3, offset=0)
    assert len(page) == 3
    page2 = list_sessions(limit=3, offset=3)
    assert len(page2) == 2


def test_delete_session():
    save_session("s1", "Test", "/tmp", {"steps": []})
    delete_session("s1")
    with pytest.raises(ValueError):
        load_session("s1")


def test_clear_all_sessions():
    save_session("s1", "A", "/tmp", {"steps": []})
    save_session("s2", "B", "/tmp", {"steps": []})
    clear_all_sessions()
    assert list_sessions() == []


def test_enforce_session_cap():
    for i in range(10):
        save_session(f"s{i}", f"Session {i}", "/tmp", {"steps": []})
    enforce_session_cap(5)
    remaining = list_sessions(limit=50)
    assert len(remaining) == 5


def test_save_and_list_learned_skill():
    skill_id = save_learned_skill("Always cite SR 11-7.", "s1,s2")
    assert isinstance(skill_id, int)
    skills = list_learned_skills(active_only=True)
    assert len(skills) == 1
    assert skills[0]["skill_text"] == "Always cite SR 11-7."
    assert skills[0]["is_active"] == 1


def test_update_learned_skill():
    skill_id = save_learned_skill("Be specific.", "s1")
    update_learned_skill(skill_id, skill_text="Be very specific.", is_active=False)
    skills = list_learned_skills(active_only=False)
    s = skills[0]
    assert s["skill_text"] == "Be very specific."
    assert s["is_active"] == 0
    # Active-only filter hides it
    assert list_learned_skills(active_only=True) == []


def test_delete_learned_skill():
    skill_id = save_learned_skill("Remove me.", "s1")
    delete_learned_skill(skill_id)
    assert list_learned_skills(active_only=False) == []
