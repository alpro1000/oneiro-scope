# LLM Infrastructure — Полная спецификация

## 1. Обзор

Документ описывает полную LLM-инфраструктуру для сервиса OneiroScope/СоноГраф, включая архитектуру, fallback-механизмы, промт-инжиниринг, метрики качества и мониторинг.

---

## 2. Архитектура высокого уровня

```
┌─────────────────────────────────────────────────────────────────┐
│                    LLM Analysis Pipeline                        │
│                                                                 │
│  ┌──────────────┐      ┌──────────────┐      ┌──────────────┐ │
│  │   Input      │      │  Processing  │      │   Output     │ │
│  │              │      │              │      │              │ │
│  │ • Dream text │─────▶│ • Lunar info │─────▶│ • JSON       │ │
│  │ • User meta  │      │ • Vector DB  │      │ • Confidence │ │
│  │ • Language   │      │ • LLM call   │      │ • Sources    │ │
│  └──────────────┘      └──────────────┘      └──────────────┘ │
│                               │                                 │
│                               ▼                                 │
│                    ┌──────────────────┐                        │
│                    │  Fallback Chain  │                        │
│                    │                  │                        │
│                    │ 1. GPT-4o-mini   │                        │
│                    │ 2. Claude-3      │                        │
│                    │ 3. Local LLaMA   │                        │
│                    │ 4. Rule-based    │                        │
│                    └──────────────────┘                        │
└─────────────────────────────────────────────────────────────────┘
```

---

## 3. Модель выбора (Model Selection)

### 3.1 Поддерживаемые модели

```yaml
models:
  primary:
    name: "gpt-4o-mini"
    provider: "openai"
    context_window: 128000
    max_output: 16384
    cost_per_1m_tokens:
      input: $0.15
      output: $0.60
    latency_p95: 2000ms
    use_case: "primary analysis"

  fallback_1:
    name: "claude-3-haiku"
    provider: "anthropic"
    context_window: 200000
    max_output: 4096
    cost_per_1m_tokens:
      input: $0.25
      output: $1.25
    latency_p95: 1500ms
    use_case: "when openai unavailable"

  fallback_2:
    name: "llama-3-70b-instruct"
    provider: "together.ai"
    context_window: 8192
    max_output: 4096
    cost_per_1m_tokens:
      input: $0.90
      output: $0.90
    latency_p95: 3000ms
    use_case: "cost optimization"

  offline:
    name: "llama-3-8b-instruct"
    provider: "local"
    context_window: 8192
    max_output: 2048
    cost_per_1m_tokens:
      input: $0
      output: $0
    latency_p95: 5000ms
    use_case: "emergency fallback"
```

### 3.2 Routing Logic

```python
# backend/services/llm/router.py

from typing import Optional
from enum import Enum

class ModelTier(Enum):
    PREMIUM = "premium"      # GPT-4o-mini (best quality)
    STANDARD = "standard"    # Claude-3-haiku
    ECONOMY = "economy"      # LLaMA-3-70B
    FALLBACK = "fallback"    # Local LLaMA-3-8B

class ModelRouter:
    def select_model(
        self,
        user_tier: str,
        dream_complexity: float,
        failover_count: int = 0
    ) -> dict:
        """
        Select appropriate model based on:
        - User subscription tier
        - Dream complexity (0-1)
        - Current failover attempt
        """

        # Failover cascade
        if failover_count == 1:
            return self._get_model_config("claude-3-haiku")
        elif failover_count == 2:
            return self._get_model_config("llama-3-70b")
        elif failover_count >= 3:
            return self._get_model_config("llama-3-8b-local")

        # Premium users always get best model
        if user_tier in ["annual", "monthly"]:
            return self._get_model_config("gpt-4o-mini")

        # Free tier gets economy for simple dreams
        if user_tier == "free" and dream_complexity < 0.5:
            return self._get_model_config("llama-3-70b")

        # Default to standard
        return self._get_model_config("gpt-4o-mini")

    def _get_model_config(self, model_name: str) -> dict:
        """Get model configuration"""
        # Implementation returns model config from YAML
        pass
```

