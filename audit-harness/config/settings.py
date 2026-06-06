import os
import re
import sys
import logging
from dataclasses import dataclass, field
from dotenv import load_dotenv, find_dotenv

logger = logging.getLogger(__name__)


@dataclass
class Settings:
    LLM_ENDPOINT: str = ""
    LLM_API_KEY: str = ""
    LLM_MODEL: str = "gemini-2.0-flash"
    LLM_TEMPERATURE: float = 0.3
    LLM_TOP_P: float = 0.9
    LLM_TOP_K: int = 40
    LLM_MAX_TOKENS: int = 8192
    MAX_ITERATION_DEPTH: int = 3
    EARLY_STOP_CONFIDENCE: float = 0.85
    HOST: str = "127.0.0.1"
    PORT: int = 5000
    ALLOWED_OUTBOUND_HOSTS: list[str] = field(default_factory=lambda: ["generativelanguage.googleapis.com"])
    KILL_ON_VIOLATION: bool = True
    ENABLE_NETWORK_GUARD: bool = True
    FILE_CHAR_CAP: int = 50000
    FILE_ROW_CAP: int = 100
    MAX_SESSION_HISTORY: int = 100

    def _cast(self, field_name, env_val):
        type_map = {
            "ALLOWED_OUTBOUND_HOSTS": lambda v: [h.strip() for h in v.split(",") if h.strip()],
            "KILL_ON_VIOLATION": lambda v: v.lower() in ("true", "1", "yes"),
            "ENABLE_NETWORK_GUARD": lambda v: v.lower() in ("true", "1", "yes"),
            "MAX_ITERATION_DEPTH": int,
            "MAX_SESSION_HISTORY": int,
            "FILE_CHAR_CAP": int,
            "FILE_ROW_CAP": int,
            "LLM_TOP_K": int,
            "LLM_MAX_TOKENS": int,
            "PORT": int,
            "LLM_TEMPERATURE": float,
            "LLM_TOP_P": float,
            "EARLY_STOP_CONFIDENCE": float,
        }
        cast = type_map.get(field_name, str)
        return cast(env_val)

    def __post_init__(self):
        _load_dotenv()
        for field_name in self.__dataclass_fields__:
            env_val = os.getenv(field_name)
            if env_val is not None and env_val != "":
                setattr(self, field_name, self._cast(field_name, env_val))
        self.ALLOWED_OUTBOUND_HOSTS = _hosts_with_loopback(self.ALLOWED_OUTBOUND_HOSTS)

    def reload(self):
        _load_dotenv(override=True)
        for field_name in self.__dataclass_fields__:
            env_val = os.getenv(field_name)
            if env_val is not None and env_val != "":
                setattr(self, field_name, self._cast(field_name, env_val))
        self.ALLOWED_OUTBOUND_HOSTS = _hosts_with_loopback(self.ALLOWED_OUTBOUND_HOSTS)

    def update_field(self, field_name: str, value: str):
        if field_name not in self.__dataclass_fields__ or field_name.startswith("_"):
            raise ValueError(f"Unknown setting field: {field_name}")
        cast_value = self._cast(field_name, value)
        setattr(self, field_name, cast_value)
        self._write_field_to_env(field_name, value)

    def _write_field_to_env(self, field_name, raw_value):
        env_path = find_dotenv(usecwd=True)
        if not env_path:
            env_path = os.path.join(os.getcwd(), ".env")
        try:
            with open(env_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
        except FileNotFoundError:
            lines = []

        pattern = re.compile(rf"^#?\s*{re.escape(field_name)}\s*=")
        found = False
        for i, line in enumerate(lines):
            if pattern.match(line):
                lines[i] = f"{field_name}={raw_value}\n"
                found = True
                break

        if not found:
            lines.append(f"{field_name}={raw_value}\n")

        with open(env_path, "w", encoding="utf-8", newline="") as f:
            f.writelines(lines)

    def get_effective_file_char_cap(self) -> int:
        if self.FILE_CHAR_CAP == 0:
            return sys.maxsize
        if self.FILE_CHAR_CAP == -1:
            return 50000
        return self.FILE_CHAR_CAP

    def get_effective_file_row_cap(self) -> int:
        if self.FILE_ROW_CAP == 0:
            return sys.maxsize
        if self.FILE_ROW_CAP == -1:
            return 100
        return self.FILE_ROW_CAP

    def to_dict(self) -> dict:
        result = {}
        for field_name in self.__dataclass_fields__:
            value = getattr(self, field_name)
            if isinstance(value, list):
                value = ",".join(value)
            str_value = str(value)
            if "API_KEY" in field_name and str_value:
                str_value = "****" + str_value[-4:] if len(str_value) > 4 else "****"
            result[field_name] = str_value
        return result


def _load_dotenv(override=True):
    env_path = find_dotenv(usecwd=True)
    if env_path:
        load_dotenv(env_path, override=override)
    else:
        logger.warning("No .env file found, using defaults")


def _hosts_with_loopback(hosts: list[str]) -> list[str]:
    loopback = {"127.0.0.1", "localhost", "::1"}
    merged = list(set(hosts) | loopback)
    return merged


settings = Settings()
