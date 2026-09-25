from unittest.mock import MagicMock

import pytest
from langchain_core.language_models.fake_chat_models import FakeListChatModel

from observatory.service import (
    ABSTENTION,
    PortfolioAssistant,
    Settings,
    load_projects,
    validate_citations,
)


def test_over_budget_sources_and_arithmetic():
    result = PortfolioAssistant(Settings()).ask("Which projects are over budget?")
    assert {p["id"] for p in result["sources"]} == {"PRJ-101", "PRJ-103"}
    cedar = next(p for p in result["sources"] if p["id"] == "PRJ-103")
    assert cedar["forecast_variance"] == 36000
    assert cedar["forecast_variance_pct"] == 22.5
    assert "actual expenditure" not in result["answer"]


@pytest.mark.parametrize("question", ["Weather tomorrow?", "Explain PRJ-999"])
def test_unknown_evidence_skips_model(question):
    model = FakeListChatModel(responses=["SHOULD NOT RUN"])
    assistant = PortfolioAssistant(Settings(mode="live"), model=model)
    assistant.generation = MagicMock()
    result = assistant.ask(question)
    assistant.generation.invoke.assert_not_called()
    assert result["answer"] == ABSTENTION
    assert result["sources"] == []


@pytest.mark.parametrize("answer", ["No citations", "Invented [PRJ-999]", "Mixed [PRJ-103] [PRJ-999]"])
def test_rejects_missing_and_unknown_citations(answer):
    assert validate_citations(answer, load_projects()) == (ABSTENTION, [], False)


def test_live_prompt_path_with_fake_model():
    model = FakeListChatModel(responses=["Cedar Claims has integration risks [PRJ-103]."])
    result = PortfolioAssistant(Settings(mode="live"), model=model).ask("Cedar Claims risks")
    assert result["citation_check_passed"]
    assert [p["id"] for p in result["sources"]] == ["PRJ-103"]
    assert result["mode"] == "live"


def test_live_rejects_citation_to_unretrieved_record():
    model = FakeListChatModel(responses=["Atlas is over budget [PRJ-101]."])
    result = PortfolioAssistant(Settings(mode="live"), model=model).ask("Cedar Claims risks")
    assert result["answer"] == ABSTENTION


def test_named_project_with_no_overrun():
    result = PortfolioAssistant(Settings()).ask("Is Beacon Analytics over budget?")
    assert "None of the selected projects" in result["answer"]
    assert [p["id"] for p in result["sources"]] == ["PRJ-102"]


@pytest.mark.parametrize("question", ["", "  ", "x" * 2001])
def test_question_limits(question):
    with pytest.raises(ValueError):
        PortfolioAssistant(Settings()).ask(question)


def test_live_configuration_requires_key(monkeypatch):
    monkeypatch.setenv("APP_MODE", "live")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(ValueError, match="Live mode requires"):
        Settings.from_env()


def test_trace_configuration_requires_keys(monkeypatch):
    monkeypatch.setenv("APP_MODE", "demo")
    monkeypatch.setenv("ENABLE_TRACING", "true")
    monkeypatch.delenv("LANGFUSE_SECRET_KEY", raising=False)
    with pytest.raises(ValueError, match="Tracing requires"):
        Settings.from_env()


def test_disabled_tracing_never_initializes_client(monkeypatch):
    import langfuse
    client_factory = MagicMock(side_effect=AssertionError("Unexpected telemetry"))
    monkeypatch.setattr(langfuse, "get_client", client_factory)
    PortfolioAssistant(Settings(tracing=False)).ask("Portfolio risks")
    client_factory.assert_not_called()


def test_langfuse_callback_score_and_flush_contract(monkeypatch):
    import langfuse
    import langfuse.langchain
    from langchain_core.callbacks import BaseCallbackHandler

    class RecordingHandler(BaseCallbackHandler):
        last_trace_id = "a" * 32

        def __init__(self):
            self.started = 0

        def on_chain_start(self, *args, **kwargs):
            self.started += 1

    handler = RecordingHandler()
    client = MagicMock()
    monkeypatch.setattr(langfuse, "get_client", lambda: client)
    monkeypatch.setattr(langfuse.langchain, "CallbackHandler", lambda: handler)
    assistant = PortfolioAssistant(Settings(tracing=True))
    result = assistant.ask("Cedar Claims risks")
    assert handler.started >= 3
    assert result["trace_id"] == "a" * 32
    assert client.create_score.call_args.kwargs["name"] == "citation_id_validity"
    assert client.create_score.call_args.kwargs["value"] == 1.0
    assistant.close()
    client.flush.assert_called_once()