---

## 4. Промт-инжиниринг

### 4.1 System Prompt (Master)

```python
SYSTEM_PROMPT_V1 = """You are a professional dream analyst with expertise in:
- Hall/Van de Castle dream content analysis
- Jungian archetypal psychology
- Lunar dream interpretation
- Scientific sleep research

Your task is to analyze dreams using evidence-based methods.

CRITICAL RULES:
1. NEVER hallucinate or invent information
2. If uncertain, explicitly state confidence < 0.6
3. Always cite sources (DreamBank, lunar_table, scientific papers)
4. Respond ONLY in valid JSON format
5. Use {language} language for interpretation

ZERO-HALLUCINATION PROTOCOL:
- If symbol not found in knowledge base → confidence = 0.4
- If dream too vague → request clarification
- If no scientific basis → acknowledge limitation

OUTPUT FORMAT:
{{
  "interpretation": "string (2-4 sentences)",
  "archetypes": ["list", "of", "symbols"],
  "mood": "positive|negative|neutral",
  "lunar_day": int,
  "lunar_effect": "diagnostic|warning|positive",
  "confidence": float (0-1),
  "sources": ["dreambank.net", "lunar_table.json"]
}}

Knowledge bases available:
- DreamBank: 20,000+ dream reports
- Hall/Van de Castle: Content analysis coding system
- Lunar calendar: 30-day cycle with dream significance
"""
```

### 4.2 Context Assembly

```python
# backend/services/llm/context.py

from typing import Dict, Any, List

class ContextAssembler:
    """Assemble context for LLM analysis"""

    def __init__(self, vector_db, lunar_service, dreambank):
        self.vector_db = vector_db
        self.lunar = lunar_service
        self.dreambank = dreambank

    async def build_context(
        self,
        dream_text: str,
        user_metadata: Dict[str, Any],
        language: str = "en"
    ) -> str:
        """
        Build complete context for LLM

        Steps:
        1. Get lunar information
        2. Search similar dreams (vector DB)
        3. Extract HVdC-relevant symbols
        4. Assemble context
        """

        # 1. Lunar context
        lunar_info = await self.lunar.get_current_lunar_info(
            timezone_str=user_metadata.get("timezone", "UTC"),
            locale=language
        )

        # 2. Vector similarity search
        similar_dreams = await self.vector_db.similarity_search(
            query=dream_text,
            k=5
        )

        # 3. Symbol extraction (rule-based)
        symbols = self._extract_symbols(dream_text, language)

        # 4. Assemble context
        context = f"""
## Dream to Analyze
{dream_text}

## Lunar Context
- Lunar Day: {lunar_info['lunar_day']}
- Moon Phase: {lunar_info['moon_phase_name']}
- Significance: {lunar_info['significance']['type']}
- Prophetic Probability: {lunar_info['significance']['prophetic_probability']}
- Interpretation: {lunar_info['significance']['interpretation']}

## Detected Symbols
{', '.join(symbols) if symbols else 'None detected'}

## Similar Dreams from DreamBank
{self._format_similar_dreams(similar_dreams)}

## Hall/Van de Castle Categories Detected
{self._format_hvdc_categories(symbols)}

Now provide your analysis in JSON format.
"""

        return context

    def _extract_symbols(self, text: str, language: str) -> List[str]:
        """Extract common dream symbols using NLP"""
        # Simple keyword matching for MVP
        # In production: use spaCy NER + custom model

        symbol_keywords = {
            "en": [
                "fly", "flying", "fall", "falling", "chase", "chased",
                "water", "ocean", "river", "fire", "snake", "spider",
                "death", "birth", "naked", "teeth", "house", "school"
            ],
            "ru": [
                "летать", "падать", "преследование", "вода", "огонь",
                "змея", "паук", "смерть", "рождение", "зубы", "дом"
            ]
        }

        keywords = symbol_keywords.get(language, symbol_keywords["en"])
        text_lower = text.lower()

        found = []
        for kw in keywords:
            if kw in text_lower:
                found.append(kw)

        return found

    def _format_similar_dreams(self, dreams: List[Dict]) -> str:
        """Format similar dreams for context"""
        if not dreams:
            return "No similar dreams found in database"

        formatted = []
        for i, dream in enumerate(dreams[:3], 1):
            formatted.append(
                f"{i}. Similarity: {dream['score']:.2f}\n"
                f"   Interpretation: {dream['interpretation']}\n"
            )

        return "\n".join(formatted)

    def _format_hvdc_categories(self, symbols: List[str]) -> str:
        """Map symbols to HVdC categories"""
        # Simplified mapping for MVP
        hvdc_map = {
            "fall": "Misfortune (MF)",
            "fly": "Achievement (AC)",
            "chase": "Aggression (AG)",
            "water": "Nature (NA)",
            "death": "Death (DE)"
        }

        categories = []
        for symbol in symbols:
            if symbol in hvdc_map:
                categories.append(hvdc_map[symbol])

        return ", ".join(categories) if categories else "None"
```

