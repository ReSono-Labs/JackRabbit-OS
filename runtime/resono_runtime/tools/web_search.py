from __future__ import annotations

import json

from resono_runtime.agents import AudienceResource, AudienceResourceKind
from resono_runtime.providers.openai.web_search import OpenAIWebSearch
from resono_runtime.tools.catalog import ToolCatalog
from resono_runtime.tools.definitions import ToolDefinition, ToolInvocationResult


WEB_SEARCH_TOOL_SET = AudienceResource(AudienceResourceKind.DOMAIN_TOOL_SET, "web-search")


def register_web_search(catalog: ToolCatalog, search: OpenAIWebSearch) -> None:
    def invoke(arguments: dict[str, object]) -> ToolInvocationResult:
        query = arguments.get("query")
        if not isinstance(query, str):
            return ToolInvocationResult("Web search query is required.", is_error=True)
        try:
            result = search.search(query)
        except (ValueError, RuntimeError) as error:
            return ToolInvocationResult(str(error), is_error=True)
        return ToolInvocationResult(json.dumps(result, separators=(",", ":")), structured_content=result)

    catalog.register(
        ToolDefinition(
            tool_id="builtin.web-search.v1",
            name="web_search",
            description="Search current public web sources and return a concise citation-backed answer.",
            input_schema={"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"], "additionalProperties": False},
            handler=invoke,
            effect_class="read",
            audience_resource=WEB_SEARCH_TOOL_SET,
            available_to=lambda _: search.available(),
        )
    )
