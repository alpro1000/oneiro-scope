"""Tests for Vertex AI and Bedrock LLM providers.

These exercise gating logic and request construction without hitting the
real cloud APIs (httpx and boto3 are mocked).
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.core.llm_provider import (
    AVAILABLE_MODELS,
    LLMProvider,
    UniversalLLMProvider,
)


def test_vertex_and_bedrock_in_catalog():
    providers = {m.provider for m in AVAILABLE_MODELS}
    assert LLMProvider.VERTEX in providers
    assert LLMProvider.BEDROCK in providers


def test_vertex_disabled_without_config(monkeypatch):
    for var in (
        "VERTEX_PROJECT",
        "GOOGLE_CLOUD_PROJECT",
        "VERTEX_ACCESS_TOKEN",
        "GOOGLE_APPLICATION_CREDENTIALS",
    ):
        monkeypatch.delenv(var, raising=False)
    p = UniversalLLMProvider()
    assert not p._provider_configured(LLMProvider.VERTEX)


def test_vertex_enabled_with_project_and_token(monkeypatch):
    monkeypatch.setenv("VERTEX_PROJECT", "demo-project")
    monkeypatch.setenv("VERTEX_ACCESS_TOKEN", "ya29.fake")
    p = UniversalLLMProvider()
    assert p._provider_configured(LLMProvider.VERTEX)
    assert "vertex" in p.get_available_providers()


def test_vertex_needs_both_project_and_creds(monkeypatch):
    monkeypatch.setenv("VERTEX_PROJECT", "demo-project")
    monkeypatch.delenv("VERTEX_ACCESS_TOKEN", raising=False)
    monkeypatch.delenv("GOOGLE_APPLICATION_CREDENTIALS", raising=False)
    p = UniversalLLMProvider()
    assert not p._provider_configured(LLMProvider.VERTEX)


def test_bedrock_disabled_without_aws_creds(monkeypatch):
    for var in ("AWS_ACCESS_KEY_ID", "AWS_PROFILE"):
        monkeypatch.delenv(var, raising=False)
    p = UniversalLLMProvider()
    assert not p._provider_configured(LLMProvider.BEDROCK)


def test_bedrock_requires_boto3(monkeypatch):
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "AKIAFAKE")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "secret")
    p = UniversalLLMProvider()
    # Gating reflects whether boto3 is importable in this environment.
    try:
        import boto3  # noqa: F401

        expected = True
    except ImportError:
        expected = False
    assert p._provider_configured(LLMProvider.BEDROCK) is expected


@pytest.mark.asyncio
async def test_call_vertex_builds_regional_url_and_parses(monkeypatch):
    monkeypatch.setenv("VERTEX_PROJECT", "demo-project")
    monkeypatch.setenv("VERTEX_LOCATION", "europe-west1")
    monkeypatch.setenv("VERTEX_ACCESS_TOKEN", "ya29.fake")
    monkeypatch.setenv("VERTEX_MODEL_ID", "gemini-1.5-flash-002")

    captured = {}

    class _Resp:
        def raise_for_status(self):
            pass

        def json(self):
            return {
                "candidates": [
                    {"content": {"parts": [{"text": "vertex says hello"}]}}
                ]
            }

    class _Client:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        async def post(self, url, headers=None, json=None):
            captured["url"] = url
            captured["headers"] = headers
            captured["payload"] = json
            return _Resp()

    provider = UniversalLLMProvider()
    # Pick the vertex model from the catalog.
    vertex_model = next(m for m in AVAILABLE_MODELS if m.provider == LLMProvider.VERTEX)

    with patch("backend.core.llm_provider.httpx.AsyncClient", return_value=_Client()):
        out = await provider._call_vertex(vertex_model, "hi", "be nice")

    assert out == "vertex says hello"
    assert "europe-west1-aiplatform.googleapis.com" in captured["url"]
    assert "projects/demo-project/locations/europe-west1" in captured["url"]
    assert captured["headers"]["Authorization"] == "Bearer ya29.fake"
    assert captured["payload"]["systemInstruction"]["parts"][0]["text"] == "be nice"


@pytest.mark.asyncio
async def test_call_bedrock_invokes_model_and_parses(monkeypatch):
    monkeypatch.setenv("AWS_REGION", "eu-central-1")
    monkeypatch.setenv("BEDROCK_MODEL_ID", "anthropic.claude-3-haiku-20240307-v1:0")

    captured = {}

    fake_body = MagicMock()
    fake_body.read.return_value = json.dumps(
        {"content": [{"text": "bedrock says hi"}]}
    ).encode()

    fake_client = MagicMock()

    def _invoke_model(**kwargs):
        captured.update(kwargs)
        return {"body": fake_body}

    fake_client.invoke_model.side_effect = _invoke_model

    fake_boto3 = MagicMock()
    fake_boto3.client.return_value = fake_client

    provider = UniversalLLMProvider()
    bedrock_model = next(
        m for m in AVAILABLE_MODELS if m.provider == LLMProvider.BEDROCK
    )

    with patch.dict("sys.modules", {"boto3": fake_boto3}):
        out = await provider._call_bedrock(bedrock_model, "hi", "be terse")

    assert out == "bedrock says hi"
    assert captured["modelId"] == "anthropic.claude-3-haiku-20240307-v1:0"
    body = json.loads(captured["body"])
    assert body["anthropic_version"] == "bedrock-2023-05-31"
    assert body["system"] == "be terse"
    assert body["messages"][0]["content"] == "hi"
    fake_boto3.client.assert_called_once_with(
        "bedrock-runtime", region_name="eu-central-1"
    )