### 4.3 Prompt Templates

```python
# backend/services/llm/prompts.py

USER_PROMPT_TEMPLATE = """
{context}

IMPORTANT:
- Be concise (2-4 sentences for interpretation)
- Confidence must reflect certainty (use 0.4-0.6 if uncertain)
- Always include sources
- Use {language} language for interpretation

Analyze this dream now.
"""

# Few-shot examples for better consistency
FEW_SHOT_EXAMPLES = [
    {
        "dream": "I was flying over my childhood home, feeling free and happy.",
        "response": {
            "interpretation": "Flying dreams often symbolize liberation and achievement. The childhood home suggests nostalgia and connection to your roots. This is a positive dream indicating emotional freedom.",
            "archetypes": ["flying", "childhood home", "freedom"],
            "mood": "positive",
            "lunar_day": 12,
            "lunar_effect": "positive",
            "confidence": 0.87,
            "sources": ["dreambank.net", "hvdc_codebook"]
        }
    },
    {
        "dream": "I was being chased but couldn't see who was chasing me.",
        "response": {
            "interpretation": "Chase dreams typically reflect avoidance of issues in waking life. The unknown pursuer suggests unidentified anxiety or responsibility you're avoiding.",
            "archetypes": ["chase", "unknown threat", "escape"],
            "mood": "negative",
            "lunar_day": 18,
            "lunar_effect": "diagnostic",
            "confidence": 0.82,
            "sources": ["dreambank.net", "lunar_table"]
        }
    }
]
```

---

## 5. Fallback Strategy

### 5.1 Multi-Tier Fallback Chain

