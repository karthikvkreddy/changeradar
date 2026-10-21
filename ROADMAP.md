# Roadmap

ChangeRadar v0.2 is a retrieval engine (lookalike incidents), not an outage predictor.

## Next

| Session | Where | Goal |
|---------|--------|------|
| **A** | this repo | CI tests for `score-diff`: memory-limit cut → checkout OOM (HIGH); docs-only ConfigMap typo must not look like an outage |
| **B** | `changeradar-corpus` | Helm-shaped change text as the query (not issue-body copies). Re-run `eval --suite github` |
| **C** | this repo | Score the same queries against the 1,513 public seed. Decide whether demo or public index is the default |
| **D** | this repo | Bring-your-own private incidents → `ingest` → real `helm diff` |
| **E** | later | Fine-tune embeddings only if B–D show the baseline is worth beating |

## Done

- CLI, Gradio UI, in-browser Space, Hub dataset
- 1,513-row public seed (RCAEval, Cloud-OpsBench, AnoMod **labels only**)
- 18 handwritten demos in git; mined GitHub issues stay local (`data/local/`)
