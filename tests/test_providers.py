from __future__ import annotations

import os

import pytest
from dataclasses import FrozenInstanceError

from coachbench.providers import FakeProvider, ProviderResponse, make_provider
from coachbench.providers.anthropic_provider import AnthropicProvider


@pytest.fixture
def scrub_anthropic_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)


def test_provider_response_is_frozen_dataclass() -> None:
    response = ProviderResponse(raw_text="{}", parsed_json={})
    with pytest.raises(FrozenInstanceError):
        response.raw_text = "changed"


def test_fake_provider_returns_canned_in_sequence() -> None:
    provider = FakeProvider(canned_responses=[
        ProviderResponse(raw_text='{"a": 1}', parsed_json={"a": 1}),
        ProviderResponse(raw_text='{"b": 2}', parsed_json={"b": 2}),
    ])
    assert provider.query(system="", user="").parsed_json == {"a": 1}
    assert provider.query(system="", user="").parsed_json == {"b": 2}


def test_fake_provider_returns_default_after_canned_exhausted() -> None:
    provider = FakeProvider(
        canned_responses=[ProviderResponse(raw_text='{"a": 1}', parsed_json={"a": 1})],
        default_payload={"fallback": True},
    )
    provider.query(system="", user="")
    response = provider.query(system="", user="")
    assert response.raw_text == '{"fallback": true}'
    assert response.parsed_json == {"fallback": True}


def test_fake_provider_returns_error_when_no_canned_and_no_default() -> None:
    response = FakeProvider().query(system="", user="")
    assert response.parsed_json is None
    assert response.error == "fake provider exhausted"


def test_fake_provider_requires_network_false_class_and_instance() -> None:
    assert FakeProvider.requires_network is False
    assert FakeProvider().requires_network is False


def test_make_provider_fake() -> None:
    assert isinstance(make_provider("fake"), FakeProvider)


def test_make_provider_unknown_raises_value_error() -> None:
    with pytest.raises(ValueError, match="unknown provider"):
        make_provider("unknown")


def test_anthropic_provider_class_requires_network_true() -> None:
    assert AnthropicProvider.requires_network is True


def test_anthropic_provider_init_requires_api_key(scrub_anthropic_key: None) -> None:
    with pytest.raises(RuntimeError, match="requires ANTHROPIC_API_KEY"):
        AnthropicProvider(api_key=None)


def test_anthropic_provider_parse_json_recovers_from_markdown_fence() -> None:
    assert AnthropicProvider._parse_json('```json\n{"concept_family": "x"}\n```') == {"concept_family": "x"}


def test_anthropic_provider_parse_json_recovers_from_prose_wrapping() -> None:
    assert AnthropicProvider._parse_json('Here is the pick: {"coverage_family": "x"} done.') == {"coverage_family": "x"}


def test_anthropic_provider_parse_json_returns_none_on_invalid() -> None:
    assert AnthropicProvider._parse_json("not json at all") is None


@pytest.mark.skipif(
    not os.environ.get("ANTHROPIC_API_KEY") or not os.environ.get("COACHBENCH_LIVE_ANTHROPIC_TEST"),
    reason="live anthropic disabled",
)
def test_anthropic_provider_live_query() -> None:
    pytest.importorskip("anthropic")
    provider = AnthropicProvider(max_tokens=64)
    response = provider.query(
        system='Respond only with {"concept_family": "inside_zone"}',
        user="Return the requested JSON.",
    )
    assert response.error is None