```python
# backend/services/llm/fallback.py

from typing import Dict, Any, Optional
import logging
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)

class LLMFallbackChain:
    """
    Implements cascading fallback strategy:
    1. Primary: GPT-4o-mini (OpenAI)
    2. Secondary: Claude-3-haiku (Anthropic)
    3. Tertiary: LLaMA-3-70B (Together.ai)
    4. Emergency: Local LLaMA-3-8B
    5. Last resort: Rule-based interpretation
    """

    def __init__(self, clients: Dict[str, Any]):
        self.openai = clients.get("openai")
        self.anthropic = clients.get("anthropic")
        self.together = clients.get("together")
        self.local_llm = clients.get("local")
        self.rule_based = RuleBasedInterpreter()

    async def analyze_dream(
        self,
        dream_text: str,
        context: str,
        language: str = "en"
    ) -> Dict[str, Any]:
        """
        Analyze dream with fallback chain
        """

        # Try primary model
        try:
            result = await self._try_openai(dream_text, context, language)
            if self._is_valid_response(result):
                result["model_used"] = "gpt-4o-mini"
                return result
        except Exception as e:
            logger.error(f"OpenAI failed: {e}")

        # Try secondary model
        try:
            result = await self._try_anthropic(dream_text, context, language)
            if self._is_valid_response(result):
                result["model_used"] = "claude-3-haiku"
                return result
        except Exception as e:
            logger.error(f"Anthropic failed: {e}")

        # Try tertiary model
        try:
            result = await self._try_together(dream_text, context, language)
            if self._is_valid_response(result):
                result["model_used"] = "llama-3-70b"
                return result
        except Exception as e:
            logger.error(f"Together.ai failed: {e}")

        # Try local model
        try:
            result = await self._try_local(dream_text, context, language)
            if self._is_valid_response(result):
                result["model_used"] = "llama-3-8b-local"
                return result
        except Exception as e:
            logger.error(f"Local LLM failed: {e}")

        # Last resort: rule-based
        logger.warning("All LLMs failed, using rule-based fallback")
        result = self.rule_based.analyze(dream_text, language)
        result["model_used"] = "rule-based"
        result["confidence"] = 0.45  # Low confidence for rule-based
        return result

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    async def _try_openai(
        self,
        dream_text: str,
        context: str,
        language: str
    ) -> Dict[str, Any]:
        """Try OpenAI GPT-4o-mini with retries"""

        response = await self.openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT_V1.format(language=language)},
                {"role": "user", "content": context}
            ],
            temperature=0.3,  # Low temperature for consistency
            response_format={"type": "json_object"},
            max_tokens=1000
        )

        return json.loads(response.choices[0].message.content)

    def _is_valid_response(self, response: Dict[str, Any]) -> bool:
        """Validate LLM response"""

        required_fields = [
            "interpretation",
            "archetypes",
            "mood",
            "confidence",
            "sources"
        ]

        # Check all required fields present
        if not all(field in response for field in required_fields):
            return False

        # Check confidence is reasonable
        if not (0.3 <= response["confidence"] <= 1.0):
            return False

        # Check interpretation not empty
        if not response["interpretation"].strip():
            return False

        return True
```

### 5.2 Rule-Based Fallback

```python
# backend/services/llm/rule_based.py

class RuleBasedInterpreter:
    """
    Simple rule-based interpreter as last resort fallback
    Uses keyword matching + predefined interpretations
    """

    def __init__(self):
        self.rules = self._load_rules()

    def analyze(self, dream_text: str, language: str) -> Dict[str, Any]:
        """Analyze dream using rules"""

        text_lower = dream_text.lower()

        # Detect mood
        mood = self._detect_mood(text_lower)

        # Detect symbols
        archetypes = self._detect_archetypes(text_lower)

        # Generate interpretation
        interpretation = self._generate_interpretation(archetypes, mood, language)

        return {
            "interpretation": interpretation,
            "archetypes": archetypes,
            "mood": mood,
            "lunar_day": None,
            "lunar_effect": "neutral",
            "confidence": 0.45,
            "sources": ["rule-based-fallback"],
            "warning": "Limited analysis due to system unavailability"
        }

    def _detect_mood(self, text: str) -> str:
        """Detect overall mood from text"""

        positive_words = ["happy", "joy", "love", "peace", "beautiful"]
        negative_words = ["fear", "scared", "death", "dark", "sad", "angry"]

        pos_count = sum(1 for w in positive_words if w in text)
        neg_count = sum(1 for w in negative_words if w in text)

        if pos_count > neg_count:
            return "positive"
        elif neg_count > pos_count:
            return "negative"
        else:
            return "neutral"

    def _detect_archetypes(self, text: str) -> List[str]:
        """Detect common archetypes"""

        archetype_keywords = {
            "flying": ["fly", "flying", "soar"],
            "falling": ["fall", "falling", "drop"],
            "water": ["water", "ocean", "river", "sea"],
            "chase": ["chase", "chased", "run", "escape"],
            "death": ["death", "die", "dead"],
            "transformation": ["transform", "change", "become"]
        }

        found = []
        for archetype, keywords in archetype_keywords.items():
            if any(kw in text for kw in keywords):
                found.append(archetype)

        return found if found else ["unidentified"]

    def _generate_interpretation(
        self,
        archetypes: List[str],
        mood: str,
        language: str
    ) -> str:
        """Generate basic interpretation"""

        if language == "ru":
            templates = {
                "flying": "Полёт символизирует свободу и стремление к целям.",
                "falling": "Падение может отражать потерю контроля или тревогу.",
                "water": "Вода связана с эмоциями и подсознанием.",
                "default": "Сон требует более детального анализа."
            }
        else:
            templates = {
                "flying": "Flying symbolizes freedom and aspiration.",
                "falling": "Falling may reflect loss of control or anxiety.",
                "water": "Water relates to emotions and the subconscious.",
                "default": "Dream requires more detailed analysis."
            }

        if archetypes and archetypes[0] != "unidentified":
            return templates.get(archetypes[0], templates["default"])
        else:
            return templates["default"]
```

