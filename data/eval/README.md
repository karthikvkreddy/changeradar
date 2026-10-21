# Retrieval eval

These numbers measure **lookalike ranking**, not “this change will page.”

| Suite | What |
|-------|------|
| `handwritten.jsonl` | Original 18-incident demo + 2 Helm diffs |
| `data/public/gold_pairs.jsonl` | 1,513 same-case labels from RCAEval + Cloud-OpsBench + AnoMod |

```bash
python -m changeradar eval
python -m changeradar eval --suite public
```

Last handwritten run (MiniLM, 18-incident index): Hit@1 0.909, Hit@3 1.000, MRR 0.939.

Last public run (1,513 pairs): Hit@1 0.288, Hit@3 0.576, family Hit@1 0.672, MRR 0.476. The 24 AnoMod same-case pairs retrieve at Hit@1 1.000 on their own (distinct service+fault text, not a production-outage claim).
