# ChangeRadar — learning log

## Phase 0 — Hugging Face Hub + embeddings

### Account + token
1. Open https://huggingface.co/settings/tokens
2. Create a token with at least **Read** access
3. Name it something like `changeradar-local`
4. Copy it once — you will not see it again

### Login on this machine
```bash
source .venv/bin/activate
huggingface-cli login
# paste the token when prompted
```

Or non-interactive:
```bash
huggingface-cli login --token hf_...
```

Public models like `all-MiniLM-L6-v2` often work without a token, but login is required for nicer rate limits and later Space deploys.

### Key idea: embeddings
Text → vector of floats. Similar ops language lands nearby in vector space.
ChangeRadar will embed *proposed changes* and *past incidents*, then find nearest neighbors.

### Model we start with
`sentence-transformers/all-MiniLM-L6-v2`
- Small, fast, CPU-friendly
- Good enough for an SRE prototype
- Later we can swap to a stronger Hub model without rewriting the product

### Your account
Logged in as `karthikreddyv` (`hf auth whoami`).

## Phase 1 — Seed corpus (Kubernetes / Helm)

We store demo data as **JSONL** (one JSON object per line): easy to append, git-friendly, no DB yet.

| File | Role |
|------|------|
| `data/incidents.jsonl` | Past outages (what we search *against*) |
| `data/changes.jsonl` | Proposed changes (what we *score*) |

Each incident has `summary` + `root_cause` — that text is what we will embed in Phase 2.
Each change has `description` — that is the query vector.

Validate anytime:
```bash
source .venv/bin/activate
python scripts/phase1_validate_corpus.py
```

## Phase 2 — Build index + score CLI

### Product loop
1. **build-index** — embed every incident once → save vectors under `data/index/`
2. **score** — embed a proposed change → cosine similarity vs all incidents → top-k lookalikes

### Commands
```bash
source .venv/bin/activate
# from repo root
python -m changeradar build-index
python -m changeradar demo
python -m changeradar score --change-id chg-001
python -m changeradar score "Helm NetworkPolicy default deny in orders ns"
```

### HF concepts in play
| Concept | Where |
|---------|--------|
| Hub model id | `sentence-transformers/all-MiniLM-L6-v2` in `embedder.py` |
| Local cache | first encode downloads weights to `~/.cache/huggingface/` |
| Embedding | text → 384-float vector |
| Cosine similarity | with normalized vectors = dot product (`embeddings @ query`) |

### Risk bands (heuristic)
- **HIGH** ≥ 0.55 — strong lookalike outage
- **MED** ≥ 0.40
- **LOW** below that

These thresholds are starting points for MiniLM on *this* corpus — we can tune later.

## Phase 3 — Gradio UI (Hugging Face's usual app layer)

Gradio turns a Python function into a small web form. Hugging Face **Spaces** later hosts that same app.