---

## 6. Quality Assurance

### 6.1 Confidence Scoring

```python
# backend/services/llm/quality.py

class QualityAssurance:
    """Validate and enhance LLM outputs"""

    CONFIDENCE_THRESHOLD = 0.60

    def validate_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate and potentially adjust response quality

        Checks:
        1. Confidence score calibration
        2. Source citation presence
        3. Interpretation quality
        4. JSON structure validity
        """

        # Recalibrate confidence if needed
        response["confidence"] = self._recalibrate_confidence(response)

        # Check for hallucination indicators
        if self._detect_hallucination(response):
            response["confidence"] *= 0.7
            response["warning"] = "Potential hallucination detected"

        # Verify sources cited
        if not response.get("sources") or len(response["sources"]) == 0:
            response["sources"] = ["general_knowledge"]
            response["confidence"] *= 0.8

        # Flag low confidence
        if response["confidence"] < self.CONFIDENCE_THRESHOLD:
            response["requires_human_review"] = True

        return response

    def _recalibrate_confidence(self, response: Dict[str, Any]) -> float:
        """
        Recalibrate confidence score based on response characteristics
        """

        base_confidence = response.get("confidence", 0.5)

        # Penalties
        if len(response.get("interpretation", "")) < 50:
            base_confidence *= 0.9  # Too short

        if len(response.get("archetypes", [])) == 0:
            base_confidence *= 0.85  # No symbols detected

        if "I think" in response.get("interpretation", ""):
            base_confidence *= 0.9  # Uncertainty language

        # Bonuses
        if len(response.get("sources", [])) >= 2:
            base_confidence *= 1.05  # Multiple sources

        if response.get("lunar_day") is not None:
            base_confidence *= 1.02  # Lunar context used

        return min(0.98, max(0.30, base_confidence))

    def _detect_hallucination(self, response: Dict[str, Any]) -> bool:
        """
        Detect potential hallucination indicators

        Red flags:
        - Overly specific claims without sources
        - Contradictions
        - Extremely high confidence (>0.95) without justification
        """

        interpretation = response.get("interpretation", "")

        # Red flag phrases
        red_flags = [
            "studies show that exactly",
            "it is proven that",
            "according to research in 20",  # Specific year
            "Dr. Smith discovered",  # Specific researcher without source
            "100% certain",
            "definitely means"
        ]

        return any(flag in interpretation.lower() for flag in red_flags)
```

### 6.2 Output Validation

