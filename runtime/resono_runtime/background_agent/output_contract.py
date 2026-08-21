"""One typed public result returned by the Background Agent SDK run."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class RequirementOutcome(BaseModel):
    model_config = ConfigDict(extra="forbid")
    requirement: str = Field(min_length=1, max_length=2048)
    status: Literal["completed", "unresolved"]
    evidence: str = Field(min_length=1, max_length=16_384)


class PhaseEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid")
    phase: str = Field(min_length=1, max_length=120)
    summary: str = Field(min_length=1, max_length=2200)


class BackgroundAgentOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: Literal["complete", "blocked", "needs_attention"]
    summary: str = Field(min_length=1, max_length=16_384)
    artifact_references: list[str] = Field(default_factory=list, max_length=64)
    requirement_outcomes: list[RequirementOutcome] = Field(default_factory=list, max_length=40)
    unresolved_issues: list[str] = Field(default_factory=list, max_length=40)
    verification_summary: str = Field(min_length=1, max_length=16_384)
    phase_evidence: list[PhaseEvidence] = Field(default_factory=list, max_length=40)


def background_output_schema() -> dict[str, object]:
    return BackgroundAgentOutput.model_json_schema()
