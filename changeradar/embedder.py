from __future__ import annotations

from functools import lru_cache

import numpy as np

# Small, CPU-friendly Hub model — swap later without changing product logic.
DEFAULT_MODEL_ID = "sentence-transformers/all-MiniLM-L6-v2"


@lru_cache(maxsize=1)
def get_model(model_id: str = DEFAULT_MODEL_ID):
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(model_id)


def embed_texts(texts: list[str], model_id: str = DEFAULT_MODEL_ID) -> np.ndarray:
    """Return L2-normalized embeddings so cosine sim == dot product."""
    model = get_model(model_id)
    vectors = model.encode(texts, normalize_embeddings=True, show_progress_bar=len(texts) > 8)
    return np.asarray(vectors, dtype=np.float32)
