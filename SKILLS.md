# SKILLS.md — Audit Harness (CritiqueFlow)

> **Purpose:** Project-specific engineering constraints. Every executor agent MUST read this
> before writing any code. Violations of these rules are build failures.

---

## 🏗️ Stack & Versions

| Component | Version | Notes |
|-----------|---------|-------|
| Python | 3.12+ (target 3.12.4) | Do NOT use 3.13-only features |
| Flask | >= 3.0 | Localhost only, debug=False in run.py |
| Package manager | `uv` | Use `uv venv`, `uv pip install` |
| HTTP client | `urllib.request` (stdlib) | **NO** requests, httpx, aiohttp |
| Test framework | `pytest` | With `unittest.mock` for LLM mocking |

---

## 🏛️ Architectural Rules

### Flat 2-Layer Architecture
```
Flask Routes (web/routes.py)
    ↓
Core Modules (core/*.py)
    ↓
LLM Client (core/llm_client.py) ← SOLE outbound exit point
```

- **NO** repository layers, service layers, DTOs, or data-mapper files.
- **NO** abstract base classes or interfaces unless there are 2+ concrete implementations running simultaneously.
- **NO** agent frameworks (LangChain, LangGraph, CrewAI, AutoGen).
- **NO** MCP servers, clients, or tool-calling infrastructure.
- **NO** ORMs or database layers.

### Single Responsibility for Outbound Traffic
- `core/llm_client.py` is the **ONLY** module that makes outbound HTTP calls.
- All other modules call `call_llm()` or `call_llm_raw()` — never `urllib.request` directly.
- The LLM endpoint URL comes from `config/settings.py`, never hardcoded.

### Prompt Files Are Static Assets
- `prompts/*.md` files are loaded once at module import time.
- Path resolution uses `pathlib.Path(__file__).parent.parent / "prompts"` — never relative CWD.
- Prompts are **never** modified at runtime.

---

## 🔒 Security Rules

### Network Guard (`security/network_guard.py`)
- **Production only:** Controlled by `ENABLE_NETWORK_GUARD` env var (default `true`).
- Monkey-patches `socket.connect`, `subprocess.Popen`, `os.system`.
- Allows only: configured `ALLOWED_OUTBOUND_HOSTS` + loopback addresses.
- **MUST be deactivated during pytest** — tests set `ENABLE_NETWORK_GUARD=false`.

### File System Boundaries
- **Read-only** access to user's working folder.
- **Write-only** to `{working_folder}/exports/` for markdown exports.
- Path traversal prevention: `os.path.realpath()` check on every file access.
- No `..` in filenames, no `/` or `\` in filenames.

### Subprocess Prohibition
- No `subprocess.Popen`, `subprocess.run`, `os.system`, `os.exec*` in production.
- These are blocked by the network guard in production mode.

---

## 🧪 Testing Strategy

### Mock-First, No External Dependencies
- **ALL automated tests mock `call_llm`** via `unittest.mock.patch`.
- Tests NEVER make real HTTP calls to any LLM endpoint.
- Mock fixtures return realistic audit responses and valid evaluator JSON.
- The mock fixtures are defined in `tests/conftest.py`.

### Test Execution Commands
```bash
# Run all unit tests (no API key needed)
python -m pytest tests/ -v -k "not integration"

# Run integration tests (requires real API key in .env)
python -m pytest tests/ -v -k "integration"

# Run all tests
python -m pytest tests/ -v
```

### Test Naming Convention
- `tests/test_{module_name}.py` — one test file per core module.
- Test functions: `test_{feature}_{scenario}` (e.g., `test_evaluate_response_sufficient`).

---

## 📦 Allowed Dependencies (requirements.txt)

```
flask>=3.0
python-dotenv>=1.0
openpyxl>=3.1
python-docx>=1.1
PyPDF2>=3.0
pytest>=8.0
```

**NOTHING ELSE.** No `requests`, `httpx`, `aiohttp`, `langchain`, `openai`, or any other package.

---

## 🎨 Frontend Rules

- **Zero external resources**: No CDN, no external fonts, no analytics scripts.
- All CSS/JS is local and self-contained.
- `fetch()` calls go to `localhost` only — no CORS needed.
- Dark theme with color-coded interaction chain roles.
- Basic markdown-to-HTML rendering in JS (bold, italic, code, headers, lists, line breaks).
  Support `**bold**`, `*italic*`, `` `code` ``, `### headers`, `- lists`, `\n` → `<br>`.

---

## 📐 Configuration via .env

