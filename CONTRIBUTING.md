# Contributing

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

Python 3.11 or newer.

## Checks

```bash
python scripts/validate_corpus.py
python -m changeradar eval
```

`eval --suite public` downloads MiniLM and embeds ~1.5k rows; skip it for small patches.

## Pull requests

- Keep changes focused. Match existing module layout under `changeradar/`.
- Do not commit `.venv/`, `data/index/`, or Hugging Face tokens.
- Retrieval metrics (Hit@k, MRR) are lookalike ranking, not production outage probability. Do not reframe them as such in docs.
