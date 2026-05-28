"""
Universal LLM Provider with multiple model support and automatic fallback.

Supports (in order of priority by cost):
1. Groq (free tier, very fast)
2. Google Gemini (very cheap, good quality)
3. Google Vertex AI (Gemini via GCP — enterprise route, same model)
4. Together AI (cheap open-source models)
5. OpenAI GPT-4o-mini (cheaper than Claude)
6. Anthropic Claude Haiku (direct API)
7. AWS Bedrock (Claude via AWS — enterprise route, same model)

Vertex and Bedrock reach the same Gemini/Claude models through cloud
provider gateways. They are useful when an org already has GCP/AWS billing,
data-residency, or private-networking requirements. Both are optional and
only activate when their credentials are configured.
"""

import asyncio
import json
import logging
import os
from enum import Enum
from typing import Optional, Tuple, List
import httpx

logger = logging.getLogger(__name__)


class LLMProvider(str, Enum):
    """Available LLM providers"""
    GROQ = "groq"
    GEMINI = "gemini"
    VERTEX = "vertex"
    TOGETHER = "together"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    BEDROCK = "bedrock"


class LLMModel:
    """LLM Model configuration"""

    def __init__(
        self,
        provider: LLMProvider,
        model_id: str,
        cost_per_1k_tokens: float,
        max_tokens: int = 4096,
        supports_system_prompt: bool = True,
    ):
        self.provider = provider
        self.model_id = model_id
        self.cost_per_1k_tokens = cost_per_1k_tokens
        self.max_tokens = max_tokens
        self.supports_system_prompt = supports_system_prompt


# Available models (ordered by cost, cheapest first)
AVAILABLE_MODELS = [
    # Groq - FREE tier, very fast
    LLMModel(
        provider=LLMProvider.GROQ,
        model_id="llama-3.1-8b-instant",
        cost_per_1k_tokens=0.0,  # Free tier
        max_tokens=8000,
    ),
    # Google Gemini - very cheap, good quality
    LLMModel(
        provider=LLMProvider.GEMINI,
        model_id="gemini-1.5-flash",
        cost_per_1k_tokens=0.000075,  # $0.075 per 1M input tokens (cheapest paid!)
        max_tokens=8192,
    ),
    # Google Vertex AI - same Gemini model via GCP gateway. Model id is
    # overridable with VERTEX_MODEL_ID (Vertex uses versioned ids like
    # "gemini-1.5-flash-002").
    LLMModel(
        provider=LLMProvider.VERTEX,
        model_id=os.getenv("VERTEX_MODEL_ID", "gemini-1.5-flash-002"),
        cost_per_1k_tokens=0.000075,
        max_tokens=8192,
    ),
    # Together AI - cheap open-source
    LLMModel(
        provider=LLMProvider.TOGETHER,
        model_id="meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo",
        cost_per_1k_tokens=0.0002,  # $0.20 per 1M tokens
        max_tokens=8000,
    ),
    # OpenAI GPT-4o-mini - cheap, good quality
    LLMModel(
        provider=LLMProvider.OPENAI,
        model_id="gpt-4o-mini",
        cost_per_1k_tokens=0.00015,  # $0.15 per 1M input tokens
        max_tokens=16000,
    ),
    # Anthropic Claude Haiku - direct API
    LLMModel(
        provider=LLMProvider.ANTHROPIC,
        model_id="claude-3-haiku-20240307",
        cost_per_1k_tokens=0.00025,  # $0.25 per 1M input tokens
        max_tokens=4096,
    ),
    # AWS Bedrock - same Claude model via AWS gateway. Model id is
    # overridable with BEDROCK_MODEL_ID.
    LLMModel(
        provider=LLMProvider.BEDROCK,
        model_id=os.getenv(
            "BEDROCK_MODEL_ID", "anthropic.claude-3-haiku-20240307-v1:0"
        ),
        cost_per_1k_tokens=0.00025,
        max_tokens=4096,
    ),
]


