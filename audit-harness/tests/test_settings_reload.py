import os
import sys
import pytest
from config.settings import Settings


@pytest.fixture
def isolated_env(monkeypatch, tmp_path):
    """Create a clean .env file in a temp dir and patch find_dotenv to return it."""
    env_file = tmp_path / ".env"
    env_file.write_text(
        "LLM_TEMPERATURE=0.5\n"
        "MAX_ITERATION_DEPTH=4\n"
        "ENABLE_NETWORK_GUARD=false\n"
        "LLM_API_KEY=sk-test-123456789abcd\n"
        "FILE_CHAR_CAP=99999\n"
        "MAX_SESSION_HISTORY=42\n",
        encoding="utf-8"
    )
    monkeypatch.setattr("config.settings.find_dotenv", lambda usecwd=True: str(env_file))
    return env_file


def test_to_dict_masks_api_key(isolated_env):
    s = Settings()
    d = s.to_dict()
    assert "LLM_API_KEY" in d
    api_val = d["LLM_API_KEY"]
    assert isinstance(api_val, str)
    assert len(api_val) > 0


def test_to_dict_has_all_fields(isolated_env):
    s = Settings()
    d = s.to_dict()
    for field_name in s.__dataclass_fields__:
        assert field_name in d


def test_update_field_persists(isolated_env, monkeypatch, tmp_path):
    env_file = tmp_path / "test.env"
    env_file.write_text("LLM_TEMPERATURE=0.1\n", encoding="utf-8")
    monkeypatch.setattr("config.settings.find_dotenv", lambda usecwd=True: str(env_file))

    s = Settings()
    assert s.LLM_TEMPERATURE == 0.1

    s.update_field("LLM_TEMPERATURE", "0.9")
    assert s.LLM_TEMPERATURE == 0.9
    content = env_file.read_text(encoding="utf-8")
    assert "LLM_TEMPERATURE=0.9" in content


def test_update_field_appends_new(isolated_env, monkeypatch, tmp_path):
    env_file = tmp_path / "test.env"
    env_file.write_text("LLM_TEMPERATURE=0.2\n", encoding="utf-8")
    monkeypatch.setattr("config.settings.find_dotenv", lambda usecwd=True: str(env_file))

    s = Settings()
    s.update_field("MAX_SESSION_HISTORY", "75")
    assert s.MAX_SESSION_HISTORY == 75
    content = env_file.read_text(encoding="utf-8")
    assert "MAX_SESSION_HISTORY=75" in content


def test_update_field_rejects_unknown(isolated_env):
    s = Settings()
    with pytest.raises(ValueError, match="Unknown"):
        s.update_field("NONEXISTENT_FIELD", "123")


def test_effective_caps_unlimited(isolated_env):
    s = Settings()
    s.FILE_CHAR_CAP = 0
    assert s.get_effective_file_char_cap() == sys.maxsize
    s.FILE_ROW_CAP = 0
    assert s.get_effective_file_row_cap() == sys.maxsize


def test_effective_caps_default_neg1(isolated_env):
    s = Settings()
    s.FILE_CHAR_CAP = -1
    assert s.get_effective_file_char_cap() == 50000
    s.FILE_ROW_CAP = -1
    assert s.get_effective_file_row_cap() == 100


def test_settings_is_mutable(isolated_env):
    s = Settings()
    s.LLM_TEMPERATURE = 0.88
    assert s.LLM_TEMPERATURE == 0.88
