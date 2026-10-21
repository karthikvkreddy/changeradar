from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open() as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def incident_embed_text(incident: dict[str, Any]) -> str:
    """Text we embed for each past outage (search corpus)."""
    tags = ", ".join(incident.get("tags") or [])
    parts = [
        incident.get("title", ""),
        incident.get("summary", ""),
        f"Root cause: {incident.get('root_cause', '')}",
        f"Symptoms: {incident.get('symptoms', '')}",
        f"Blast radius: {incident.get('blast_radius', '')}",
        f"Tags: {tags}",
    ]
    return "\n".join(p for p in parts if p)


INCIDENT_REQUIRED = {"id", "title", "summary", "root_cause", "tags"}


def validate_incident(row: dict[str, Any]) -> list[str]:
    return sorted(INCIDENT_REQUIRED - row.keys())


def append_incidents(dest: Path, new_rows: list[dict[str, Any]]) -> int:
    """Append unique-id incidents. Corporate BYO path — no model training."""
    existing = load_jsonl(dest) if dest.exists() else []
    seen = {r["id"] for r in existing}
    added = 0
    dest.parent.mkdir(parents=True, exist_ok=True)
    with dest.open("a") as f:
        for row in new_rows:
            missing = validate_incident(row)
            if missing:
                raise ValueError(f"{row.get('id')!r} missing fields: {missing}")
            if row["id"] in seen:
                continue
            f.write(json.dumps(row) + "\n")
            seen.add(row["id"])
            added += 1
    return added


def change_embed_text(change: dict[str, Any]) -> str:
    """Text we embed for a proposed change (query)."""
    return f"{change.get('title', '')}\n{change.get('description', '')}".strip()
