from __future__ import annotations

import argparse
import sys
from pathlib import Path

from changeradar.corpus import append_incidents, change_embed_text, load_jsonl
from changeradar.diffparse import summarize_diff
from changeradar.embedder import DEFAULT_MODEL_ID
from changeradar.eval import load_suite_queries, run_eval
from changeradar.hubdata import DEFAULT_HUB_DATASET, download_incidents
from changeradar.index import IncidentIndex, build_index
from changeradar.risk import risk_band

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INCIDENTS = ROOT / "data" / "incidents.jsonl"
DEFAULT_CHANGES = ROOT / "data" / "changes.jsonl"
DEFAULT_INDEX_DIR = ROOT / "data" / "index"
DEFAULT_EVAL_HAND = ROOT / "data" / "eval" / "handwritten.jsonl"
DEFAULT_PUBLIC_INC = ROOT / "data" / "public" / "incidents.jsonl"
DEFAULT_PUBLIC_CHG = ROOT / "data" / "public" / "changes.jsonl"
DEFAULT_PUBLIC_GOLD = ROOT / "data" / "public" / "gold_pairs.jsonl"
DEFAULT_GH_INC = ROOT / "data" / "local" / "github" / "incidents.jsonl"
DEFAULT_GH_CHG = ROOT / "data" / "local" / "github" / "changes.jsonl"
DEFAULT_GH_GOLD = ROOT / "data" / "local" / "github" / "gold_pairs.jsonl"


def _incidents_path(args: argparse.Namespace) -> Path:
    if getattr(args, "from_hub", None):
        print(f"Downloading incidents from hf://datasets/{args.from_hub}")
        return download_incidents(repo_id=args.from_hub)
    return Path(args.incidents)


def cmd_build_index(args: argparse.Namespace) -> int:
    incidents = _incidents_path(args)
    print(f"Embedding incidents from {incidents} …")
    print(f"Model: {args.model}")
    index = build_index(incidents, model_id=args.model)
    out = Path(args.out)
    index.save(out)
    print(f"Wrote {len(index.incidents)} vectors (dim={index.embeddings.shape[1]}) → {out}")
    return 0


def _print_hits(query_label: str, hits) -> None:
    print(f"\nQuery: {query_label}")
    print("-" * 72)
    for i, hit in enumerate(hits, 1):
        inc = hit.incident
        risk = f"{risk_band(hit.score):<4}"
        print(f"{i}. [{hit.score:.3f}] {risk}  {inc['id']}  {inc['title']}")
        print(f"   ns={inc.get('namespace', '?')}  tags={', '.join(inc.get('tags') or [])}")
        print(f"   {inc['summary'][:140]}{'…' if len(inc['summary']) > 140 else ''}")
    print()


def cmd_score(args: argparse.Namespace) -> int:
    index = IncidentIndex.load(Path(args.index))
    text = args.text
    if args.change_id:
        changes = {c["id"]: c for c in load_jsonl(Path(args.changes))}
        if args.change_id not in changes:
            print(f"Unknown change id: {args.change_id}", file=sys.stderr)
            return 1
        change = changes[args.change_id]
        text = change_embed_text(change)
        label = f"{args.change_id} — {change['title']}"
    else:
        label = text[:80] + ("…" if len(text) > 80 else "")

    hits = index.search(text, top_k=args.top_k)
    _print_hits(label, hits)
    if hits:
        top = hits[0].score
        print(f"Top match score {top:.3f} → risk band {risk_band(top)}")
    return 0


def cmd_demo(args: argparse.Namespace) -> int:
    """Score a few seeded changes so you can see the product behavior."""
    index_dir = Path(args.index)
    if not (index_dir / "meta.json").exists():
        print("Index missing — building it first…")
        index = build_index(_incidents_path(args), model_id=args.model)
        index.save(index_dir)
    else:
        index = IncidentIndex.load(index_dir)

    demo_ids = ["chg-001", "chg-002", "chg-009"]
    changes = {c["id"]: c for c in load_jsonl(Path(args.changes))}
    for cid in demo_ids:
        change = changes[cid]
        hits = index.search(change_embed_text(change), top_k=3)
        _print_hits(f"{cid} — {change['title']}", hits)
    return 0


def cmd_ui(args: argparse.Namespace) -> int:
    from changeradar.ui import launch

    launch(share=args.share)
    return 0


def cmd_score_diff(args: argparse.Namespace) -> int:
    if args.file:
        raw = Path(args.file).read_text()
        label = Path(args.file).name
    else:
        raw = sys.stdin.read()
        label = "stdin"
    if not raw.strip():
        print("score-diff needs a file or a piped helm/kubectl diff", file=sys.stderr)
        return 1

    summary = summarize_diff(raw)
    print(f"Parsed {label}")
    print(f"  title:    {summary.title}")
    print(f"  signals:  {', '.join(summary.signals) or '(none)'}")
    print(f"  resources:{', '.join(summary.resources) or '(none)'}")

    index = IncidentIndex.load(Path(args.index))
    hits = index.search(summary.embed_text(), top_k=args.top_k)
    _print_hits(summary.title, hits)
    if hits:
        print(f"Top match score {hits[0].score:.3f} → risk band {risk_band(hits[0].score)}")
    return 0


