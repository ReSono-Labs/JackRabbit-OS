import io
import json
import logging
from types import SimpleNamespace

import httpx
import openai
import pytest

from resono_runtime.core.logging import _FORMAT, runtime_logger
from resono_runtime.providers.openai import web_search
from resono_runtime.providers.openai.access import SUBSCRIPTION_BASE_URL
from resono_runtime.providers.openai.platform import OpenAIProviderError


PRIVATE_QUERY = "private-query-marker"
PRIVATE_RESULT = "private-result-and-token-marker"


@pytest.fixture
def diagnostic_log():
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    # Exercise the formatter used by the real runtime, not pytest's extra fields.
    handler.setFormatter(logging.Formatter(_FORMAT))
    logger = runtime_logger()
    logger.addHandler(handler)
    try:
        yield stream
    finally:
        logger.removeHandler(handler)


@pytest.fixture
def sdk_search(monkeypatch):
    """Keep the resolver and pinned SDK real; replace only outbound HTTP."""
    real_client = openai.AsyncOpenAI

    def configure(handler, *, subscription=False):
        requests = []
        credential_reads = []

        def respond(request):
            requests.append(request)
            return handler(request)

        monkeypatch.setattr(
            openai, "DefaultAsyncHttpxClient",
            lambda: httpx.AsyncClient(transport=httpx.MockTransport(respond)),
        )
        monkeypatch.setattr(
            openai, "AsyncOpenAI",
            lambda **kwargs: real_client(max_retries=0, **kwargs),
        )

        def credential(kind):
            credential_reads.append(kind)
            return "test-only-credential"

        search = web_search.OpenAIWebSearch(
            SimpleNamespace(platform_key=lambda: credential("platform")),
            SimpleNamespace(selection=lambda: SimpleNamespace(
                access_path="subscription" if subscription else "platform")),
            SimpleNamespace(access_token=lambda: credential("subscription")),
        )
        return search, requests, credential_reads

    return configure


def response_payload(*, answer=PRIVATE_RESULT, citations=True):
    annotations = [{
        "type": "url_citation", "start_index": 0, "end_index": 1,
        "title": "Test source", "url": "https://example.com/source",
    }] if citations else []
    return {
        "id": "resp_test", "object": "response", "created_at": 1,
        "status": "completed", "model": "gpt-5.6-terra",
        "error": None, "incomplete_details": None, "instructions": None,
        "metadata": {}, "parallel_tool_calls": True, "tool_choice": "auto",
        "tools": [{"type": "web_search"}], "temperature": 1, "top_p": 1,
        "output": [{
            "id": "msg_test", "type": "message", "role": "assistant",
            "status": "completed", "content": [{
                "type": "output_text", "text": answer, "annotations": annotations,
            }],
        }],
    }


def streamed(payload, event_type="response.completed"):
    event = {"type": event_type, "sequence_number": 0, "response": payload}
    return httpx.Response(200, headers={"content-type": "text/event-stream"},
                          content="data: " + json.dumps(event) + "\n\n")


def assert_safe_failure(stream, *, phase, reason, exception, status="none"):
    rendered = stream.getvalue()
    assert (f"web_search.failed phase={phase} reason={reason} "
            f"exception={exception} http_status={status}") in rendered
    assert PRIVATE_QUERY not in rendered
    assert PRIVATE_RESULT not in rendered
    assert "test-only-credential" not in rendered
    assert "Traceback" not in rendered


def test_http_failure_reports_status_without_provider_body(sdk_search, diagnostic_log):
    search, _, _ = sdk_search(lambda _request: httpx.Response(
        429, json={"error": {"message": PRIVATE_RESULT, "type": "rate_limit_error"}},
    ))
    with pytest.raises(RuntimeError, match=r"^OpenAI web search was rejected \(HTTP 429\)\.$"):
        search.search(PRIVATE_QUERY)
    assert_safe_failure(diagnostic_log, phase="execute", reason="http_error",
                        exception="RateLimitError", status="429")


