#!/usr/bin/env python3
"""
Phase 0 — Prove Hugging Face + embeddings work on your machine.

What you learn:
  - Model IDs on the Hub look like `org/name` (e.g. sentence-transformers/...)
  - First run downloads weights into ~/.cache/huggingface/
  - Embeddings turn text into fixed-size float vectors; similar meaning → high cosine similarity
"""

from __future__ import annotations

import sys

MODEL_ID = "sentence-transformers/all-MiniLM-L6-v2"

# Tiny Kubernetes/Helm flavored phrases — same idea we'll use for real incidents later.
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
    print("(First run downloads ~90MB into ~/.cache/huggingface/ — that is normal.)\n")

    try:
        from sentence_transformers import SentenceTransformer
    except ImportError:
        print("sentence-transformers not installed. Run:", file=sys.stderr)
        print("  pip install -r requirements.txt", file=sys.stderr)
        return 1

    model = SentenceTransformer(MODEL_ID)
    vectors = model.encode(TEXTS, normalize_embeddings=True)

    print(f"Embedding dim: {len(vectors[0])}")
    print(f"Example vector snippet (first 8 floats): {vectors[0][:8]}\n")

    print("Cosine similarity (1.0 = identical meaning direction):")
    print(f"  [0] vs [1] (both scale checkout-api) : {cosine(vectors[0], vectors[1]):.3f}")
    print(f"  [0] vs [2] (scale vs TLS rotate)     : {cosine(vectors[0], vectors[2]):.3f}")
    print()
    print("Expect [0]↔[1] much higher than [0]↔[2]. That is the core of ChangeRadar.")
    print("Phase 0 OK.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