All runtime configuration is loaded via `python-dotenv` into a frozen dataclass.
Default values are provided for ALL fields — the app MUST start with only `LLM_ENDPOINT` and `LLM_API_KEY` set.

### Required Fields (no defaults)
- `LLM_ENDPOINT` — full URL to LLM API (e.g., `https://api.example.com/invoke`)
- `LLM_API_KEY` — bearer token / API key

### Optional Fields (with defaults)
- `LLM_MODEL` — default `"gemini-2.0-flash"` (for testing)
- `LLM_TEMPERATURE` — default `0.3`
- `LLM_TOP_P` — default `0.9`
- `LLM_TOP_K` — default `40`
- `LLM_MAX_TOKENS` — default `8192`
- `MAX_ITERATION_DEPTH` — default `3` (= 6 total LLM calls per query)
- `EARLY_STOP_CONFIDENCE` — default `0.85`
- `HOST` — default `127.0.0.1`
- `PORT` — default `5000`
- `ALLOWED_OUTBOUND_HOSTS` — comma-separated hostnames
- `KILL_ON_VIOLATION` — default `true`
- `ENABLE_NETWORK_GUARD` — default `true` (**set to `false` during testing**)

---

## 🔢 LLM Client Response Parsing

The `llm_client.py` must handle multiple response formats since the production gateway
(`/invoke`) may return different JSON structures depending on the underlying model:

### Parsing Priority Order
1. **OpenAI format:** `response["choices"][0]["message"]["content"]`
2. **Anthropic format:** `response["content"][0]["text"]`
3. **Raise `RuntimeError`** with the raw response body for debugging.

### Request Format
Always send OpenAI-compatible chat format:
```json
{
  "model": "<LLM_MODEL>",
  "messages": [{"role": "...", "content": "..."}],
  "temperature": 0.3,
  "top_p": 0.9,
  "max_tokens": 8192
}
```

### Timeout
- Set `urllib.request.urlopen` timeout to **120 seconds**.
- On timeout, raise `RuntimeError("LLM request timed out after 120s")`.

### Retry
- On HTTP 429 (rate limit) or 5xx, retry up to **2 times** with 2-second backoff.
- On all other HTTP errors, raise immediately with status code and body.

---

## 📊 Evaluator JSON Extraction

LLMs frequently wrap JSON responses in markdown code fences. The evaluator parser
MUST handle all of these:

```
{"sufficient": true, ...}              ← raw JSON
```json\n{"sufficient": true, ...}\n```  ← fenced JSON
```

### Extraction Strategy
1. Try `json.loads(response_text)` directly.
2. If that fails, use regex `r'```(?:json)?\s*(\{.*?\})\s*```'` (with `re.DOTALL`) to extract from code fences.
3. If that fails, use regex `r'\{[^{}]*"sufficient"[^{}]*\}'` to find JSON-like substring.
4. If ALL fail, return the hardcoded fallback dict (as specified in the original plan).

---

## 📁 File Structure

```
CritiqueFlow/
├── SKILLS.md                    ← THIS FILE
├── CLAUDE.md / AGENTS.md / GEMINI.md  ← Orchestration (never committed)
├── implementation_plan.md       ← Execution plan
├── success_criteria.md          ← Verification gates
└── audit-harness/               ← ALL source code lives here
    ├── .env                     ← Real config (gitignored)
    ├── .env.example             ← Template
    ├── requirements.txt
    ├── run.py                   ← Entry point
    ├── config/
    │   ├── __init__.py
    │   └── settings.py
    ├── security/
    │   ├── __init__.py
    │   └── network_guard.py
    ├── core/
    │   ├── __init__.py
    │   ├── llm_client.py
    │   ├── harness_engine.py
    │   ├── evaluator.py
    │   ├── file_reader.py
    │   └── interaction_chain.py
    ├── prompts/
    │   ├── system_auditor.md
    │   └── evaluator_criteria.md
    ├── web/
    │   ├── __init__.py
    │   ├── app.py
    │   ├── routes.py
    │   ├── templates/
    │   │   └── index.html
    │   └── static/
    │       ├── style.css
    │       └── app.js
    └── tests/
        ├── __init__.py
        ├── conftest.py
        ├── test_settings.py
        ├── test_network_guard.py
        ├── test_interaction_chain.py
        ├── test_file_reader.py
        ├── test_llm_client.py
        ├── test_evaluator.py
        ├── test_harness_engine.py
        ├── test_routes.py
        └── fixtures/
            ├── sample.md
            ├── sample.txt
            ├── sample.xlsx
            ├── sample.docx
            └── sample.pdf
```