@pytest.mark.parametrize("code,param,expected_code,expected_param", [
    ("unsupported_parameter", "tools[0].search_context_size", "unsupported_parameter", "tools[0].search_context_size"),
    ("model_not_found", "model", "model_not_found", "model"),
    (PRIVATE_RESULT, PRIVATE_QUERY, "other", "other"),
    ({"message": PRIVATE_RESULT}, [PRIVATE_QUERY], "other", "other"),
    (None, None, "none", "none"),
])
def test_http_error_fields_are_strict_whitelists(
    sdk_search, diagnostic_log, code, param, expected_code, expected_param,
):
    search, _, _ = sdk_search(lambda _request: httpx.Response(400, json={"error": {
        "message": PRIVATE_RESULT, "code": code, "param": param,
    }}))
    with pytest.raises(RuntimeError, match=r"^OpenAI web search was rejected \(HTTP 400\)\.$"):
        search.search(PRIVATE_QUERY)
    assert_safe_failure(diagnostic_log, phase="execute", reason="http_error",
                        exception="BadRequestError", status="400")
    assert (f"error_code={expected_code} error_param={expected_param}") in diagnostic_log.getvalue()


def test_stream_failure_reports_sdk_type_without_response_body(sdk_search, diagnostic_log):
    payload = response_payload()
    payload.update(status="failed", error={"code": "server_error", "message": PRIVATE_RESULT})
    search, _, _ = sdk_search(lambda _request: streamed(payload, "response.failed"), subscription=True)
    with pytest.raises(RuntimeError, match=r"^OpenAI web search was rejected\.$"):
        search.search(PRIVATE_QUERY)
    assert_safe_failure(diagnostic_log, phase="execute", reason="sdk_error",
                        exception="ModelBehaviorError")


@pytest.mark.parametrize("answer,citations,reason,message", [
    ("", True, "missing_answer", "OpenAI web search returned no answer."),
    (PRIVATE_RESULT, False, "missing_citations", "OpenAI web search returned no citations."),
])
def test_incomplete_results_have_distinct_safe_reasons(
    sdk_search, diagnostic_log, answer, citations, reason, message,
):
    search, _, _ = sdk_search(lambda _request: httpx.Response(
        200, json=response_payload(answer=answer, citations=citations),
    ))
    with pytest.raises(RuntimeError) as caught:
        search.search(PRIVATE_QUERY)
    assert str(caught.value) == message
    assert_safe_failure(diagnostic_log, phase="validate", reason=reason,
                        exception="SearchResultError")
    if reason == "missing_citations":
        assert ("web_search.citation_shape responses=1 outputs=1 messages=1 web_search=0 "
                "completed_search=0 annotations=0 urls=0 stream_annotation_urls=0 "
                "stream_item_urls=0 action_search=0 action_open_page=0 "
                "action_find_in_page=0 action_other=0 sources=0") in diagnostic_log.getvalue()
    else:
        assert "web_search.citation_shape" not in diagnostic_log.getvalue()


def test_stream_counters_expose_metadata_missing_from_terminal(sdk_search, diagnostic_log):
    cited_item = response_payload()["output"][0]
    search_item = {
        "id": "ws_test", "type": "web_search_call", "status": "completed",
        "action": {"type": "search", "query": PRIVATE_QUERY, "sources": [
            {"type": "url", "url": "https://example.com/stream-source"},
        ]},
    }
    terminal = response_payload(citations=False)
    terminal["output"].insert(0, search_item)
    events = [
        {"type": "response.output_text.annotation.added", "sequence_number": 0,
         "item_id": "msg_test", "output_index": 1, "content_index": 0,
         "annotation_index": 0, "annotation": cited_item["content"][0]["annotations"][0]},
        {"type": "response.output_item.done", "sequence_number": 1,
         "output_index": 1, "item": cited_item},
        {"type": "response.completed", "sequence_number": 2, "response": terminal},
    ]
    stream = "".join("data: " + json.dumps(event) + "\n\n" for event in events)
    search, _, _ = sdk_search(lambda _request: httpx.Response(
        200, headers={"content-type": "text/event-stream"}, content=stream,
    ), subscription=True)
    with pytest.raises(RuntimeError) as caught:
        search.search(PRIVATE_QUERY)
    assert str(caught.value) == "OpenAI web search returned no citations."
    assert_safe_failure(diagnostic_log, phase="validate", reason="missing_citations",
                        exception="SearchResultError")
    assert ("web_search.citation_shape responses=1 outputs=2 messages=1 web_search=1 "
            "completed_search=1 annotations=0 urls=0 stream_annotation_urls=1 "
            "stream_item_urls=1 action_search=1 action_open_page=0 "
            "action_find_in_page=0 action_other=0 sources=1") in diagnostic_log.getvalue()
    assert "https://example.com/stream-source" not in diagnostic_log.getvalue()


