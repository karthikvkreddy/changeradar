# Local corpora (not published)

Mined GitHub issue text stays **out of git**. Put it here, then ingest and eval:

```bash
python -m changeradar ingest \
  --add ../changeradar-corpus/export/incidents.jsonl \
  --into data/local/github/incidents.jsonl
cp ../changeradar-corpus/export/changes.jsonl data/local/github/changes.jsonl
cp ../changeradar-corpus/export/gold_pairs.jsonl data/local/github/gold_pairs.jsonl

python -m changeradar build-index \
  --incidents data/local/github/incidents.jsonl \
  --out data/index-github

python -m changeradar eval --suite github
```

This does not mix into `data/incidents.jsonl` (the 18 handwritten demos).

Last local run (MiniLM, 214 incidents, 67 same-document pairs): Hit@1 0.940, Hit@3 0.970, family Hit@1 0.985, MRR 0.960. That is same-issue retrieval, not a production-outage claim.
