"""
Universal LLM Provider with multiple model support and automatic fallback.

Supports (in order of priority by cost):
1. Groq (free tier, very fast)
2. Together AI (cheap open-source models)
3. OpenAI GPT-4o-mini (cheaper than Claude)
4. Anthropic Claude Haiku (current)
"""

import logging
import os
from enum import Enum
from typing import Optional, Tuple, List
import httpx

logger = logging.getLogger(__name__)


class LLMProvider(str, Enum):
    """Available LLM providers"""
    GROQ = "groq"
    TOGETHER = "together"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"


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
    # Anthropic Claude Haiku - current default
    LLMModel(
        provider=LLMProvider.ANTHROPIC,
        model_id="claude-3-haiku-20240307",
        cost_per_1k_tokens=0.00025,  # $0.25 per 1M input tokens
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
            LLMProvider.TOGETHER: os.getenv("TOGETHER_API_KEY"),
            LLMProvider.OPENAI: os.getenv("OPENAI_API_KEY"),
            LLMProvider.ANTHROPIC: os.getenv("ANTHROPIC_API_KEY"),
        }

        # Get available models (only those with API keys)
        self.available_models = [
            model for model in AVAILABLE_MODELS
            if self.api_keys.get(model.provider)
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
                return result, model.provider.value
            except Exception as e:
                logger.warning(
                    f"Failed with {model.provider.value}: {str(e)}"
                )
                continue

        # All models failed - use fallback
        logger.error("All LLM providers failed - using fallback")
        return self._fallback_response(), None

    async def _call_provider(
        self,
        model: LLMModel,
        prompt: str,
        system_prompt: Optional[str],
    ) -> str:
        """Call specific LLM provider"""

        if model.provider == LLMProvider.GROQ:
            return await self._call_groq(model, prompt, system_prompt)
        elif model.provider == LLMProvider.TOGETHER:
            return await self._call_together(model, prompt, system_prompt)
        elif model.provider == LLMProvider.OPENAI:
            return await self._call_openai(model, prompt, system_prompt)
        elif model.provider == LLMProvider.ANTHROPIC:
            return await self._call_anthropic(model, prompt, system_prompt)
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
