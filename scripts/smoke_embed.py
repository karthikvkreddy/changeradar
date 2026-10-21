#!/usr/bin/env python3
"""Sanity-check that MiniLM embeddings separate related Helm changes from unrelated ones."""

from __future__ import annotations

import sys

MODEL_ID = "sentence-transformers/all-MiniLM-L6-v2"

TEXTS = [
    "Helm upgrade doubled replica count for checkout-api in production",
    "Increased HPA maxReplicas for checkout-api Deployment from 5 to 20",
    "Rotated TLS certs for the ingress-nginx controller",
]


def cosine(a, b) -> float:
    import numpy as np

    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))


def main() -> int:
    print(f"Loading model: {MODEL_ID}")
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError:
        print("sentence-transformers not installed. Run: pip install -e .", file=sys.stderr)
        return 1

    model = SentenceTransformer(MODEL_ID)
    vectors = model.encode(TEXTS, normalize_embeddings=True)

    print(f"Embedding dim: {len(vectors[0])}")
    print("Cosine similarity (1.0 = identical meaning direction):")
    print(f"  [0] vs [1] (both scale checkout-api) : {cosine(vectors[0], vectors[1]):.3f}")
    print(f"  [0] vs [2] (scale vs TLS rotate)     : {cosine(vectors[0], vectors[2]):.3f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
