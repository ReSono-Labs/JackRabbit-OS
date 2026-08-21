"""Builds bounded immutable context from canonical runtime owners."""

from __future__ import annotations

from ..memory.session_context import SessionContextBuilder
from ..skills.activation import SkillActivation
from ..tools.catalog import ToolCatalog
from .audience import AgentKind
from .primary_context import ExecutionKind, PrimaryAgentContext, WorkspaceGrant


class PrimaryContextBuilder:
    def __init__(self, *, tools: ToolCatalog, skills: SkillActivation,
                 memory: SessionContextBuilder, background_instructions=lambda: "") -> None:
        self._tools = tools
        self._skills = skills
        self._memory = memory
        self._background_instructions = background_instructions

    def background_goal(self, *, run_id: str, origin_id: str,
                        instruction_profile: str) -> PrimaryAgentContext:
        definitions = self._tools.definitions_for(AgentKind.TEXT)
        memory = self._memory.build(current_session_id=origin_id)
        sections = []
        rendered_memory = memory.render()
        if rendered_memory:
            sections.append(rendered_memory)
        managed_instructions = self._background_instructions()
        if managed_instructions: sections.append(managed_instructions)
        return PrimaryAgentContext(
            context_version=1, execution_id=run_id,
            execution_kind=ExecutionKind.BACKGROUND_GOAL,
            origin_id=origin_id, instruction_profile=instruction_profile,
            tool_ids=tuple(item.tool_id for item in definitions),
            skill_ids=("background/SKILLS.MD",) if managed_instructions else (),
            memory_references=tuple(item.memory_id for item in memory.memories),
            workspace_grants=(WorkspaceGrant(f"run://{run_id}/work", "read_write"),
                              WorkspaceGrant("workspace://", "read_publish")),
            rendered_context="\n\n".join(sections),
        )
