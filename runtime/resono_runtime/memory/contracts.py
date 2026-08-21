from __future__ import annotations

from enum import Enum


REVIEWER_CONTRACT_VERSION = 2


class MemoryDomain(str, Enum):
    IDENTITY = "identity"
    PERSONAL = "personal"
    RELATIONSHIP = "relationship"
    ENVIRONMENT = "environment"
    PROJECT = "project"
    DEVICE = "device"
    PLATFORM = "platform"


class MemoryType(str, Enum):
    FACT = "fact"
    PREFERENCE = "preference"
    DECISION = "decision"
    EPISODE = "episode"
    CONSTRAINT = "constraint"
    CORRECTION = "correction"


class ReconciliationIntent(str, Enum):
    CREATE = "create"
    CONFIRM = "confirm"
    CORRECT = "correct"
    CONFLICT = "conflict"


class SourceAuthority(str, Enum):
    USER_ASSERTED = "user_asserted"
    TOOL_VERIFIED = "tool_verified"
    MODEL_DERIVED = "model_derived"

