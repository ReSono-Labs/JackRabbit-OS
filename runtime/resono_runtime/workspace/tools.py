"""Canonical workspace tools with separate Voice-read and Background-write grants."""

from __future__ import annotations

import json

from ..agents.audience import AgentKind, AudienceResource, AudienceResourceKind
from ..background_agent.workspace import RunWorkspaceRegistry
from ..tools.catalog import ToolCatalog
from ..tools.definitions import ToolDefinition, ToolInvocationContext, ToolInvocationResult
from .service import DurableWorkspace


WORKSPACE_TOOL_SET = AudienceResource(AudienceResourceKind.DOMAIN_TOOL_SET, "workspace")


def register_workspace_tools(catalog: ToolCatalog, durable: DurableWorkspace,
                             runs: RunWorkspaceRegistry) -> None:
    catalog.register(ToolDefinition(
        tool_id="builtin.workspace-list.v1", name="workspace_list",
        description="List files published in the durable ReSono workspace.",
        input_schema={"type":"object","properties":{"directory":{"type":"string","enum":["inbox","documents","projects","generated","downloads","scratch"]}},"additionalProperties":False},
        handler=lambda args: _list(durable, args), audience_resource=WORKSPACE_TOOL_SET,
    ))
    catalog.register(ToolDefinition(
        tool_id="builtin.workspace-read.v1", name="workspace_read",
        description="Read one text file from a workspace:// reference.",
        input_schema={"type":"object","properties":{"reference":{"type":"string","pattern":"^workspace://"}},"required":["reference"],"additionalProperties":False},
        handler=lambda args: _read(durable, args), audience_resource=WORKSPACE_TOOL_SET,
    ))
    catalog.register(ToolDefinition(
        tool_id="builtin.run-workspace-list.v1", name="run_workspace_list",
        description="List working files for a background run. Voice must provide the run ID; the background agent uses its own run.",
        input_schema=_run_ref_schema(require_ref=False),
        handler=lambda _: ToolInvocationResult("An agent context is required.", is_error=True),
        context_handler=lambda context, args: _run_list(runs, context, args),
        audience_resource=WORKSPACE_TOOL_SET,
    ))
    catalog.register(ToolDefinition(
        tool_id="builtin.run-workspace-read.v1", name="run_workspace_read",
        description="Read one UTF-8 working file from a background run.",
        input_schema=_run_ref_schema(require_ref=True),
        handler=lambda _: ToolInvocationResult("An agent context is required.", is_error=True),
        context_handler=lambda context, args: _run_read(runs, context, args),
        audience_resource=WORKSPACE_TOOL_SET,
    ))
    catalog.register(ToolDefinition(
        tool_id="builtin.run-workspace-write.v1", name="run_workspace_write",
        description="Write one UTF-8 file inside this background run's work/ directory.",
        input_schema={"type":"object","properties":{"reference":{"type":"string","pattern":"^work/"},"content":{"type":"string"}},"required":["reference","content"],"additionalProperties":False},
        handler=lambda _: ToolInvocationResult("A background run is required.", is_error=True),
        context_handler=lambda context, args: _run_write(runs, context, args),
        effect_class="local_write", audience_resource=WORKSPACE_TOOL_SET,
        available_to=lambda agent: agent is AgentKind.TEXT,
    ))
    catalog.register(ToolDefinition(
        tool_id="builtin.workspace-publish.v1", name="workspace_publish",
        description="Publish one completed file from this run into a new durable workspace:// destination. Existing files are never overwritten.",
        input_schema={"type":"object","properties":{"source":{"type":"string","pattern":"^work/"},"destination":{"type":"string","pattern":"^workspace://"},"mediaType":{"type":"string"},"artifactRole":{"type":"string"}},"required":["source","destination","mediaType","artifactRole"],"additionalProperties":False},
        handler=lambda _: ToolInvocationResult("A background run is required.", is_error=True),
        context_handler=lambda context, args: _publish(durable, runs, context, args),
        effect_class="local_write", audience_resource=WORKSPACE_TOOL_SET,
        available_to=lambda agent: agent is AgentKind.TEXT,
    ))


def _list(workspace: DurableWorkspace, args: dict[str, object]) -> ToolInvocationResult:
    entries = workspace.list(directory=str(args["directory"]) if args.get("directory") else None)
    data = [{"reference": item.reference, "name": item.display_name, "mediaType": item.media_type,
             "bytes": item.byte_size, "originRunId": item.origin_run_id} for item in entries]
    return ToolInvocationResult(json.dumps(data, separators=(",", ":")), {"entries": data})


def _read(workspace: DurableWorkspace, args: dict[str, object]) -> ToolInvocationResult:
    try:
        text = workspace.read(str(args["reference"])).decode("utf-8")
    except Exception as error:
        return ToolInvocationResult(str(error), is_error=True)
    return ToolInvocationResult(text, {"reference": str(args["reference"]), "text": text})


def _run_id(context: ToolInvocationContext, args: dict[str, object]) -> str:
    if context.agent is AgentKind.TEXT and context.execution_id:
        return context.execution_id
    if context.agent is AgentKind.VOICE and context.voice_session_id and args.get("runId"):
        return str(args["runId"])
    raise PermissionError("A valid run context is required")


def _run_list(runs: RunWorkspaceRegistry, context: ToolInvocationContext, args: dict[str, object]) -> ToolInvocationResult:
    try:
        run_id = _run_id(context, args)
        files = list(runs.get(run_id).list_files())
    except Exception as error:
        return ToolInvocationResult(str(error), is_error=True)
    return ToolInvocationResult(json.dumps(files), {"runId": run_id, "files": files})


def _run_read(runs: RunWorkspaceRegistry, context: ToolInvocationContext, args: dict[str, object]) -> ToolInvocationResult:
    try:
        run_id = _run_id(context, args)
        text = runs.get(run_id).read_text(str(args["reference"]))
    except Exception as error:
        return ToolInvocationResult(str(error), is_error=True)
    return ToolInvocationResult(text, {"runId": run_id, "reference": str(args["reference"]), "text": text})


def _run_write(runs: RunWorkspaceRegistry, context: ToolInvocationContext, args: dict[str, object]) -> ToolInvocationResult:
    try:
        run_id = _run_id(context, args)
        runs.get(run_id).write_text(str(args["reference"]), str(args["content"]))
    except Exception as error:
        return ToolInvocationResult(str(error), is_error=True)
    return ToolInvocationResult("Run workspace file written.", {"runId": run_id, "reference": str(args["reference"])})


def _publish(durable: DurableWorkspace, runs: RunWorkspaceRegistry, context: ToolInvocationContext, args: dict[str, object]) -> ToolInvocationResult:
    try:
        run_id = _run_id(context, args)
        source = runs.get(run_id).path_for_publication(str(args["source"]))
        entry = durable.publish(source, str(args["destination"]), media_type=str(args["mediaType"]),
                                origin_run_id=run_id, artifact_role=str(args["artifactRole"]))
    except Exception as error:
        return ToolInvocationResult(str(error), is_error=True)
    return ToolInvocationResult("Artifact published.", {"reference": entry.reference, "contentHash": entry.content_hash})


def _run_ref_schema(*, require_ref: bool) -> dict[str, object]:
    properties = {"runId":{"type":"string","minLength":1},"reference":{"type":"string","pattern":"^work/"}}
    required = ["reference"] if require_ref else []
    return {"type":"object","properties":properties,"required":required,"additionalProperties":False}
