from __future__ import annotations

from collections.abc import Callable, Sequence
import hashlib
import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from resono_runtime.core.logging import runtime_logger

from .platform import OpenAIProviderError


_LOG = runtime_logger()

DEFAULT_EMBEDDING_MODEL = "text-embedding-3-small"
DEFAULT_EMBEDDING_DIMENSIONS = 1536

EmbedExecutor = Callable[..., list[list[float]]]


class EmbeddingUnavailable(RuntimeError):
    """Raised when a real provider embedding cannot be produced."""


class OpenAIEmbeddings:
    """Real OpenAI text embeddings over the Platform API.

    No hash, random, or keyword fallback is used: embeddings are real provider
    vectors. When the provider is unreachable or no Platform key is available,
    embedding fails explicitly so the pipeline can store memory without a vector
    rather than pretend a semantic search exists.
    """

    API_ROOT = "https://api.openai.com/v1"

    def __init__(
        self,
        api_key: str,
        *,
        safety_source: str,
        model: str = DEFAULT_EMBEDDING_MODEL,
        dimensions: int = DEFAULT_EMBEDDING_DIMENSIONS,
        executor: EmbedExecutor | None = None,
    ) -> None:
        self._api_key = api_key
        self._safety_id = hashlib.sha256(
            f"resono-r1:{safety_source}".encode()
        ).hexdigest()
        self._model = model
        self._dimensions = int(dimensions)
        self._executor = executor

    @property
    def model_key(self) -> str:
        return self._model

    @property
    def dimensions(self) -> int:
        return self._dimensions

    def embed(self, text: str) -> list[float]:
        return self.embed_many([text])[0]

    def embed_many(self, texts: Sequence[str]) -> list[list[float]]:
        cleaned = [item.strip() for item in texts if item and item.strip()]
        if not cleaned:
            raise EmbeddingUnavailable("No text provided for embedding.")
        if any(len(item) > 16_384 for item in cleaned):
            raise EmbeddingUnavailable("Embedding input exceeds the maximum length.")
        if self._executor is not None:
            vectors = self._executor(
                api_key=self._api_key,
                model=self._model,
                inputs=cleaned,
            )
        else:
            vectors = self._http_embed(cleaned)
        return _validate_vectors(vectors, self._dimensions)

    def _http_embed(self, texts: list[str]) -> list[list[float]]:
        body = json.dumps(
            {"model": self._model, "input": texts, "dimensions": self._dimensions},
            separators=(",", ":"),
        ).encode()
        request = Request(
            self.API_ROOT + "/embeddings",
            data=body,
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
                "Accept": "application/json",
                "OpenAI-Safety-Identifier": self._safety_id,
            },
            method="POST",
        )
        try:
            with urlopen(request, timeout=30) as response:
                payload = json.loads(response.read(8_388_608).decode())
        except HTTPError as error:
            status = int(error.code)
            _LOG.warning("openai.embeddings.error status=%s", status)
            code = "credential_rejected" if status in (401, 403) else "provider_rejected"
            raise EmbeddingUnavailable(
                f"OpenAI rejected the embedding request ({code})."
            ) from error
        except (URLError, TimeoutError, OSError) as error:
            _LOG.error("openai.embeddings.error_unreachable")
            raise EmbeddingUnavailable("OpenAI is currently unreachable.") from error
        data = payload.get("data", []) if isinstance(payload, dict) else []
        if not isinstance(data, list) or len(data) != len(texts):
            raise EmbeddingUnavailable("OpenAI returned an invalid embedding response.")
        ordered = sorted(
            (item for item in data if isinstance(item, dict)),
            key=lambda item: int(item.get("index", 0)),
        )
        return [list(item.get("embedding", [])) for item in ordered]


def _validate_vectors(vectors: list[list[float]], expected_dimensions: int) -> list[list[float]]:
    if not isinstance(vectors, list) or len(vectors) == 0:
        raise EmbeddingUnavailable("Embedding provider returned no vectors.")
    validated: list[list[float]] = []
    for vector in vectors:
        if not isinstance(vector, list) or len(vector) != expected_dimensions:
            raise EmbeddingUnavailable("Embedding vector has unexpected dimensions.")
        try:
            validated.append([float(value) for value in vector])
        except (TypeError, ValueError) as error:
            raise EmbeddingUnavailable("Embedding vector is not numeric.") from error
    return validated
