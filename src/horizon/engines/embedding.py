"""Lazy-loaded embedding engine backed by sentence-transformers."""

from __future__ import annotations

import threading
from collections.abc import Sequence

import numpy as np
from numpy import ndarray

from horizon.session import Session


def resolve_embedding_device(preferred: str | None = None) -> str:
    """Pick the inference device for the embedding model.

    SentenceTransformer defaults to the "strongest" accelerator (CUDA/MPS).
    For Horizon's workload — many small ``encode`` calls per turn — MPS/GPU
    often loses to CPU because of per-call sync and ``.cpu()`` transfer cost.
    SBERT efficiency docs recommend CPU for latency-sensitive local embedding:
    https://sbert.net/docs/sentence_transformer/usage/efficiency.html

    ONNX/OpenVINO backends (2–3× CPU speedup) need sentence-transformers≥3.2;
    tracked separately from this pin-compatible path.
    """
    if preferred and preferred != "auto":
        return preferred
    try:
        import torch

        if preferred == "auto" and torch.cuda.is_available():
            return "cuda"
    except ImportError:
        pass
    return "cpu"


class EmbeddingModelError(RuntimeError):
    """Raised when the embedding model cannot be loaded."""


class EmbeddingEngine:
    """Thread-safe, lazily-initialized embedding engine.

    The model is downloaded / loaded on the first call to embed(), not on
    __init__. This keeps new_conversation() instant and first process_turn()
    as the only potentially slow operation.
    """

    def __init__(
        self,
        model_name: str = "all-MiniLM-L6-v2",
        model_path: str | None = None,
        device: str | None = "cpu",
    ) -> None:
        self._model_name = model_name
        self._model_path = model_path
        self._device = resolve_embedding_device(device)
        self._model = None
        self._dim: int | None = None
        self._lock = threading.Lock()

    def _ensure_loaded(self) -> None:
        if self._model is not None:
            return
        try:
            from sentence_transformers import SentenceTransformer

            source = self._model_path or self._model_name
            self._model = SentenceTransformer(source, device=self._device)
            # get_embedding_dimension is the new API; fall back for older versions
            get_dim = getattr(
                self._model,
                "get_embedding_dimension",
                getattr(self._model, "get_sentence_embedding_dimension", None),
            )
            self._dim = get_dim() if get_dim else self._model.encode("x").shape[-1]
        except Exception as exc:
            raise EmbeddingModelError(
                f"Failed to load embedding model '{self._model_path or self._model_name}': {exc}"
            ) from exc

    def ensure_loaded(self) -> None:
        """Eagerly load the embedding model.

        Public alias of _ensure_loaded() intended for tests that need to
        isolate model download / network access from subsequent operations.
        """
        self._ensure_loaded()

    @staticmethod
    def _as_vector(raw: object) -> ndarray:
        return np.asarray(raw, dtype=np.float32).reshape(-1)

    def _encode_many(self, texts: Sequence[str]) -> list[ndarray]:
        """Run one batched forward pass; serialised for thread-safe sharing."""
        if not texts:
            return []
        self._ensure_loaded()
        with self._lock:
            raw = self._model.encode(
                list(texts),
                normalize_embeddings=True,
                show_progress_bar=False,
                convert_to_numpy=True,
                batch_size=min(32, len(texts)),
            )
        if len(texts) == 1:
            return [self._as_vector(raw)]
        return [self._as_vector(raw[i]) for i in range(len(texts))]

    def embed(self, text: str) -> ndarray:
        """Return a unit-norm embedding vector for the given text."""
        return self._encode_many([text])[0]

    def embed_batch(self, texts: list[str]) -> list[ndarray]:
        """Embed a batch of texts in a single model call (faster than N embed() calls)."""
        return self._encode_many(texts)

    @property
    def dim(self) -> int:
        self._ensure_loaded()
        return self._dim


def update_history(session: Session, new_combined: ndarray, decay: float = 0.9) -> None:
    """Update the session's exponentially-weighted history embedding in place.

    The history embedding summarises what the conversation has covered so far.
    decay=0.9 means a turn's influence halves after ~7 subsequent turns,
    matching the agent's approximate attention pattern.
    """
    if session.history_embedding is None:
        session.history_embedding = new_combined.copy()
    else:
        session.history_embedding = decay * session.history_embedding + (1.0 - decay) * new_combined
        norm = np.linalg.norm(session.history_embedding)
        if norm > 1e-8:
            session.history_embedding /= norm
