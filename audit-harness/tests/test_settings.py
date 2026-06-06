import os
import pytest
from config.settings import Settings


def test_settings_loads_llm_endpoint():
    from config.settings import settings
    assert isinstance(settings.LLM_ENDPOINT, str)


def test_settings_loads_llm_model_default():
    from config.settings import settings
    assert isinstance(settings.LLM_MODEL, str)
    assert len(settings.LLM_MODEL) > 0


def test_settings_loads_temperature_is_float():
    from config.settings import settings
    assert isinstance(settings.LLM_TEMPERATURE, float)
    assert settings.LLM_TEMPERATURE >= 0.0


def test_settings_max_iteration_is_int():
    from config.settings import settings
    assert isinstance(settings.MAX_ITERATION_DEPTH, int)
    assert settings.MAX_ITERATION_DEPTH >= 1


def test_settings_early_stop_confidence_is_float():
    from config.settings import settings
    assert isinstance(settings.EARLY_STOP_CONFIDENCE, float)
    assert 0.0 <= settings.EARLY_STOP_CONFIDENCE <= 1.0


def test_settings_allowed_outbound_hosts_includes_loopback():
    from config.settings import settings
    loopback = {"127.0.0.1", "localhost", "::1"}
    assert loopback.issubset(set(settings.ALLOWED_OUTBOUND_HOSTS))


def test_settings_host_is_localhost():
    from config.settings import settings
    assert settings.HOST == "127.0.0.1" or settings.HOST == "localhost"


def test_settings_port_is_int():
    from config.settings import settings
    assert isinstance(settings.PORT, int)
    assert 1 <= settings.PORT <= 65535


def test_settings_enable_network_guard_is_bool():
    from config.settings import settings
    assert isinstance(settings.ENABLE_NETWORK_GUARD, bool)


def test_settings_llm_top_k_is_int():
    from config.settings import settings
    assert isinstance(settings.LLM_TOP_K, int)


def test_settings_top_p_is_float():
    from config.settings import settings
    assert isinstance(settings.LLM_TOP_P, float)


def test_settings_kill_on_violation_is_bool():
    from config.settings import settings
    assert isinstance(settings.KILL_ON_VIOLATION, bool)


def test_settings_file_char_cap_is_int():
    from config.settings import settings
    assert isinstance(settings.FILE_CHAR_CAP, int)
    assert settings.FILE_CHAR_CAP > 0


def test_settings_file_row_cap_is_int():
    from config.settings import settings
    assert isinstance(settings.FILE_ROW_CAP, int)
    assert settings.FILE_ROW_CAP > 0


def test_settings_is_mutable():
    from config.settings import settings
    original = settings.LLM_TEMPERATURE
    settings.LLM_TEMPERATURE = 0.5
    assert settings.LLM_TEMPERATURE == 0.5
    settings.LLM_TEMPERATURE = original


def test_settings_allowed_outbound_hosts_is_list():
    from config.settings import settings
    assert isinstance(settings.ALLOWED_OUTBOUND_HOSTS, list)
    assert all(isinstance(h, str) for h in settings.ALLOWED_OUTBOUND_HOSTS)


def test_settings_max_tokens_is_int():
    from config.settings import settings
    assert isinstance(settings.LLM_MAX_TOKENS, int)
    assert settings.LLM_MAX_TOKENS > 0


def test_new_instance_with_custom_env(monkeypatch):
    monkeypatch.setattr("config.settings.find_dotenv", lambda usecwd=True: None)
    monkeypatch.setenv("LLM_TEMPERATURE", "0.5")
    monkeypatch.setenv("MAX_ITERATION_DEPTH", "5")
    monkeypatch.setenv("ENABLE_NETWORK_GUARD", "false")
    monkeypatch.setenv("ALLOWED_OUTBOUND_HOSTS", "example.com,api.example.com")
    monkeypatch.setenv("FILE_CHAR_CAP", "100000")
    monkeypatch.setenv("FILE_ROW_CAP", "200")
    monkeypatch.setenv("MAX_SESSION_HISTORY", "50")
    s = Settings()
    assert s.LLM_TEMPERATURE == 0.5
    assert s.MAX_ITERATION_DEPTH == 5
    assert s.ENABLE_NETWORK_GUARD is False
    assert "example.com" in s.ALLOWED_OUTBOUND_HOSTS
    assert "api.example.com" in s.ALLOWED_OUTBOUND_HOSTS
    assert s.FILE_CHAR_CAP == 100000
    assert s.FILE_ROW_CAP == 200
    assert s.MAX_SESSION_HISTORY == 50
    assert "127.0.0.1" in s.ALLOWED_OUTBOUND_HOSTS


def test_max_session_history_exists():
    from config.settings import settings
    assert isinstance(settings.MAX_SESSION_HISTORY, int)
    assert settings.MAX_SESSION_HISTORY >= 1


def test_effective_caps_unlimited():
    from config.settings import settings
    import sys
    settings.FILE_CHAR_CAP = 0
    assert settings.get_effective_file_char_cap() == sys.maxsize
    settings.FILE_CHAR_CAP = 50000


def test_effective_caps_default():
    from config.settings import settings
    settings.FILE_CHAR_CAP = -1
    assert settings.get_effective_file_char_cap() == 50000
    settings.FILE_ROW_CAP = -1
    assert settings.get_effective_file_row_cap() == 100
    settings.FILE_CHAR_CAP = 50000
    settings.FILE_ROW_CAP = 100


def test_to_dict_masks_api_key():
    from config.settings import settings
    d = settings.to_dict()
    assert "LLM_API_KEY" in d
    api_val = d["LLM_API_KEY"]
    assert api_val == "****" or "****" in api_val
