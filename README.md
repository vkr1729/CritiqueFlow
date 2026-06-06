# CritiqueFlow

[![Python Version](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12-blue.svg)](https://www.python.org/)
[![Tests Status](https://img.shields.io/badge/tests-138%20passed-green.svg)](#-testing)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](#-license)
[![Security](https://img.shields.io/badge/security-Network%20Guard-orange.svg)](#-security--network-guard)

**CritiqueFlow** is a production-grade, local-first **Model Risk Audit Harness** designed to automate the generation, evaluation, and iterative refinement of model audit workpapers. By leveraging a multi-agent generator-evaluator architecture, CritiqueFlow eliminates "role contamination" and systematically drives draft workpapers to meet rigorous regulatory and enterprise quality standards.

---

## 🚀 Core Value Proposition

When generating complex model risk reviews (e.g., assessing interest rate models or quantitative finance methodologies), LLMs often suffer from **self-validation bias** or **role contamination**—where the same model session that drafted a document fails to recognize its omissions. 

CritiqueFlow solves this by implementing an automated **generator-evaluator loop**:
1. **Generator**: Drafts the audit workpaper based on the user's query and uploaded context documents (PDF, Docx, Markdown, Excel, TXT).
2. **Evaluator**: Critiques the workpaper against static regulatory guidelines and specific audit criteria, identifying gaps and issuing a follow-up challenge.
3. **Iterative Harness**: Feeds the critique back to the generator to refine the draft. This loop runs up to a configurable maximum depth or stops early when the evaluator's confidence and sufficiency scores meet the desired threshold.

---

## ✨ Key Features

- **Role Contamination Mitigation**: Strict separation between the generation prompts and evaluation logic.
- **Robust JSON Extraction**: Multi-strategy parsing (raw JSON, regex extraction from markdown code fences, and substring matching) ensures evaluator judgments are always parsed reliably, falling back to a structured default on unparseable outputs.
- **Context Compaction**: Uses an LLM summarization step to compact history from prior audit sessions, preventing context window bloat and maximizing token efficiency.
- **Enterprise Network Guard**: A production-only security layer that monkey-patches `socket.connect`, `subprocess.Popen`, and `os.system` to prevent unauthorized outbound data egress.
- **File Reader with Size Caps**: Safe file parser supporting PDF, Word (Docx), Excel (Xlsx), Markdown, and TXT files, with configurable size/row caps to prevent memory exhaustion.
- **Mutable Settings & Prompt Editors**: Live `.env` editing, hot-reloading settings, and customizable system prompts directly from the frontend dashboard.
- **Developer Diagnostics & Skills Learner**: Local database-backed skill repository that appends user-taught skills to the auditor's system prompt dynamically.
- **Cross-Platform Compatibility**: Full support for Windows 11 and Linux with unified path handling, file encoding (UTF-8), and line endings.

---

## 🏛️ Architecture Overview

```mermaid
graph TD
    User([User Query & Documents]) --> HF[Harness Engine]
    HF --> |Inject Context| G[Generator Prompt]
    G --> |call_llm| LLM1[LLM Client]
    LLM1 --> |Draft Workpaper| HF
    HF --> |Evaluate| E[Evaluator Prompt]
    E --> |call_llm_raw| LLM2[LLM Client]
    LLM2 --> |JSON Evaluation| HF
    HF --> |Is Sufficient or High Confidence?| Verdict{Check Stop}
    Verdict --> |No: Iteration < Max| Challenge[Harness Follow-up Challenge]
    Challenge --> |Refine Draft| G
    Verdict --> |Yes / Max Reached| Output([Final Polished Workpaper])
```

- **Flask Blueprint Routes (`web/routes.py`)**: Serving the frontend SPA and providing REST endpoints for querying, listing files, settings, and session exports.
- **Harness Engine (`core/harness_engine.py`)**: Runs the generation-evaluation loop and saves the conversation timeline to the SQLite database.
- **Evaluator (`core/evaluator.py`)**: Runs the prompt validator and parses the JSON response using regex fallback methods.
- **LLM Client (`core/llm_client.py`)**: Manages outbound connections using Python's standard `urllib.request` (no external HTTP dependencies), handling retries (for 429/5xx), timeouts, and parsing OpenAI/Anthropic format responses.

---

## 📦 File Structure

```
CritiqueFlow/
├── SKILLS.md                    # Project-specific engineering constraints
├── implementation_plan.md       # Implementation and phase documentation
├── success_criteria.md          # Verification gates and test checklists
└── audit-harness/               # CritiqueFlow Application Source Code
    ├── run.py                   # Server Entry Point
    ├── requirements.txt         # Production Dependencies
    ├── critiqueflow.sh          # Desktop Launch Script (Linux/Mac)
    ├── config/                  # Configuration Loader & Hot-Reload Settings
    ├── security/                # Network Guard & Execution Sandboxing
    ├── core/                    # Harness Engine, Evaluator, LLM Client, File Reader
    ├── prompts/                 # Static Auditor and Evaluator Prompts
    ├── web/                     # Flask App & UI (HTML, CSS, JS)
    └── tests/                   # Extensive Pytest Test Suite
```

---

## 🛠️ Installation

### Prerequisites
- Python 3.10, 3.11, or 3.12
- `uv` package manager (recommended for fast installation) or standard `pip`

### 1. Clone & Navigate
```bash
git clone https://github.com/your-repo/CritiqueFlow.git
cd CritiqueFlow/audit-harness
```

### 2. Set Up Virtual Environment & Dependencies
Using **`uv`**:
```bash
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
uv pip install -r requirements.txt
```

Or using **standard Python venv**:
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

---

## ⚙️ Configuration (`.env`)

Create a `.env` file in the `audit-harness/` directory. You can copy the example file:
```bash
cp .env.example .env
```

### Configuration Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `LLM_ENDPOINT` | **Required.** The full URL to the OpenAI-compatible or Anthropic-compatible chat endpoint. | None |
| `LLM_API_KEY` | **Required.** Your API Bearer token. | None |
| `LLM_MODEL` | The model name to pass in the payload. | `gemini-2.0-flash` |
| `LLM_TEMPERATURE` | Controls the creativity/determinism of the generator. | `0.3` |
| `LLM_TOP_P` | Nucleus sampling parameter. | `0.9` |
| `LLM_TOP_K` | Top-K sampling parameter. | `40` |
| `LLM_MAX_TOKENS` | Max token length for LLM responses. | `8192` |
| `MAX_ITERATION_DEPTH` | Maximum iterations of the generator-evaluator loop (each iteration makes up to 2 LLM calls). | `3` |
| `EARLY_STOP_CONFIDENCE` | Confidence threshold (0.0 to 1.0) below which the harness will stop if the evaluator is satisfied. | `0.85` |
| `HOST` | Binding address for the Flask server. | `127.0.0.1` |
| `PORT` | Target port for the Flask server. Falls back to next available port if occupied. | `5000` |
| `ENABLE_NETWORK_GUARD` | Enables monkey-patching of sockets/subprocesses to prevent data leaks. | `true` |
| `ALLOWED_OUTBOUND_HOSTS` | Comma-separated list of allowed hostnames (e.g., `generativelanguage.googleapis.com,api.groq.com`). | `generativelanguage.googleapis.com` |
| `KILL_ON_VIOLATION` | Exits the process immediately on outbound guard violations if set to `true`. | `true` |
| `FILE_CHAR_CAP` | Character limit for reading text/docx/pdf documents (use `0` for unlimited, `-1` for default). | `50000` |
| `FILE_ROW_CAP` | Row limit for spreadsheet (Excel) document parsing (use `0` for unlimited, `-1` for default). | `100` |

---

## 🖥️ Usage

### Starting the Server

#### Linux / macOS:
You can start CritiqueFlow directly using the provided launcher script:
```bash
chmod +x critiqueflow.sh
./critiqueflow.sh
```
This script will activate the virtual environment, launch the Flask server, write the active port configuration, and automatically open your default browser to CritiqueFlow.

#### Manual Startup (Cross-Platform):
```bash
python run.py
```
By default, the UI will be accessible at `http://127.0.0.1:5000` (or `5001` if port `5000` is in use).

### Using the UI

1. **Load Workspace**: Enter the absolute path to your audit documents directory and click **Load**. All supported files will appear in the sidebar.
2. **Select Context Documents**: Check the boxes next to files you want to include in the context of the audit query.
3. **Execute Audit**: Enter your audit query (e.g., "Review the model validation findings for our interest rate curve fitter") and click **Run Audit**.
4. **Inspect Reasoning Chain**: The right-hand panel displays a detailed vertical timeline showing:
   - Your initial query.
   - The generator's draft at each iteration.
   - The evaluator's structured critique, confidence levels, and identified gaps.
   - The follow-up challenge issued back to the generator.
5. **Export Findings**: Click **Export Markdown** to save a fully formatted audit workpaper file directly in your workspace under the `exports/` folder.

---

## 🧪 Testing

CritiqueFlow is built with a test-first methodology. To run the complete suite of **138 unit tests**:

```bash
# Verify all configurations, client parsers, harness logic, and routes
pytest tests/ -v
```

*Note: All unit tests run against simulated API responses using unittest mocks; no active internet connection or LLM billing is required for testing.*

---

## 📄 License

CritiqueFlow is open-source software licensed under the [MIT License](LICENSE).
