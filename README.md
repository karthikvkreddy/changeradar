# ChangeRadar

Open-source **change-impact retrieval** for SRE: score a Kubernetes / Helm change (or a real `helm`/`kubectl` diff) against past incidents using Hugging Face embeddings.

Public seed is now **1,513 labeled cases** derived from RCAEval + Cloud-OpsBench (MIT) plus AnoMod Table 2 labels (GitHub MIT; Zenodo telemetry zip unused), plus the original 18 hand-written Helm examples. Gold pairs are *same-case labels* (retrieval), not “this change will page in prod.” Fine-tuning is a later phase; day-one path is still ingest + re-embed.

**Larger mined corpus** (GitHub issues, Stack Exchange, docs) lives in a sibling repo: [`changeradar-corpus`](../changeradar-corpus). That track is independent of Hugging Face.

Cosine score = lookalike ranking, not a prediction that the change will page.

## Why this exists

Most SRE tooling alerts on thresholds or greps logs. ChangeRadar puts change descriptions (and diffs) in the same vector space as postmortems so a proposed change can surface *lookalike outages* before merge.

## Bring-your-own incidents (the corporate path)

1. Keep incidents private as JSONL (`id`, `title`, `summary`, `root_cause`, `tags`).
2. `python -m changeradar ingest --add your-incidents.jsonl`
3. `python -m changeradar build-index`
4. Pipe a real diff: `helm diff upgrade … | python -m changeradar score-diff`

Later (optional): fine-tune or swap the Hub embedding model. The product works before that.

## Commands

Activate the venv first (`source .venv/bin/activate`). Recreate it only on a new machine.

### One-time local setup

```bash
cd /Users/karthikkumarreddy/Documents/ai-jobs/changeradar
python3.11 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -r requirements.txt
```

### Hugging Face login (CLI)

```bash
hf auth login          # paste token (Read for downloads, Write to push)
hf auth whoami
hf auth list
```

### Run locally

```bash
# Phase 0 — prove embeddings work
python scripts/phase0_smoke_embed.py

# Phase 1 — validate JSONL corpus
python scripts/phase1_validate_corpus.py

# Phase 2 — embed incidents, then score
python -m changeradar build-index
python -m changeradar demo
python -m changeradar score --change-id chg-001
python -m changeradar score --change-id chg-009 --top-k 3
python -m changeradar score "Enable default-deny NetworkPolicy in orders ns"

# Phase 3 — Gradio UI (http://127.0.0.1:7860)
python -m changeradar ui
# python app.py          # same UI, Spaces-style entrypoint

# Phase 5 — real diffs + Hub corpus + BYO incidents
python -m changeradar score-diff data/diffs/checkout-memory.helm.diff
python -m changeradar score-diff data/diffs/hpa-maxreplicas.helm.diff
python -m changeradar score-diff data/diffs/docs-only.helm.diff
# helm diff upgrade checkout ./chart -f values-prod.yaml | python -m changeradar score-diff
python -m changeradar build-index --from-hub
python -m changeradar ingest --add data/samples/byo-incident.jsonl
python -m changeradar build-index

# Public seed (~1.5k + AnoMod labels) + gold-pair retrieval eval
pip install -r scripts/requirements-import.txt   # once, to rebuild from Hub
python scripts/import_public_seed.py
python -m changeradar build-index --incidents data/public/incidents.jsonl --out data/index-public
python scripts/eval_gold_pairs.py

# Phase 6 — retrieval eval (not outage probability)
python -m changeradar eval
python -m changeradar eval --suite public
```

### Push to Hugging Face (Phase 4)

Gradio Spaces need Pro on a new account, so we published a **static Space** + a **dataset**.

```bash
# Create empty repos (once)
hf repos create karthikreddyv/changeradar --type space --sdk static --public
hf repos create karthikreddyv/changeradar-incidents --type dataset --public --exist-ok

# Upload the in-browser app (contents of space/)
hf upload karthikreddyv/changeradar ./space . --repo-type space \
  --commit-message "In-browser ChangeRadar: Transformers.js MiniLM scorer"

# Upload the public seed (1,513 cases) + handwritten demo
hf upload karthikreddyv/changeradar-incidents ./data/public/incidents.jsonl incidents.jsonl \
  --repo-type dataset --commit-message "Public seed incidents (RCAEval + Cloud-OpsBench + AnoMod)"
hf upload karthikreddyv/changeradar-incidents ./data/public/changes.jsonl changes.jsonl \
  --repo-type dataset --commit-message "Public seed changes"
hf upload karthikreddyv/changeradar-incidents ./data/public/gold_pairs.jsonl gold_pairs.jsonl \
  --repo-type dataset --commit-message "Public seed gold pairs"
hf upload karthikreddyv/changeradar-incidents ./data/README.md README.md \
  --repo-type dataset --commit-message "Dataset card for 1.5k public seed"
hf upload karthikreddyv/changeradar-incidents ./data/demo/incidents.jsonl demo/incidents.jsonl \
  --repo-type dataset --commit-message "Handwritten demo incidents"
hf upload karthikreddyv/changeradar-incidents ./data/demo/changes.jsonl demo/changes.jsonl \
  --repo-type dataset --commit-message "Handwritten demo changes"

# Inspect
hf spaces ls karthikreddyv/changeradar
hf spaces info karthikreddyv/changeradar
```

After a change to `space/`, re-run the Space `hf upload` command. After a corpus change, re-run the dataset uploads.

**Did not work on this account (kept for reference):**

```bash
# 403 with Read token; 402 Gradio/ZeroGPU without Pro
hf repos create karthikreddyv/changeradar --type space --sdk gradio --flavor cpu-basic --public
hf repos create karthikreddyv/changeradar-demo --type space --sdk gradio --flavor zero-a10g --public
```

## Hugging Face concepts used

| Concept | Role here |
|---------|-----------|
| **Hub model** | `sentence-transformers/all-MiniLM-L6-v2` maps text → 384-d vector |
| **Embeddings + cosine** | Rank incidents nearest to a proposed change |
| **Gradio** | Local browser UI (`python -m changeradar ui`) |
| **Space** | [karthikreddyv/changeradar](https://huggingface.co/spaces/karthikreddyv/changeradar) — Transformers.js in-browser |
| **Dataset** | [karthikreddyv/changeradar-incidents](https://huggingface.co/datasets/karthikreddyv/changeradar-incidents) |

## Risk bands (heuristic for MiniLM on this corpus)

- **HIGH** ≥ 0.55
- **MED** ≥ 0.40
- **LOW** below that

## Phase 6 eval (retrieval, not outage probability)

Handwritten suite (9 English changes + 2 Helm diffs against the 18-incident demo):

| Metric | Result |
|--------|--------|
| Hit@1 | **0.909** (10/11) |
| Hit@3 | **1.000** (11/11) |
| MRR | **0.939** |

Miss: `hpa-maxreplicas.helm.diff` ranks `inc-002` at #3 (top is a probe incident). Public 1,513-pair suite is lower (exact Hit@1 0.288, family Hit@1 0.672) because of near-duplicate RCAEval repeats.