def cmd_eval(args: argparse.Namespace) -> int:
    """Retrieval eval. Not an outage-probability score."""
    suite = args.suite
    results = []
    if suite in ("handwritten", "all"):
        incidents = load_jsonl(Path(args.incidents))
        queries, gold_ids = load_suite_queries(DEFAULT_EVAL_HAND, Path(args.changes), ROOT)
        results.append(run_eval(name="handwritten", incidents=incidents, queries=queries, gold_incident_ids=gold_ids))
    if suite in ("public", "all"):
        if not DEFAULT_PUBLIC_GOLD.exists():
            print("public suite missing — run python scripts/import_public_seed.py", file=sys.stderr)
            if suite == "public":
                return 1
        else:
            incidents = load_jsonl(DEFAULT_PUBLIC_INC)
            queries, gold_ids = load_suite_queries(DEFAULT_PUBLIC_GOLD, DEFAULT_PUBLIC_CHG, ROOT)
            if args.limit:
                queries, gold_ids = queries[: args.limit], gold_ids[: args.limit]
            results.append(run_eval(name="public", incidents=incidents, queries=queries, gold_incident_ids=gold_ids))
    if suite == "github":
        if not DEFAULT_GH_GOLD.exists():
            print(
                "github suite missing — copy changeradar-corpus/export into data/local/github/ "
                "(see data/local/README.md)",
                file=sys.stderr,
            )
            return 1
        incidents = load_jsonl(DEFAULT_GH_INC)
        queries, gold_ids = load_suite_queries(DEFAULT_GH_GOLD, DEFAULT_GH_CHG, ROOT)
        if args.limit:
            queries, gold_ids = queries[: args.limit], gold_ids[: args.limit]
        results.append(run_eval(name="github", incidents=incidents, queries=queries, gold_incident_ids=gold_ids))
    print("Retrieval only — not P(outage | change).\n")
    for r in results:
        print(r.format())
        if r.n <= 80:
            print("\n".join(r.details))
            print()
    return 0


def cmd_ingest(args: argparse.Namespace) -> int:
    dest = Path(args.into)
    incoming = load_jsonl(Path(args.add))
    added = append_incidents(dest, incoming)
    print(f"Appended {added} new incident(s) → {dest} (skipped duplicates by id)")
    print("Rebuild the index (no model training — re-embed only):")
    print(f"  python -m changeradar build-index --incidents {dest}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="changeradar",
        description="Score Kubernetes/Helm change risk against past incidents (HF embeddings).",
    )
    sub = p.add_subparsers(dest="command", required=True)

    b = sub.add_parser("build-index", help="Embed incidents.jsonl and save vectors")
    b.add_argument("--incidents", default=str(DEFAULT_INCIDENTS))
    b.add_argument("--from-hub", nargs="?", const=DEFAULT_HUB_DATASET, default=None,
                   help=f"Download incidents.jsonl from a Hub dataset (default {DEFAULT_HUB_DATASET})")
    b.add_argument("--out", default=str(DEFAULT_INDEX_DIR))
    b.add_argument("--model", default=DEFAULT_MODEL_ID)
    b.set_defaults(func=cmd_build_index)

    s = sub.add_parser("score", help="Score free text or a seeded change id")
    s.add_argument("text", nargs="?", default=None, help="Change description to score")
    s.add_argument("--change-id", help="Score a row from data/changes.jsonl (e.g. chg-001)")
    s.add_argument("--changes", default=str(DEFAULT_CHANGES))
    s.add_argument("--index", default=str(DEFAULT_INDEX_DIR))
    s.add_argument("--top-k", type=int, default=5)
    s.set_defaults(func=cmd_score)

    d = sub.add_parser("demo", help="Score a few seeded changes (builds index if needed)")
    d.add_argument("--incidents", default=str(DEFAULT_INCIDENTS))
    d.add_argument("--changes", default=str(DEFAULT_CHANGES))
    d.add_argument("--index", default=str(DEFAULT_INDEX_DIR))
    d.add_argument("--model", default=DEFAULT_MODEL_ID)
    d.set_defaults(func=cmd_demo)

    u = sub.add_parser("ui", help="Open the Gradio scoring UI in a browser")
    u.add_argument("--share", action="store_true", help="Create a temporary public Gradio link")
    u.set_defaults(func=cmd_ui)

    sd = sub.add_parser("score-diff", help="Score a Helm / kubectl diff (file or stdin)")
    sd.add_argument("file", nargs="?", help="Path to a .diff (omit to read stdin)")
    sd.add_argument("--index", default=str(DEFAULT_INDEX_DIR))
    sd.add_argument("--top-k", type=int, default=5)
    sd.set_defaults(func=cmd_score_diff)

    ing = sub.add_parser("ingest", help="Append your incidents JSONL (BYO corpus, no training)")
    ing.add_argument("--add", required=True, help="JSONL of new incidents")
    ing.add_argument("--into", default=str(DEFAULT_INCIDENTS))
    ing.set_defaults(func=cmd_ingest)

    ev = sub.add_parser("eval", help="Retrieval Hit@1/Hit@3/MRR (not outage probability)")
    ev.add_argument("--suite", choices=("handwritten", "public", "github", "all"), default="handwritten")
    ev.add_argument("--incidents", default=str(DEFAULT_INCIDENTS))
    ev.add_argument("--changes", default=str(DEFAULT_CHANGES))
    ev.add_argument("--limit", type=int, default=0, help="Cap public suite size (0 = all)")
    ev.set_defaults(func=cmd_eval)

    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "score" and not args.text and not args.change_id:
        parser.error("score requires TEXT or --change-id")
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