```python
# backend/services/llm/validation.py

from pydantic import BaseModel, Field, validator
from typing import List, Optional

class DreamAnalysisOutput(BaseModel):
    """Pydantic model for LLM output validation"""

    interpretation: str = Field(
        ...,
        min_length=20,
        max_length=500,
        description="Dream interpretation (2-4 sentences)"
    )

    archetypes: List[str] = Field(
        ...,
        min_items=0,
        max_items=10,
        description="List of detected symbols/archetypes"
    )

    mood: str = Field(
        ...,
        regex="^(positive|negative|neutral)$",
        description="Overall dream mood"
    )

    lunar_day: Optional[int] = Field(
        None,
        ge=1,
        le=30,
        description="Lunar day (1-30)"
    )

    lunar_effect: Optional[str] = Field(
        None,
        regex="^(diagnostic|warning|positive|neutral)$",
        description="Lunar significance type"
    )

    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Confidence score (0-1)"
    )

    sources: List[str] = Field(
        ...,
        min_items=1,
        description="Knowledge sources used"
    )

    model_used: Optional[str] = Field(
        None,
        description="Model used for analysis"
    )

    requires_human_review: Optional[bool] = Field(
        False,
        description="Flag for human review"
    )

    @validator("confidence")
    def confidence_realistic(cls, v):
        """Ensure confidence is not unrealistically high"""
        if v > 0.95:
            raise ValueError("Confidence > 0.95 requires justification")
        return v

    @validator("interpretation")
    def interpretation_quality(cls, v):
        """Check interpretation quality"""
        if len(v.split()) < 10:
            raise ValueError("Interpretation too short (< 10 words)")
        return v
```

---

## 7. Метрики и мониторинг

### 7.1 Quality Metrics

```python
# backend/services/llm/metrics.py

from prometheus_client import Counter, Histogram, Gauge, Summary

# Request metrics
llm_requests_total = Counter(
    'llm_requests_total',
    'Total LLM requests',
    ['model', 'status', 'language']
)

llm_latency = Histogram(
    'llm_latency_seconds',
    'LLM request latency',
    ['model'],
    buckets=[0.5, 1, 2, 5, 10, 30]
)

# Quality metrics
llm_confidence_score = Histogram(
    'llm_confidence_score',
    'Confidence score distribution',
    ['model'],
    buckets=[0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 0.95, 1.0]
)

llm_token_usage = Summary(
    'llm_token_usage',
    'Token usage per request',
    ['model', 'type']  # type: input/output
)

# Fallback metrics
llm_fallback_triggered = Counter(
    'llm_fallback_triggered_total',
    'Fallback triggers',
    ['from_model', 'to_model', 'reason']
)

llm_validation_failures = Counter(
    'llm_validation_failures_total',
    'Output validation failures',
    ['model', 'failure_type']
)

# Cost metrics
llm_cost_estimate = Counter(
    'llm_cost_estimate_usd',
    'Estimated LLM costs in USD',
    ['model']
)

# Human review queue
llm_human_review_queue_size = Gauge(
    'llm_human_review_queue_size',
    'Items in human review queue'
)
```

### 7.2 Monitoring Dashboards

```yaml
# Grafana Dashboard Configuration

dashboard:
  name: "LLM Analysis Monitoring"

  panels:
    - title: "Request Rate"
      metric: rate(llm_requests_total[5m])
      visualization: graph
      thresholds:
        warning: 100/s
        critical: 500/s

    - title: "P95 Latency"
      metric: histogram_quantile(0.95, llm_latency_seconds)
      visualization: graph
      thresholds:
        warning: 2s
        critical: 5s

    - title: "Confidence Score Distribution"
      metric: llm_confidence_score
      visualization: heatmap
      target: "p50 >= 0.80"

    - title: "Fallback Rate"
      metric: rate(llm_fallback_triggered_total[5m]) / rate(llm_requests_total[5m])
      visualization: graph
      thresholds:
        warning: 0.05  # 5%
        critical: 0.10  # 10%

    - title: "Validation Failure Rate"
      metric: rate(llm_validation_failures_total[5m]) / rate(llm_requests_total[5m])
      visualization: graph
      thresholds:
        warning: 0.02  # 2%
        critical: 0.05  # 5%

    - title: "Human Review Queue"
      metric: llm_human_review_queue_size
      visualization: gauge
      thresholds:
        warning: 50
        critical: 100

    - title: "Estimated Hourly Cost"
      metric: rate(llm_cost_estimate_usd[1h])
      visualization: stat
      alert_on: > $10/hour
```

