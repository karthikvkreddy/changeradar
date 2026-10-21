---
license: mit
task_categories:
- sentence-similarity
language:
- en
tags:
- sre
- kubernetes
- helm
- incidents
- embeddings
pretty_name: ChangeRadar Kubernetes incidents
---

# ChangeRadar incidents

Label-derived Kubernetes / Helm incident text for [ChangeRadar](https://huggingface.co/spaces/karthikreddyv/changeradar). Embed a proposed change, rank lookalike past incidents. **Retrieval, not outage prediction.**

| File | Rows | Role |
|------|-----:|------|
| `incidents.jsonl` | 1,513 | Public seed (search corpus) |
| `changes.jsonl` | 1,513 | Same-case change text (queries) |
| `gold_pairs.jsonl` | 1,513 | Retrieval labels (change_id → incident_id) |
| `demo/incidents.jsonl` | 18 | Hand-written Helm postmortems |
| `demo/changes.jsonl` | 10 | Hand-written change descriptions |

Telemetry is not included. Rows are labels turned into JSONL.

## Public seed sources

| Source | Cases | License |
|--------|------:|---------|
| [phamquiluan/RCAEval](https://huggingface.co/datasets/phamquiluan/RCAEval) | 735 | MIT |
| [LLM4Ops/Cloud-OpsBench](https://huggingface.co/datasets/LLM4Ops/Cloud-OpsBench) | 754 | MIT |
| [EvoTestOps/AnoMod](https://github.com/EvoTestOps/AnoMod) | 24 | MIT (GitHub experiment catalog; Zenodo dump not copied) |

Gold pairs are **same-case labels**: the change text should retrieve that incident. They are not P(production outage | change).

Rebuild locally from this git repo:

```bash
pip install -r scripts/requirements-import.txt
python scripts/import_public_seed.py
```
