# API Setup Guide — Free LLM Endpoints for Testing

> This guide helps you configure a real LLM endpoint for manual testing and integration
> verification. **Automated tests (pytest) do NOT need a real API key** — they use mocks.
> This guide is only needed for manual smoke testing and end-to-end verification.

---

## 🎯 Quick Setup (Recommended: Google AI Studio)

**Time to setup: ~2 minutes. No credit card required.**

### Step 1: Get an API Key
1. Go to [https://aistudio.google.com/apikey](https://aistudio.google.com/apikey)
2. Sign in with any Google account
3. Click **"Create API key"**
4. Copy the key (starts with `AIza...`)

### Step 2: Configure `.env`
```bash
cd audit-harness
cp .env.example .env
```

Edit `.env` with these values:
```env
# === LLM Configuration (Google AI Studio - Gemini) ===
LLM_ENDPOINT=https://generativelanguage.googleapis.com/v1beta/openai/chat/completions
LLM_API_KEY=AIza_YOUR_KEY_HERE
LLM_MODEL=gemini-2.0-flash
LLM_TEMPERATURE=0.3
LLM_TOP_P=0.9
LLM_TOP_K=40
LLM_MAX_TOKENS=8192

# === Harness Behavior ===
MAX_ITERATION_DEPTH=3
EARLY_STOP_CONFIDENCE=0.85

# === Server ===
HOST=127.0.0.1
PORT=5000

# === Security ===
ALLOWED_OUTBOUND_HOSTS=generativelanguage.googleapis.com
KILL_ON_VIOLATION=true
ENABLE_NETWORK_GUARD=true
```

### Step 3: Test the Connection
```bash
cd audit-harness
python -c "
from core.llm_client import call_llm_raw
response = call_llm_raw('Say hello in exactly 5 words.')
print('SUCCESS:', response)
"
```

### Rate Limits (Free Tier)
| Metric | Limit |
|--------|-------|
| Requests/minute | 15 |
| Requests/day | 1,500 |
| Tokens/minute | 1,000,000 |

These limits are generous for testing. At 6 LLM calls per query, you can run ~2 queries per minute.

---

## 🔄 Fallback Option: Groq (If Gemini Hits Limits)

**Time to setup: ~3 minutes. No credit card required.**

### Step 1: Get an API Key
1. Go to [https://console.groq.com](https://console.groq.com)
2. Sign up with Google/GitHub account
3. Navigate to **API Keys** → **Create API Key**
4. Copy the key (starts with `gsk_...`)

### Step 2: Update `.env`
```env
# === LLM Configuration (Groq - Llama) ===
LLM_ENDPOINT=https://api.groq.com/openai/v1/chat/completions
LLM_API_KEY=gsk_YOUR_KEY_HERE
LLM_MODEL=llama-3.3-70b-versatile
LLM_TEMPERATURE=0.3
LLM_TOP_P=0.9
LLM_TOP_K=40
LLM_MAX_TOKENS=8192

# === Security ===
ALLOWED_OUTBOUND_HOSTS=api.groq.com
```

### Rate Limits (Free Tier)
| Metric | Limit |
|--------|-------|
| Requests/minute | 30 |
| Requests/day | 14,400 |
| Tokens/minute | 6,000 |

> **Note:** Groq's free tier has lower token-per-minute limits but higher request-per-minute.
> If you hit rate limits, reduce `MAX_ITERATION_DEPTH` to 2 or increase delays.

---

## 🏢 Production Configuration (Corporate Gateway)

For the actual production deployment with the corporate `/invoke` gateway:

```env
# === LLM Configuration (Corporate Gateway) ===
LLM_ENDPOINT=https://YOUR_INTERNAL_HOST/invoke
LLM_API_KEY=YOUR_BEARER_TOKEN
LLM_MODEL=claude-sonnet-4-20250514
LLM_TEMPERATURE=0.3
LLM_TOP_P=0.9
LLM_TOP_K=40
LLM_MAX_TOKENS=8192

# === Security ===
ALLOWED_OUTBOUND_HOSTS=YOUR_INTERNAL_HOST
KILL_ON_VIOLATION=true
ENABLE_NETWORK_GUARD=true
```

The `llm_client.py` automatically handles both response formats:
- **OpenAI format** (`choices[0].message.content`) — used by Gemini, Groq, OpenAI
- **Anthropic format** (`content[0].text`) — used by Anthropic API, AWS Bedrock

---

## 🧪 Verify Your Setup

After configuring any endpoint, run this verification:

```bash
cd audit-harness

# 1. Test basic connectivity
python -c "
from core.llm_client import call_llm_raw
response = call_llm_raw('Reply with exactly: HARNESS_TEST_OK')
print('LLM Response:', response)
assert 'HARNESS_TEST_OK' in response or len(response) > 0, 'Empty response!'
print('✅ LLM connectivity verified')
"

# 2. Test evaluator JSON generation
python -c "
from core.llm_client import call_llm_raw
import json
prompt = '''Return ONLY a JSON object with this structure, no other text:
{\"sufficient\": true, \"confidence\": 0.95, \"gaps_identified\": [], \"follow_up_challenge\": null, \"reasoning\": \"Test passed\"}'''
response = call_llm_raw(prompt)
print('Raw response:', response[:200])
# Try parsing
try:
    data = json.loads(response)
    print('✅ Direct JSON parse works')
except:
    import re
    match = re.search(r'\{.*?\}', response, re.DOTALL)
    if match:
        data = json.loads(match.group())
        print('✅ JSON extracted from response')
    else:
        print('❌ Could not extract JSON - evaluator fallback will trigger')
"

# 3. Test full harness flow (if both tests above pass)
python -c "
from core.harness_engine import run_harness
chain = run_harness('What are the key risks in a Hull-White one-factor interest rate model used for CVA computation?')
print(f'✅ Harness completed: {chain.total_iterations} iterations, early_stopped={chain.early_stopped}')
print(f'Final output preview: {chain.final_output[:200]}...')
"
```

---

## 🛡️ Security Notes

- **Never commit `.env` files** to version control. The `.gitignore` excludes them.
- **API keys are sensitive** — treat free-tier keys with the same care as production keys.
- **The network guard** (when enabled) ensures only the configured endpoint receives traffic.
- **Both Google AI Studio and Groq** are legitimate, well-established API providers with SOC2/ISO certifications.
- **No data retention concerns for testing** — both providers' free tiers have clear data usage policies. However, do NOT send real audit documents or sensitive client data through free-tier APIs. Use synthetic test data only.

---

## 📋 Endpoint Comparison

| Feature | Google AI Studio (Gemini) | Groq |
|---------|--------------------------|------|
| **Signup** | Google account | Google/GitHub |
| **Credit card** | No | No |
| **Free RPM** | 15 | 30 |
| **Free RPD** | 1,500 | 14,400 |
| **Response quality** | Excellent (Gemini 2.0 Flash) | Excellent (Llama 3.3 70B) |
| **JSON compliance** | Good — usually returns clean JSON | Good — usually returns clean JSON |
| **Speed** | ~1-3s per request | ~0.5-1s per request |
| **OpenAI compatible** | ✅ | ✅ |
| **Best for** | Primary testing | Fallback / high-volume testing |
