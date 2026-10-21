# ChangeRadar

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![CI](https://github.com/karthikvkreddy/changeradar/actions/workflows/ci.yml/badge.svg)](https://github.com/karthikvkreddy/changeradar/actions/workflows/ci.yml)

Score a Kubernetes or Helm change against past incidents using sentence embeddings.

ChangeRadar embeds a proposed change (or a `helm` / `kubectl` diff) and ranks lookalike postmortems by cosine similarity. **This is retrieval, not outage prediction** — a high score means “this looks like a known incident,” not “this will page in production.”

[Live demo](https://huggingface.co/spaces/karthikreddyv/changeradar) · [Public dataset](https://huggingface.co/datasets/karthikreddyv/changeradar-incidents)

## Features

- CLI and local Gradio UI
- Parse `helm diff` / `kubectl diff` output
- Bring-your-own incident JSONL (re-embed, no training required)
- Public seed of 1,513 labeled cases (RCAEval, Cloud-OpsBench, AnoMod)
- Retrieval eval: Hit@1, Hit@3, family Hit@1, MRR

## Install

Python 3.11+. First run downloads [`sentence-transformers/all-MiniLM-L6-v2`](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2) (~80MB).

```bash
git clone https://github.com/karthikvkreddy/changeradar.git
cd changeradar
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e .
```

## Quick start

```bash
python -m changeradar build-index
python -m changeradar demo
python -m changeradar score "Enable default-deny NetworkPolicy in the orders namespace"
python -m changeradar score-diff data/diffs/checkout-memory.helm.diff
python -m changeradar ui   # http://127.0.0.1:7860
```

Pipe a live diff:

```bash
helm diff upgrade checkout ./chart -f values-prod.yaml | python -m changeradar score-diff
```

## Private incidents

Keep postmortems local. Ingest, rebuild the index, then score as usual:

```bash
python -m changeradar ingest --add path/to/your-incidents.jsonl
python -m changeradar build-index
```

Each incident is one JSON line:

```json
{
  "id": "inc-001",
  "title": "checkout-oom-after-helm-limit-cut",
  "namespace": "checkout",
  "date": "2024-03-12",
  "summary": "Helm values reduced memory limits for checkout-api from 1Gi to 256Mi.",
  "root_cause": "memory limit set below working set",
  "tags": ["helm", "resources", "memory", "OOM"]
}
```

Optional: pull the published seed instead of the bundled demo.

```bash
python -m changeradar build-index --from-hub
```

## How it works

1. Embed each incident (`title`, `summary`, `root_cause`, `tags`) with MiniLM (384-d, L2-normalized).
2. Embed the change description or parsed diff.
3. Rank by cosine similarity (dot product on normalized vectors).
4. Map the top score to a heuristic band for this model and corpus: **HIGH** ≥ 0.55, **MED** ≥ 0.40, else **LOW**.

Swap the Hub model with `--model` on `build-index`; no fine-tuning is required for the product to work.

## Evaluation

Numbers are lookalike ranking, not P(outage | change).

```bash
python -m changeradar eval                 # handwritten demo pairs
python -m changeradar eval --suite public  # 1,513 gold pairs
```

| Suite | Pairs | Hit@1 | Hit@3 | Family Hit@1 | MRR |
|-------|------:|------:|------:|-------------:|----:|
| Handwritten demo | 11 | 0.909 | 1.000 | — | 0.939 |
| Public seed | 1,513 | 0.288 | 0.576 | 0.672 | 0.476 |

Gold pairs are *same-case labels* (this change text should retrieve that incident). Exact Hit@1 on the public seed is pulled down by near-duplicate RCAEval repetitions; family Hit@1 is the better “known incident type” figure.

See [`data/eval/README.md`](data/eval/README.md) and [`data/public/README.md`](data/public/README.md).

## Public seed

Derived **labels only** (no metrics/logs dumps):

| Source | Cases | License |
|--------|------:|---------|
| [RCAEval](https://huggingface.co/datasets/phamquiluan/RCAEval) | 735 | MIT |
| [Cloud-OpsBench](https://huggingface.co/datasets/LLM4Ops/Cloud-OpsBench) | 754 | MIT |
| [AnoMod](https://github.com/EvoTestOps/AnoMod) | 24 | MIT |

Rebuild from upstream labels:

```bash
pip install -r scripts/requirements-import.txt
python scripts/import_public_seed.py
```

## Roadmap

Upcoming work is listed in [ROADMAP.md](ROADMAP.md).

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). Bug reports and pull requests are welcome.

## License

[MIT](LICENSE)