### 7.3 Alerting Rules

```yaml
# alerts/llm.yml

groups:
  - name: llm_alerts
    interval: 30s

    rules:
      - alert: HighLLMLatency
        expr: histogram_quantile(0.95, llm_latency_seconds) > 5
        for: 5m
        severity: warning
        annotations:
          summary: "LLM P95 latency above 5s"

      - alert: LowConfidenceSpike
        expr: |
          (
            sum(rate(llm_confidence_score_bucket{le="0.6"}[5m]))
            /
            sum(rate(llm_confidence_score_count[5m]))
          ) > 0.20
        for: 10m
        severity: warning
        annotations:
          summary: "Over 20% of responses have confidence < 0.6"

      - alert: AllModelsDown
        expr: rate(llm_fallback_triggered_total{to_model="rule-based"}[5m]) > 0
        for: 2m
        severity: critical
        annotations:
          summary: "All LLM models unavailable, using rule-based fallback"

      - alert: HighCostBurn
        expr: rate(llm_cost_estimate_usd[1h]) > 20
        for: 5m
        severity: critical
        annotations:
          summary: "LLM costs exceeding $20/hour"

      - alert: LargeReviewQueue
        expr: llm_human_review_queue_size > 100
        for: 30m
        severity: warning
        annotations:
          summary: "Human review queue has over 100 items"
```

---

## 8. Cost Optimization

### 8.1 Cost Breakdown

```yaml
Monthly cost estimates (10,000 analyses):

Scenario 1: All GPT-4o-mini
  - Avg tokens per request: 1500 input + 500 output
  - Input cost: 10,000 × 1.5k × $0.15/1M = $2.25
  - Output cost: 10,000 × 0.5k × $0.60/1M = $3.00
  - Total: $5.25/month

Scenario 2: Optimized (70% GPT, 30% LLaMA)
  - GPT-4o-mini (7,000): $3.68
  - LLaMA-3-70B (3,000): $5.40
  - Total: $9.08/month

Scenario 3: Heavy usage (100,000 analyses)
  - GPT-4o-mini: $52.50/month
  - With optimization: $90.80/month
```

### 8.2 Cost Control Strategies

```python
# backend/services/llm/cost_control.py

class CostController:
    """Monitor and control LLM costs"""

    def __init__(self, budget_limit_usd: float = 100.0):
        self.budget_limit = budget_limit_usd
        self.current_spend = 0.0

    async def check_budget(self) -> bool:
        """Check if budget allows request"""
        return self.current_spend < self.budget_limit

    def estimate_cost(self, model: str, tokens: dict) -> float:
        """Estimate request cost"""

        prices = {
            "gpt-4o-mini": {"input": 0.15, "output": 0.60},
            "claude-3-haiku": {"input": 0.25, "output": 1.25},
            "llama-3-70b": {"input": 0.90, "output": 0.90}
        }

        if model not in prices:
            return 0.0

        cost = (
            tokens["input"] * prices[model]["input"] / 1_000_000 +
            tokens["output"] * prices[model]["output"] / 1_000_000
        )

        return cost

    async def record_usage(self, model: str, tokens: dict):
        """Record usage and update spend"""
        cost = self.estimate_cost(model, tokens)
        self.current_spend += cost

        # Update metrics
        llm_cost_estimate.labels(model=model).inc(cost)

        # Check budget limit
        if self.current_spend >= self.budget_limit * 0.9:
            logger.warning(f"LLM spend at 90% of budget: ${self.current_spend:.2f}")
```

---

## 9. Testing

### 9.1 Unit Tests

