# LLM Providers Guide

OneiroScope supports multiple LLM providers with automatic fallback. The system tries providers in order of cost (cheapest first) until one succeeds.

## Supported Providers

### 1. Groq (Recommended for Development)

**Cost:** FREE tier available
**Speed:** ⚡ Very Fast (fastest inference)
**Model:** `llama-3.1-8b-instant`

**Pros:**
- Completely free tier
- Extremely fast inference (< 1s response)
- Good quality for astrology/dreams interpretation
- Great for development and testing

**Cons:**
- Rate limits on free tier
- Slightly lower quality than GPT-4o-mini or Claude

**Setup:**
1. Sign up at https://console.groq.com/
2. Create API key
3. Add to `.env`: `GROQ_API_KEY=gsk-...`

---

### 2. Together AI

**Cost:** $0.20 per 1M tokens (very cheap)
**Speed:** ⚡ Fast
**Model:** `meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo`

**Pros:**
- Very cheap (5x cheaper than Claude)
- Wide selection of open-source models
- Good for high-volume applications

**Cons:**
- Requires credit card
- Slightly lower quality than proprietary models

**Setup:**
1. Sign up at https://api.together.xyz/
2. Add credits
3. Create API key
4. Add to `.env`: `TOGETHER_API_KEY=...`

---

### 3. OpenAI (GPT-4o-mini)

**Cost:** $0.15 per 1M input tokens, $0.60 per 1M output
**Speed:** 🚀 Fast
**Model:** `gpt-4o-mini`

**Pros:**
- High quality interpretations
- Reliable and stable
- Good multilingual support
- Cheaper than Claude

**Cons:**
- Requires payment
- Not as cheap as Groq/Together

**Setup:**
1. Sign up at https://platform.openai.com/
2. Add payment method
3. Create API key
4. Add to `.env`: `OPENAI_API_KEY=sk-...`

---

### 4. Anthropic (Claude Haiku)

**Cost:** $0.25 per 1M input tokens, $1.25 per 1M output
**Speed:** 🚀 Fast
**Model:** `claude-3-haiku-20240307`

**Pros:**
- Excellent quality
- Good at nuanced interpretations
- Strong safety features
- Great for esoteric/mystical content

**Cons:**
- Most expensive option
- Requires payment

**Setup:**
1. Sign up at https://console.anthropic.com/
2. Add payment method
3. Create API key
4. Add to `.env`: `ANTHROPIC_API_KEY=sk-ant-...`

---

## Configuration

### Basic Setup (Recommended)

For development, configure only Groq (free):

```env
GROQ_API_KEY=gsk-your-key-here
```

### Production Setup (Recommended)

For production, configure multiple providers for redundancy:

```env
GROQ_API_KEY=gsk-...        # Primary (free tier)
OPENAI_API_KEY=sk-...       # Fallback #1 (good quality)
ANTHROPIC_API_KEY=sk-ant-...  # Fallback #2 (best quality)
```

### High-Volume Setup

For high-volume applications where cost matters:

```env
TOGETHER_API_KEY=...        # Primary (cheapest paid)
GROQ_API_KEY=gsk-...       # Fallback (free tier)
```

---

## How Automatic Fallback Works

The system tries providers in this order:

1. **Groq** (if API key configured)
2. **Together AI** (if API key configured)
3. **OpenAI** (if API key configured)
4. **Anthropic** (if API key configured)
5. **Fallback Mode** (rule-based, no AI)

If a provider fails (network error, rate limit, etc.), the system automatically tries the next one.

---

## Cost Estimation

### Typical Request Sizes

| Service | Input Tokens | Output Tokens | Total |
|---------|-------------|---------------|-------|
| Natal Chart | ~800 | ~1200 | ~2000 |
| Horoscope | ~600 | ~1000 | ~1600 |
| Dream Analysis | ~500 | ~1000 | ~1500 |
| Event Forecast | ~700 | ~800 | ~1500 |

### Monthly Cost Examples (1000 requests)

| Provider | Cost per Request | Monthly Cost (1000 req) |
|----------|-----------------|------------------------|
| Groq | $0.00 | **$0.00** |
| Together AI | $0.0004 | **$0.40** |
| OpenAI (GPT-4o-mini) | $0.0006 | **$0.60** |
| Anthropic (Claude) | $0.001 | **$1.00** |

**Recommendation:** Use Groq for development/testing, switch to paid providers only if needed for quality/volume.

---

## Performance Comparison

Based on benchmarks:

| Provider | Response Time | Quality Score | Cost Score |
|----------|--------------|--------------|------------|
| Groq | ⭐⭐⭐⭐⭐ (0.5-1s) | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| Together AI | ⭐⭐⭐⭐ (1-2s) | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| OpenAI | ⭐⭐⭐⭐ (1-3s) | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| Anthropic | ⭐⭐⭐ (2-4s) | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ |

---

## Troubleshooting

### "All LLM providers failed"

**Cause:** No API keys configured or all providers returned errors.

**Solution:**
1. Check `.env` file - at least one API key should be set
2. Verify API keys are valid
3. Check API provider status pages
4. Review logs for specific error messages

### "Using fallback interpretation"

**Cause:** No LLM API keys configured.

**Solution:**
- Add at least one API key to `.env`
- Restart backend server

### High costs with paid providers

**Solution:**
1. Switch to Groq (free tier)
2. Implement request caching (Redis)
3. Reduce `max_tokens` in config
4. Use cheaper providers (Together AI)

---

## Advanced Configuration

### Using Specific Provider Only

In code, you can force a specific provider:

```python
from backend.core.llm_provider import UniversalLLMProvider, LLMProvider

llm = UniversalLLMProvider(
    preferred_provider=LLMProvider.OPENAI  # Use only OpenAI
)
```

### Custom Temperature/Tokens

```python
llm = UniversalLLMProvider(
    max_tokens=1000,      # Reduce tokens to save cost
    temperature=0.3,      # Lower = more deterministic
)
```

---

## Rate Limits

| Provider | Free Tier | Paid Tier |
|----------|-----------|-----------|
| Groq | 30 req/min | Higher limits |
| Together AI | N/A | ~300 req/min |
| OpenAI | 3 req/min | 3500 req/min |
| Anthropic | N/A | 50 req/min |

**Tip:** Configure multiple providers to distribute load and avoid rate limits.

---

## Security Best Practices

1. **Never commit API keys** to git
2. Use `.env` file (ignored by git)
3. Rotate API keys regularly
4. Use separate keys for dev/staging/prod
5. Monitor API usage dashboards
6. Set spending limits on provider dashboards

---

## Support

For issues or questions:
- Check provider documentation
- Review logs: `backend/logs/`
- Open issue on GitHub
