"""Load incident JSONL from the Hugging Face Hub (optional; local files still work)."""

from __future__ import annotations

from pathlib import Path

DEFAULT_HUB_DATASET = "karthikreddyv/changeradar-incidents"


def download_incidents(
    repo_id: str = DEFAULT_HUB_DATASET,
    filename: str = "incidents.jsonl",
) -> Path:
    from huggingface_hub import hf_hub_download

    path = hf_hub_download(repo_id=repo_id, filename=filename, repo_type="dataset")
    return Path(path)