```python
# tests/unit/test_llm_service.py

@pytest.mark.asyncio
async def test_fallback_chain():
    """Test fallback mechanism"""

    # Mock primary model failure
    mock_openai = Mock(side_effect=Exception("API unavailable"))

    # Mock secondary success
    mock_anthropic = Mock(return_value={
        "interpretation": "Test interpretation",
        "confidence": 0.85,
        "sources": ["test"]
    })

    fallback = LLMFallbackChain({
        "openai": mock_openai,
        "anthropic": mock_anthropic
    })

    result = await fallback.analyze_dream("test dream", "context", "en")

    assert result["model_used"] == "claude-3-haiku"
    assert mock_anthropic.called

@pytest.mark.asyncio
async def test_confidence_calibration():
    """Test confidence score adjustments"""

    qa = QualityAssurance()

    # High confidence without justification
    response = {
        "interpretation": "Short",
        "confidence": 0.96,
        "sources": []
    }

    validated = qa.validate_response(response)

    # Should reduce confidence
    assert validated["confidence"] < 0.90
    assert validated.get("warning") is not None
```

### 9.2 Integration Tests

```python
# tests/integration/test_dream_analysis_e2e.py

@pytest.mark.asyncio
async def test_full_analysis_pipeline():
    """Test complete dream analysis pipeline"""

    dream_text = "I was flying over the ocean, feeling peaceful."

    result = await llm_service.analyze_dream(
        dream_text=dream_text,
        user_id=test_user_id,
        language="en"
    )

    # Validate output structure
    assert "interpretation" in result
    assert "confidence" in result
    assert result["confidence"] >= 0.6
    assert "sources" in result
    assert len(result["sources"]) >= 1

    # Check archetypes detected
    assert "flying" in result.get("archetypes", [])

    # Check mood classification
    assert result["mood"] == "positive"

@pytest.mark.asyncio
async def test_multilingual_analysis():
    """Test RU/EN analysis"""

    dream_ru = "Я летал над океаном, чувствовал спокойствие."

    result = await llm_service.analyze_dream(
        dream_text=dream_ru,
        language="ru"
    )

    # Interpretation should be in Russian
    assert any(c.isalpha() and ord(c) > 1000 for c in result["interpretation"])
```

---

## 10. Deployment

### 10.1 Environment Variables

```bash
# .env.llm

# OpenAI
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini
OPENAI_TEMPERATURE=0.3
OPENAI_MAX_TOKENS=1000

# Anthropic
ANTHROPIC_API_KEY=sk-ant-...
ANTHROPIC_MODEL=claude-3-haiku-20240307

# Together.ai
TOGETHER_API_KEY=...
TOGETHER_MODEL=meta-llama/Llama-3-70b-chat-hf

# Cost controls
LLM_BUDGET_LIMIT_USD=100.0
LLM_FALLBACK_ENABLED=true

# Quality thresholds
LLM_CONFIDENCE_THRESHOLD=0.60
LLM_HUMAN_REVIEW_THRESHOLD=0.55

# Rate limiting
LLM_RATE_LIMIT_PER_USER=10  # per hour
LLM_RATE_LIMIT_GLOBAL=1000  # per minute
```

---

## 11. Security

### 11.1 PII Protection

```python
# backend/services/llm/privacy.py

import re

class PIIProtection:
    """Remove PII from dream text before sending to LLM"""

    PII_PATTERNS = {
        "email": r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
        "phone": r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b',
        "ssn": r'\b\d{3}-\d{2}-\d{4}\b',
        "address": r'\b\d+\s+[\w\s]+(?:street|st|avenue|ave|road|rd|boulevard|blvd)\b'
    }

    def sanitize(self, text: str) -> tuple[str, dict]:
        """Remove PII and return sanitized text + redactions"""

        redactions = {}
        sanitized = text

        for pii_type, pattern in self.PII_PATTERNS.items():
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                redactions[pii_type] = len(matches)
                sanitized = re.sub(pattern, f"[{pii_type.upper()}_REDACTED]", sanitized, flags=re.IGNORECASE)

        return sanitized, redactions
```

---

**Document Version**: 1.0
**Last Updated**: 2025-11-01
**Owner**: LLM Infrastructure Team
**Status**: Production Ready