def test_search_feed_sources_are_counted_but_not_reclassified_as_citations(sdk_search, diagnostic_log):
    payload = response_payload(citations=False)
    payload["output"].insert(0, {
        "id": "ws_feed", "type": "web_search_call", "status": "completed",
        "action": {"type": "search", "query": PRIVATE_QUERY,
                   "sources": [{"type": "url", "url": "oai-weather"}]},
    })
    search, _, _ = sdk_search(lambda _request: streamed(payload), subscription=True)
    with pytest.raises(RuntimeError) as caught:
        search.search(PRIVATE_QUERY)
    assert str(caught.value) == "OpenAI web search returned no citations."
    assert ("web_search.citation_shape responses=1 outputs=2 messages=1 web_search=1 "
            "completed_search=1 annotations=0 urls=0 stream_annotation_urls=0 "
            "stream_item_urls=0 action_search=1 action_open_page=0 "
            "action_find_in_page=0 action_other=0 sources=1") in diagnostic_log.getvalue()
    assert "oai-weather" not in diagnostic_log.getvalue()


def test_access_failure_is_logged_and_preserves_original_error(monkeypatch, diagnostic_log):
    error = OpenAIProviderError("subscription_reconnect_required", "Reconnect ChatGPT.", status=409)

    def reject_access(**_kwargs):
        raise error

    monkeypatch.setattr(web_search, "openai_provider_access", reject_access)
    with pytest.raises(OpenAIProviderError) as caught:
        web_search.OpenAIWebSearch(None, None, None).search(PRIVATE_QUERY)
    assert caught.value is error
    assert_safe_failure(diagnostic_log, phase="access", reason="access_error",
                        exception="OpenAIProviderError")


@pytest.mark.parametrize("error,reason,exception", [
    (httpx.ConnectTimeout(PRIVATE_RESULT), "timeout", "APITimeoutError"),
    (httpx.ConnectError(PRIVATE_RESULT), "connection_error", "APIConnectionError"),
])
def test_transport_failure_has_safe_category(sdk_search, diagnostic_log, error, reason, exception):
    def fail(_request):
        raise error

    search, _, _ = sdk_search(fail)
    with pytest.raises(RuntimeError, match=r"^OpenAI web search was rejected\.$"):
        search.search(PRIVATE_QUERY)
    assert_safe_failure(diagnostic_log, phase="execute", reason=reason, exception=exception)


def test_unknown_exception_never_logs_dynamic_name_or_message(monkeypatch, diagnostic_log):
    custom_error = type(PRIVATE_RESULT, (RuntimeError,), {"status_code": PRIVATE_RESULT})

    async def fail(**_kwargs):
        raise custom_error(PRIVATE_RESULT)

    monkeypatch.setattr(web_search, "_run_search", fail)
    search = web_search.OpenAIWebSearch(
        SimpleNamespace(platform_key=lambda: "test-only-credential"),
        SimpleNamespace(selection=lambda: SimpleNamespace(access_path="platform")), None,
    )
    with pytest.raises(RuntimeError, match=r"^OpenAI web search was rejected\.$"):
        search.search(PRIVATE_QUERY)
    assert_safe_failure(diagnostic_log, phase="execute", reason="unexpected_error", exception="other")


@pytest.mark.parametrize("subscription", [False, True])
def test_success_keeps_canonical_access_transport_and_result(sdk_search, diagnostic_log, subscription):
    payload = response_payload()
    search, requests, credential_reads = sdk_search(
        lambda _request: streamed(payload) if subscription else httpx.Response(200, json=payload),
        subscription=subscription,
    )
    result = search.search(PRIVATE_QUERY)
    assert result == {
        "query": PRIVATE_QUERY, "answer": PRIVATE_RESULT,
        "citations": [{"title": "Test source", "url": "https://example.com/source"}],
        "responseId": "resp_test",
    }
    assert credential_reads == ["subscription" if subscription else "platform"]
    assert len(requests) == 1
    assert str(requests[0].url) == (
        SUBSCRIPTION_BASE_URL if subscription else "https://api.openai.com/v1"
    ) + "/responses"
    body = json.loads(requests[0].content)
    assert body["model"] == "gpt-5.6-terra"
    assert body["tools"][0]["type"] == "web_search"
    assert body.get("stream", False) is subscription
    if subscription:
        assert body["store"] is False
    assert diagnostic_log.getvalue() == ""
