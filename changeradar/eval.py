"""Retrieval eval. Numbers are lookalike ranking, not P(outage)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from changeradar.corpus import change_embed_text, incident_embed_text, load_jsonl
from changeradar.diffparse import summarize_diff
from changeradar.embedder import embed_texts


@dataclass
class EvalResult:
    name: str
    n: int
    hit1: int
    hit3: int
    family_hit1: int
    mrr: float
    details: list[str]

    def as_dict(self) -> dict[str, Any]:
        n = max(self.n, 1)
        return {
            "suite": self.name,
            "pairs": self.n,
            "hit_at_1": round(self.hit1 / n, 3),
            "hit_at_3": round(self.hit3 / n, 3),
            "family_hit_at_1": round(self.family_hit1 / n, 3),
            "mrr": round(self.mrr, 3),
        }

    def format(self) -> str:
        d = self.as_dict()
        return (
            f"{self.name}: n={self.n}  "
            f"Hit@1={d['hit_at_1']:.3f} ({self.hit1}/{self.n})  "
            f"Hit@3={d['hit_at_3']:.3f} ({self.hit3}/{self.n})  "
            f"family Hit@1={d['family_hit_at_1']:.3f}  "
            f"MRR={d['mrr']:.3f}"
        )


def family_key(inc_id: str, inc: dict[str, Any] | None = None) -> str:
    if inc_id.startswith("rca-"):
        return inc_id.rsplit("_", 1)[0]
    if inc_id.startswith("anom-"):
        # anom-tt-cpu_contention / anom-sn-cpu_contention → same type family
        return inc_id.split("-", 2)[-1]
    if inc is not None and inc.get("root_cause"):
        return f"{inc.get('source', '')}|{inc.get('root_cause')}|{inc.get('blast_radius', '')}"
    return inc_id


def query_text(pair: dict[str, Any], changes: dict[str, dict], root: Path) -> str:
    kind = pair.get("query_kind") or ("diff" if pair.get("diff_file") else "change")
    if kind == "diff":
        raw = (root / pair["diff_file"]).read_text()
        return summarize_diff(raw).embed_text()
    change = changes[pair["change_id"]]
    return change_embed_text(change)


def run_eval(
    *,
    name: str,
    incidents: list[dict[str, Any]],
    queries: list[str],
    gold_incident_ids: list[str],
) -> EvalResult:
    id_to_row = {inc["id"]: i for i, inc in enumerate(incidents)}
    families = [family_key(inc["id"], inc) for inc in incidents]
    inc_vec = embed_texts([incident_embed_text(x) for x in incidents])
    q_vec = embed_texts(queries)

    hit1 = hit3 = fam1 = 0
    rr: list[float] = []
    details: list[str] = []
    for qi, gold_id in enumerate(gold_incident_ids):
        if gold_id not in id_to_row:
            raise KeyError(f"gold incident {gold_id} not in corpus")
        target = id_to_row[gold_id]
        order = np.argsort(-(inc_vec @ q_vec[qi]))
        rank = int(np.where(order == target)[0][0]) + 1
        top_id = incidents[int(order[0])]["id"]
        if rank == 1:
            hit1 += 1
        if rank <= 3:
            hit3 += 1
        rr.append(1.0 / rank)
        if families[int(order[0])] == families[target]:
            fam1 += 1
        details.append(f"  q{qi + 1}: gold={gold_id} rank={rank} top={top_id}")

    n = len(gold_incident_ids)
    return EvalResult(
        name=name,
        n=n,
        hit1=hit1,
        hit3=hit3,
        family_hit1=fam1,
        mrr=float(np.mean(rr)) if rr else 0.0,
        details=details,
    )


def load_suite_queries(
    gold_path: Path,
    changes_path: Path,
    root: Path,
) -> tuple[list[str], list[str]]:
    gold = load_jsonl(gold_path)
    changes = {c["id"]: c for c in load_jsonl(changes_path)} if changes_path.exists() else {}
    queries = [query_text(g, changes, root) for g in gold]
    ids = [g["incident_id"] for g in gold]
    return queries, ids
