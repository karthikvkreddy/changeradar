# Public seed (derived)

Label-derived text from:

| Source | Cases | License |
|--------|------:|---------|
| [phamquiluan/RCAEval](https://huggingface.co/datasets/phamquiluan/RCAEval) | 735 | MIT |
| [LLM4Ops/Cloud-OpsBench](https://huggingface.co/datasets/LLM4Ops/Cloud-OpsBench) | 754 | MIT |
| [EvoTestOps/AnoMod](https://github.com/EvoTestOps/AnoMod) ([paper](https://dl.acm.org/doi/pdf/10.1145/3793302.3793324), [Zenodo](https://zenodo.org/records/18342898)) | 24 | MIT (GitHub experiment catalog). Zenodo dump is CC-BY; we do not copy it. |

Telemetry (metrics/logs) is **not** copied — including **no** `AnoMod.zip`. We only keep published case labels turned into ChangeRadar JSONL.

AnoMod attribution: Ping, K., Mazhar, H., Wang, Y., Song, Y., & Mäntylä, M. V. (2026). *AnoMod: A Dataset for Anomaly Detection and Root Cause Analysis in Microservice System.* MSR '26. Table 2: 12 types × SocialNetwork + TrainTicket. Chaos Mesh YAML names/services from `TT_collection-scripts/chaos-experiments/`.

## What “high confidence” means here

Each `gold_pairs.jsonl` row links a change to the **same labeled case**.

- **Valid claim:** this change text should retrieve that incident (same injected fault / same snapshot).
- **Invalid claim:** shipping this change in your prod cluster will cause an outage with 90% probability.

Rebuild:

```bash
pip install -r scripts/requirements-import.txt
python scripts/import_public_seed.py
python scripts/eval_gold_pairs.py
```
