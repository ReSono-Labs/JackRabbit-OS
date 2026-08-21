"""Two-slot R1 agent instruction documents with atomic replacement."""
from __future__ import annotations
from dataclasses import dataclass
import hashlib, os, secrets, tempfile
from pathlib import Path

CANONICAL_FILENAME = "SKILLS.MD"
MAX_DOCUMENT_BYTES = 256 * 1024
DESTINATIONS = frozenset({"voice", "text"})

class AgentInstructionsError(ValueError): pass

@dataclass(frozen=True, slots=True)
class InstructionDocument:
    destination: str; path: Path; content_hash: str; byte_size: int

@dataclass(frozen=True, slots=True)
class InstructionPreflight:
    token: str; state: str; destination: str; content_hash: str; byte_size: int

class AgentInstructionDocuments:
    """Owns one Voice and one Background Agent SKILLS.MD document."""
    def __init__(self, *, voice_path: Path, background_path: Path, background_workspace: object) -> None:
        self._paths = {"voice": voice_path, "text": background_path}
        self._background_workspace = background_workspace
        self._pending: dict[str, tuple[str, bytes, str]] = {}

    def preflight(self, payload: bytes, *, filename: str, destination: str) -> InstructionPreflight:
        if filename != CANONICAL_FILENAME: raise AgentInstructionsError("The file must be named exactly SKILLS.MD.")
        if destination not in DESTINATIONS: raise AgentInstructionsError("Choose either Voice or Background Agent.")
        if not payload: raise AgentInstructionsError("SKILLS.MD cannot be empty.")
        if len(payload) > MAX_DOCUMENT_BYTES: raise AgentInstructionsError("SKILLS.MD exceeds the 256 KB limit.")
        try: text = payload.decode("utf-8")
        except UnicodeDecodeError as error: raise AgentInstructionsError("SKILLS.MD must be UTF-8 text.") from error
        normalized = text.replace("\r\n", "\n").replace("\r", "\n").encode("utf-8")
        if not normalized.strip(): raise AgentInstructionsError("SKILLS.MD must contain instructions.")
        digest, token = hashlib.sha256(normalized).hexdigest(), secrets.token_urlsafe(32)
        self._pending[token] = (destination, normalized, digest)
        return InstructionPreflight(token, "conflict" if self._paths[destination].is_file() else "new", destination, digest, len(normalized))

    def confirm(self, token: str, *, replace: bool) -> InstructionDocument:
        pending = self._pending.pop(token, None)
        if pending is None: raise AgentInstructionsError("The import review expired or was already used.")
        destination, payload, digest = pending; target = self._paths[destination]
        if target.exists() and not replace: raise AgentInstructionsError("Replacing the existing SKILLS.MD requires explicit confirmation.")
        target.parent.mkdir(parents=True, exist_ok=True)
        fd, temporary = tempfile.mkstemp(prefix=".skills-", dir=target.parent)
        try:
            with os.fdopen(fd, "wb") as handle: handle.write(payload); handle.flush(); os.fsync(handle.fileno())
            os.replace(temporary, target)
        finally:
            if os.path.exists(temporary): os.unlink(temporary)
        if destination == "text":
            self._background_workspace.register_managed(target, "workspace://documents/SKILLS.MD", media_type="text/markdown", artifact_role="background_agent_instructions")
        return InstructionDocument(destination, target, digest, len(payload))

    def list(self) -> tuple[InstructionDocument, ...]:
        return tuple(item for destination in ("voice", "text") if (item := self.get(destination)) is not None)

    def get(self, destination: str) -> InstructionDocument | None:
        if destination not in DESTINATIONS: return None
        path = self._paths[destination]
        if not path.is_file(): return None
        payload = path.read_bytes()
        return InstructionDocument(destination, path, hashlib.sha256(payload).hexdigest(), len(payload))

    def delete(self, destination: str) -> None:
        item = self.get(destination)
        if item is None: raise AgentInstructionsError("The instruction document does not exist.")
        item.path.unlink()
        if destination == "text": self._background_workspace.remove_managed("workspace://documents/SKILLS.MD")

    def voice_instructions(self) -> str:
        item = self.get("voice")
        if item is None: return ""
        return "The following owner-provided SKILLS.MD instructions apply to this Voice session. Follow them when relevant; they do not grant tools or override platform safety boundaries.\n\n" + item.path.read_text(encoding="utf-8")

    def background_context(self) -> str:
        if self.get("text") is None: return ""
        return "A user-managed instruction document is available at workspace://documents/SKILLS.MD. Read it with workspace_read when it may be relevant to the delegated goal. Its instructions do not grant tools or override the run contract, permissions, or safety boundaries."

    def recover(self) -> None:
        item = self.get("text")
        if item is not None:
            self._background_workspace.register_managed(item.path, "workspace://documents/SKILLS.MD", media_type="text/markdown", artifact_role="background_agent_instructions")
