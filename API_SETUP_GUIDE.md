# API Setup Guide

> This guide helps you configure a real LLM endpoint for running the CritiqueFlow harness. 
> *(Note: Automated `pytest` tests use local mocks and do NOT need an API key).*

---

## 🎯 Recommended Evaluator Model: GPT-OSS-120B (Cloud)

For the Evaluator agent, we highly recommend using **GPT-OSS-120B**. Released as an open-weight, 117B parameter Mixture-of-Experts (MoE) reasoning model, it provides full access to its internal chain-of-thought and allows for configurable reasoning effort. This makes it exceptionally skilled at the deep, critical analysis required for auditing.

**Where to access it for free:**
You can access `gpt-oss-120b` for free (or via their free-tier models) on [OpenRouter.ai](https://openrouter.ai). Simply create an account, generate an API key, and point CritiqueFlow to their OpenAI-compatible endpoint.

---

## 💻 Lightweight Local Execution (Ollama)

If you prefer to run the harness entirely offline on your local machine, you should use a lightweight reasoning model. We recommend models like `deepseek-r1:8b` or `llama3.1:8b`, which fit comfortably on a standard laptop with at least 8GB to 16GB of RAM.

To get started locally:
1. Install [Ollama](https://ollama.com/)
2. Run your preferred lightweight model: `ollama run deepseek-r1:8b`

---

## ⚙️ Quick Configuration

1. Navigate to the harness directory and copy the template environment file:
```bash
cd audit-harness
cp .env.example .env
```

2. Edit your `.env` file with your chosen endpoint, key, and model.

### Example A: Using OpenRouter (Cloud)
```env
# === LLM Configuration ===
LLM_ENDPOINT=https://openrouter.ai/api/v1/chat/completions
LLM_API_KEY=sk-or-v1-YOUR_KEY_HERE
LLM_MODEL=openai/gpt-oss-120b

# === Harness Behavior ===
LLM_TEMPERATURE=0.3
MAX_ITERATION_DEPTH=3
```

### Example B: Using Ollama (Local)
```env
# === LLM Configuration ===
LLM_ENDPOINT=http://127.0.0.1:11434/v1/chat/completions
LLM_API_KEY=ollama
LLM_MODEL=deepseek-r1:8b

# === Harness Behavior ===
LLM_TEMPERATURE=0.3
MAX_ITERATION_DEPTH=3
```

---

## 🛡️ Security Reminders

- **Never commit `.env` files** to version control. The repository's `.gitignore` excludes them by default.
- **Network Guard:** If you have `ENABLE_NETWORK_GUARD=true` in your `.env`, ensure that `ALLOWED_OUTBOUND_HOSTS` matches the domain of your endpoint (e.g., `openrouter.ai` or `127.0.0.1`).
