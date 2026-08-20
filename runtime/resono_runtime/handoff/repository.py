from __future__ import annotations
from dataclasses import dataclass
from ..storage.database import RuntimeDatabase

@dataclass(frozen=True, slots=True)
class StoredHandoff:
    handoff_id: str; session_id: str; file_key: str; filename: str; mime_type: str
    content_hash: str; question_hash: str; model_key: str; inspection_markdown: str; created_at: str

class HandoffRepository:
    def __init__(self, database: RuntimeDatabase) -> None: self._database = database
    def cached(self, content_hash: str, question_hash: str, model_key: str) -> StoredHandoff | None:
        with self._database.connect() as connection:
            row = connection.execute("SELECT * FROM direct_handoffs WHERE content_hash=? AND question_hash=? AND model_key=? ORDER BY created_at DESC LIMIT 1", (content_hash, question_hash, model_key)).fetchone()
        return _row(row) if row else None
    def save(self, item: StoredHandoff) -> StoredHandoff:
        with self._database.connect() as connection:
            connection.execute("INSERT INTO direct_handoffs VALUES (?,?,?,?,?,?,?,?,?,?)", tuple(getattr(item, name) for name in item.__dataclass_fields__))
            connection.commit()
        return item

def _row(row: object) -> StoredHandoff:
    return StoredHandoff(*(str(row[key]) for key in StoredHandoff.__dataclass_fields__))
