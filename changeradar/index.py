from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from changeradar.corpus import incident_embed_text, load_jsonl
from changeradar.embedder import DEFAULT_MODEL_ID, embed_texts


@dataclass
class Hit:
    score: float
    incident: dict[str, Any]


@dataclass
class IncidentIndex:
    model_id: str
    incidents: list[dict[str, Any]]
    embeddings: np.ndarray  # shape (n, dim), L2-normalized

    def search(self, query_text: str, top_k: int = 5) -> list[Hit]:
        q = embed_texts([query_text], model_id=self.model_id)[0]
        scores = self.embeddings @ q  # cosine similarity
        k = min(top_k, len(self.incidents))
        idxs = np.argsort(-scores)[:k]
        return [Hit(score=float(scores[i]), incident=self.incidents[i]) for i in idxs]

    def save(self, directory: Path) -> None:
        directory.mkdir(parents=True, exist_ok=True)
        np.save(directory / "embeddings.npy", self.embeddings)
        meta = {
            "model_id": self.model_id,
            "count": len(self.incidents),
            "dim": int(self.embeddings.shape[1]),
        }
        (directory / "meta.json").write_text(json.dumps(meta, indent=2) + "\n")
        with (directory / "incidents.jsonl").open("w") as f:
            for row in self.incidents:
                f.write(json.dumps(row) + "\n")

    @classmethod
    def load(cls, directory: Path) -> IncidentIndex:
        meta = json.loads((directory / "meta.json").read_text())
        incidents = load_jsonl(directory / "incidents.jsonl")
        embeddings = np.load(directory / "embeddings.npy")
        if len(incidents) != embeddings.shape[0]:
            raise ValueError("incidents.jsonl and embeddings.npy length mismatch")
        return cls(model_id=meta["model_id"], incidents=incidents, embeddings=embeddings)


def build_index(
    incidents_path: Path,
    model_id: str = DEFAULT_MODEL_ID,
) -> IncidentIndex:
    incidents = load_jsonl(incidents_path)
    if not incidents:
        raise ValueError(f"No incidents in {incidents_path}")
    texts = [incident_embed_text(row) for row in incidents]
    embeddings = embed_texts(texts, model_id=model_id)
    return IncidentIndex(model_id=model_id, incidents=incidents, embeddings=embeddings)