| File | Role |
|------|------|
| `changeradar/ui.py` | Form: change text → `index.search` → Markdown results |
| `app.py` | Entry point Spaces looks for (`demo = build_app()`) |
| `python -m changeradar ui` | Launch locally (http://127.0.0.1:7860) |

Same scoring path as the CLI. Only the interface changed.

```bash
source .venv/bin/activate
python -m changeradar ui
```

Phase 4: push this folder as a Space at huggingface.co/spaces so others can try it without installing Python.

## Phase 4 — Hugging Face Space

A **Space** is a git repo on the Hub that runs `app.py` (Gradio). Same code as local UI.

Needed files:
- `README.md` with YAML header (`sdk: gradio`, `app_file: app.py`)
- `app.py` — Spaces entrypoint
- `requirements.txt` — pip install on the Space CPU
- `changeradar/` + `data/incidents.jsonl` — app + corpus

A **Write** token is required to create/upload (Read was enough for model download).

### What we hit in 2026
New personal accounts cannot host **Gradio / Docker** Spaces on CPU without **PRO** (or wait 30 days / grant for ZeroGPU). **Static** Spaces stay free.

So Phase 4 publishes:
1. A **static Space** that runs MiniLM in the browser via **Transformers.js** (`Xenova/all-MiniLM-L6-v2`)
2. A **dataset** of the incident/change JSONL on the Hub

Same product idea as the Python CLI. Different HF runtime (browser instead of Gradio CPU).

| Hub URL | Kind |
|---------|------|
| https://huggingface.co/spaces/karthikreddyv/changeradar | Static Space |
| https://huggingface.co/datasets/karthikreddyv/changeradar-incidents | Dataset |

### Commands we used to publish

```bash
hf auth login
hf auth whoami
hf auth list

hf repos create karthikreddyv/changeradar --type space --sdk static --public
hf upload karthikreddyv/changeradar ./space . --repo-type space \
  --commit-message "In-browser ChangeRadar: Transformers.js MiniLM scorer"

hf repos create karthikreddyv/changeradar-incidents --type dataset --public --exist-ok
hf upload karthikreddyv/changeradar-incidents ./data/incidents.jsonl incidents.jsonl --repo-type dataset
hf upload karthikreddyv/changeradar-incidents ./data/changes.jsonl changes.jsonl --repo-type dataset
hf upload karthikreddyv/changeradar-incidents ./data/README.md README.md --repo-type dataset

hf spaces ls karthikreddyv/changeradar
hf spaces info karthikreddyv/changeradar
```

Re-upload the Space after editing `space/`. Full runbook is in the repo `README.md` **Commands** section.

## Phase 5 — Diffs + bring-your-own corpus

**Product stance:** ChangeRadar is an engine. The public JSONL is a *seed*, not a benchmark. Corporates add private incidents and re-embed. That is “teaching the system your history,” not GPU fine-tuning.

| Command | Meaning |
|---------|---------|
| `score-diff FILE` | Parse Helm/kubectl `+`/`-` lines → embed → same cosine search |
| `ingest --add yours.jsonl` | Append incidents (skip duplicate ids) |
| `build-index --from-hub` | Pull `incidents.jsonl` from the Hub dataset |

```bash
python -m changeradar score-diff data/diffs/checkout-memory.helm.diff
python -m changeradar ingest --add data/samples/byo-incident.jsonl --into /tmp/cr-incidents.jsonl
python -m changeradar build-index --from-hub
```

## Public seed (~1.5k) and what “>90% confident” can mean

No 1–2k *production Helm-diff → outage* dataset exists in the open. Closest MIT sources:

| Dataset | n | What it really is |
|---------|---:|-------------------|
| RCAEval | 735 | Injected faults on Boutique / Sock Shop / Train Ticket |
| Cloud-OpsBench | 754 | Labeled K8s incident snapshots |
| AnoMod | 24 | Table 2 labels only (CPU/net/disk, pod kill, DNS, HTTP abort, DB pool/tx, code). GitHub MIT. No `AnoMod.zip`. |

We derive `data/public/*.jsonl` + `gold_pairs.jsonl` (same case on both sides).

- **OK to say:** gold change should retrieve that known incident (or its fault family).
- **Not OK to say:** this change causes a prod outage with 90% probability.

Exact-id Hit@1 is pulled down by RCAEval repeats (5 nearly identical cpu-on-adservice cases). Family Hit@1 is the honest “known incident type” number.

Fine-tuning / a real training loop is a **later phase**. Day-one corporate path stays `ingest` + `build-index`.

## Phase 6 — Eval command (this repo)

Corpus mining (GitHub/SO) is a **different session** (`changeradar-corpus`). Here we only measure the engine.

```bash
python -m changeradar eval                 # handwritten demo pairs + diffs
python -m changeradar eval --suite public  # 1.5k gold pairs
```

Publish Hit@1 / Hit@3 / MRR as **retrieval** metrics. Fine-tune stays later.