class UniversalLLMProvider:
    """
    Universal LLM provider with automatic fallback.

    Tries models in order of cost (cheapest first) until one succeeds.
    """

    def __init__(
        self,
        max_tokens: int = 2000,
        temperature: float = 0.7,
        preferred_provider: Optional[LLMProvider] = None,
    ):
        """
        Initialize UniversalLLMProvider.

        Args:
            max_tokens: Maximum tokens for response
            temperature: Temperature for generation
            preferred_provider: Preferred provider (or None for auto-select cheapest)
        """
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.preferred_provider = preferred_provider

        # Load API keys from environment
        self.api_keys = {
            LLMProvider.GROQ: os.getenv("GROQ_API_KEY"),
            LLMProvider.GEMINI: os.getenv("GEMINI_API_KEY"),
            LLMProvider.TOGETHER: os.getenv("TOGETHER_API_KEY"),
            LLMProvider.OPENAI: os.getenv("OPENAI_API_KEY"),
            LLMProvider.ANTHROPIC: os.getenv("ANTHROPIC_API_KEY"),
        }

        # Get available models. Simple-key providers are gated on their key;
        # Vertex/Bedrock are gated on cloud credentials (see _provider_configured).
        self.available_models = [
            model for model in AVAILABLE_MODELS
            if self._provider_configured(model.provider)
        ]

        if not self.available_models:
            logger.warning("No LLM API keys configured - will use fallback mode")
        else:
            providers = [m.provider.value for m in self.available_models]
            logger.info(f"LLM providers available: {', '.join(providers)}")

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
    ) -> Tuple[str, Optional[str]]:
        """
        Generate text using available LLM.

        Tries models in order of cost until one succeeds.

        Args:
            prompt: User prompt
            system_prompt: System prompt (optional)

        Returns:
            Tuple of (generated_text, provider_used)
        """
        if not self.available_models:
            return self._fallback_response(), None

        # If preferred provider specified, try it first
        models_to_try = self.available_models.copy()
        if self.preferred_provider:
            models_to_try.sort(
                key=lambda m: (m.provider != self.preferred_provider, m.cost_per_1k_tokens)
            )

        # Try each model until one succeeds
        for model in models_to_try:
            try:
                logger.info(f"Trying {model.provider.value}/{model.model_id}...")
                result = await self._call_provider(
                    model, prompt, system_prompt
                )
                logger.info(f"Success with {model.provider.value}")
                # Cost tracking — never raises (see cost_tracker.record).
                # ~4 chars/token is the standard rough estimate when the
                # provider does not return token usage.
                from backend.core import cost_tracker

                input_chars = len(prompt) + len(system_prompt or "")
                cost_tracker.record(
                    provider=model.provider.value,
                    input_tokens=max(1, input_chars // 4),
                    output_tokens=max(1, len(result) // 4),
                    cost_per_1k_tokens=model.cost_per_1k_tokens,
                )
                return result, model.provider.value
            except Exception as e:
                logger.warning(
                    f"Failed with {model.provider.value}: {str(e)}"
                )
                continue

        # All models failed - use fallback
        logger.error("All LLM providers failed - using fallback")
        return self._fallback_response(), None

    def _provider_configured(self, provider: "LLMProvider") -> bool:
        """Whether a provider has enough config to be usable.

        Simple-key providers need their API key. Vertex needs a GCP project
        plus credentials (an explicit token or discoverable ADC). Bedrock
        needs AWS credentials and the boto3 library.
        """
        if provider == LLMProvider.VERTEX:
            has_project = bool(
                os.getenv("VERTEX_PROJECT") or os.getenv("GOOGLE_CLOUD_PROJECT")
            )
            has_creds = bool(
                os.getenv("VERTEX_ACCESS_TOKEN")
                or os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
            )
            return has_project and has_creds
        if provider == LLMProvider.BEDROCK:
            has_creds = bool(
                os.getenv("AWS_ACCESS_KEY_ID") or os.getenv("AWS_PROFILE")
            )
            try:
                import boto3  # noqa: F401
            except ImportError:
                return False
            return has_creds
        return bool(self.api_keys.get(provider))

    async def _call_provider(
        self,
        model: LLMModel,
        prompt: str,
        system_prompt: Optional[str],
    ) -> str:
        """Call specific LLM provider"""

        if model.provider == LLMProvider.GROQ:
            return await self._call_groq(model, prompt, system_prompt)
        elif model.provider == LLMProvider.GEMINI:
            return await self._call_gemini(model, prompt, system_prompt)
        elif model.provider == LLMProvider.VERTEX:
            return await self._call_vertex(model, prompt, system_prompt)
        elif model.provider == LLMProvider.TOGETHER:
            return await self._call_together(model, prompt, system_prompt)
        elif model.provider == LLMProvider.OPENAI:
            return await self._call_openai(model, prompt, system_prompt)
        elif model.provider == LLMProvider.ANTHROPIC:
            return await self._call_anthropic(model, prompt, system_prompt)
        elif model.provider == LLMProvider.BEDROCK:
            return await self._call_bedrock(model, prompt, system_prompt)
        else:
            raise ValueError(f"Unknown provider: {model.provider}")

    async def _call_groq(
        self, model: LLMModel, prompt: str, system_prompt: Optional[str]
    ) -> str:
        """Call Groq API"""
        api_key = self.api_keys[LLMProvider.GROQ]

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model.model_id,
                    "messages": messages,
                    "max_tokens": self.max_tokens,
                    "temperature": self.temperature,
                },
            )
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]

    async def _call_gemini(
        self, model: LLMModel, prompt: str, system_prompt: Optional[str]
    ) -> str:
        """Call Google Gemini API"""
        api_key = self.api_keys[LLMProvider.GEMINI]

        # Build request payload
        payload = {
            "contents": [
                {
                    "parts": [{"text": prompt}],
                    "role": "user",
                }
            ],
            "generationConfig": {
                "temperature": self.temperature,
                "maxOutputTokens": self.max_tokens,
            },
        }

        # Add system instruction if provided
        if system_prompt:
            payload["systemInstruction"] = {
                "parts": [{"text": system_prompt}]
            }

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/{model.model_id}:generateContent?key={api_key}",
                headers={
                    "Content-Type": "application/json",
                },
                json=payload,
            )
            response.raise_for_status()
            data = response.json()
            return data["candidates"][0]["content"]["parts"][0]["text"]

    async def _call_together(
        self, model: LLMModel, prompt: str, system_prompt: Optional[str]
    ) -> str:
        """Call Together AI API"""
        api_key = self.api_keys[LLMProvider.TOGETHER]

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                "https://api.together.xyz/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model.model_id,
                    "messages": messages,
                    "max_tokens": self.max_tokens,
                    "temperature": self.temperature,
                },
            )
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]

    async def _call_openai(
        self, model: LLMModel, prompt: str, system_prompt: Optional[str]
    ) -> str:
        """Call OpenAI API"""
        api_key = self.api_keys[LLMProvider.OPENAI]

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model.model_id,
                    "messages": messages,
                    "max_tokens": self.max_tokens,
                    "temperature": self.temperature,
                },
            )
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]

    async def _call_anthropic(
        self, model: LLMModel, prompt: str, system_prompt: Optional[str]
    ) -> str:
        """Call Anthropic API"""
        api_key = self.api_keys[LLMProvider.ANTHROPIC]

        payload = {
            "model": model.model_id,
            "max_tokens": self.max_tokens,
            "messages": [{"role": "user", "content": prompt}],
        }

        if system_prompt:
            payload["system"] = system_prompt

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": api_key,
                    "anthropic-version": "2023-06-01",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
            response.raise_for_status()
            data = response.json()
            return data["content"][0]["text"]

    def _vertex_access_token(self) -> str:
        """Resolve a GCP OAuth access token for Vertex.

        Prefers an explicit short-lived VERTEX_ACCESS_TOKEN (handy for tests
        and CI). Otherwise mints one from Application Default Credentials via
        google-auth (service account in GOOGLE_APPLICATION_CREDENTIALS).
        """
        explicit = os.getenv("VERTEX_ACCESS_TOKEN")
        if explicit:
            return explicit
        try:
            import google.auth
            import google.auth.transport.requests
        except ImportError as exc:
            raise RuntimeError(
                "Vertex requires google-auth (or set VERTEX_ACCESS_TOKEN)"
            ) from exc
        credentials, _ = google.auth.default(
            scopes=["https://www.googleapis.com/auth/cloud-platform"]
        )
        credentials.refresh(google.auth.transport.requests.Request())
        return credentials.token

    async def _call_vertex(
        self, model: LLMModel, prompt: str, system_prompt: Optional[str]
    ) -> str:
        """Call Gemini via Google Vertex AI.

        Same generateContent payload as the public Gemini API, but routed
        through the regional Vertex endpoint and authorized with a GCP
        bearer token instead of an API key.
        """
        project = os.getenv("VERTEX_PROJECT") or os.getenv("GOOGLE_CLOUD_PROJECT")
        location = os.getenv("VERTEX_LOCATION", "us-central1")
        token = await asyncio.get_event_loop().run_in_executor(
            None, self._vertex_access_token
        )

        payload = {
            "contents": [{"parts": [{"text": prompt}], "role": "user"}],
            "generationConfig": {
                "temperature": self.temperature,
                "maxOutputTokens": self.max_tokens,
            },
        }
        if system_prompt:
            payload["systemInstruction"] = {"parts": [{"text": system_prompt}]}

        url = (
            f"https://{location}-aiplatform.googleapis.com/v1/projects/"
            f"{project}/locations/{location}/publishers/google/models/"
            f"{model.model_id}:generateContent"
        )

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                url,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
            response.raise_for_status()
            data = response.json()
            return data["candidates"][0]["content"]["parts"][0]["text"]

    async def _call_bedrock(
        self, model: LLMModel, prompt: str, system_prompt: Optional[str]
    ) -> str:
        """Call Claude via AWS Bedrock.

        boto3 handles SigV4 signing and credential resolution (env vars,
        profile, or instance role). The sync invoke runs in an executor so
        it doesn't block the event loop. Uses the Anthropic Messages schema
        with the Bedrock anthropic_version marker.
        """
        region = os.getenv("AWS_REGION") or os.getenv("AWS_DEFAULT_REGION", "us-east-1")

        body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "messages": [{"role": "user", "content": prompt}],
        }
        if system_prompt:
            body["system"] = system_prompt

        def _invoke() -> str:
            import boto3

            client = boto3.client("bedrock-runtime", region_name=region)
            resp = client.invoke_model(
                modelId=model.model_id,
                body=json.dumps(body),
                contentType="application/json",
                accept="application/json",
            )
            data = json.loads(resp["body"].read())
            return data["content"][0]["text"]

        return await asyncio.get_event_loop().run_in_executor(None, _invoke)

    def _fallback_response(self) -> str:
        """Fallback response when no API available"""
        return (
            "AI interpretation temporarily unavailable. "
            "Please check API configuration."
        )

    def get_available_providers(self) -> List[str]:
        """Get list of available provider names"""
        return [m.provider.value for m in self.available_models]

    def get_cheapest_provider(self) -> Optional[str]:
        """Get name of cheapest available provider"""
        if not self.available_models:
            return None
        return self.available_models[0].provider.value
