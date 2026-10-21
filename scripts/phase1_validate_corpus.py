#!/usr/bin/env python3
"""Phase 1 — validate the Kubernetes/Helm seed corpus (JSONL)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INCIDENTS = ROOT / "data" / "incidents.jsonl"
CHANGES = ROOT / "data" / "changes.jsonl"

INCIDENT_REQUIRED = {"id", "title", "namespace", "date", "summary", "root_cause", "tags"}
CHANGE_REQUIRED = {"id", "title", "description"}


def load_jsonl(path: Path) -> list[dict]:
    rows: list[dict] = []
    with path.open() as f:
        for i, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as e:
                raise SystemExit(f"{path}:{i}: invalid JSON — {e}") from e
    return rows


def check_required(rows: list[dict], required: set[str], label: str) -> None:
    ids: set[str] = set()
    for row in rows:
        missing = required - row.keys()
        if missing:
            raise SystemExit(f"{label} {row.get('id')!r} missing fields: {sorted(missing)}")
        if row["id"] in ids:
            raise SystemExit(f"{label} duplicate id: {row['id']}")
        ids.add(row["id"])


def main() -> int:
    incidents = load_jsonl(INCIDENTS)
    changes = load_jsonl(CHANGES)
    check_required(incidents, INCIDENT_REQUIRED, "incident")
    check_required(changes, CHANGE_REQUIRED, "change")

    print(f"incidents: {len(incidents)}  ({INCIDENTS.relative_to(ROOT)})")
    print(f"changes:   {len(changes)}  ({CHANGES.relative_to(ROOT)})")
    print("\nSample incident tags:")
    for row in incidents[:3]:
        print(f"  {row['id']}: {', '.join(row['tags'])}")
    print("\nPhase 1 corpus OK.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
