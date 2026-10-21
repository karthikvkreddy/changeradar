"""Gradio UI — same scoring path as the CLI, in a browser."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import gradio as gr

from changeradar.cli import DEFAULT_CHANGES, DEFAULT_INCIDENTS, DEFAULT_INDEX_DIR
from changeradar.corpus import change_embed_text, load_jsonl
from changeradar.embedder import DEFAULT_MODEL_ID
from changeradar.index import IncidentIndex, build_index
from changeradar.risk import risk_band

EXAMPLES = [
    "Helm values.yaml: resources.limits.memory 1Gi -> 256Mi for checkout-api Deployment to save cost in prod.",
    "Increase search-api HorizontalPodAutoscaler maxReplicas from 10 to 200 ahead of flash sale.",
    "docs-site Helm chart appVersion bump for typo fixes in static markdown; no probe, HPA, or network changes.",
    "Enable Istio sidecar injection on latency-critical payments pods.",
]


@lru_cache(maxsize=1)
def get_index() -> IncidentIndex:
    if (DEFAULT_INDEX_DIR / "meta.json").exists():
        return IncidentIndex.load(DEFAULT_INDEX_DIR)
    index = build_index(DEFAULT_INCIDENTS, model_id=DEFAULT_MODEL_ID)
    index.save(DEFAULT_INDEX_DIR)
    return index


def example_labels() -> list[str]:
    rows = load_jsonl(DEFAULT_CHANGES)
    return [f"{c['id']} — {c['title']}" for c in rows]


def _change_text_by_label(label: str | None) -> str:
    if not label:
        return ""
    cid = label.split(" — ", 1)[0]
    for row in load_jsonl(DEFAULT_CHANGES):
        if row["id"] == cid:
            return change_embed_text(row)
    return ""


def score_change(text: str, top_k: int) -> str:
    query = (text or "").strip()
    if not query:
        return "Paste a Helm / Kubernetes change description (or pick an example)."

    hits = get_index().search(query, top_k=int(top_k))
    if not hits:
        return "No incidents in the index."

    overall = risk_band(hits[0].score)
    lines = [
        f"**Overall risk (top match): `{overall}`** — cosine `{hits[0].score:.3f}`",
        "",
        "This is *lookalike retrieval*, not a prediction that the change will page.",
        "",
        "| Rank | Score | Band | Incident | Namespace | Tags |",
        "| ---: | ----: | :--- | :------- | :-------- | :--- |",
    ]
    details = []
    for i, hit in enumerate(hits, 1):
        inc = hit.incident
        tags = ", ".join(inc.get("tags") or [])
        lines.append(
            f"| {i} | {hit.score:.3f} | {risk_band(hit.score)} | "
            f"`{inc['id']}` {inc['title']} | {inc.get('namespace', '?')} | {tags} |"
        )
        details.append(
            f"### {i}. {inc['title']} (`{inc['id']}`)\n"
            f"- **Score:** {hit.score:.3f} ({risk_band(hit.score)})\n"
            f"- **Summary:** {inc.get('summary', '')}\n"
            f"- **Root cause:** {inc.get('root_cause', '')}\n"
            f"- **Blast radius:** {inc.get('blast_radius', '')}"
        )
    return "\n".join(lines) + "\n\n" + "\n\n".join(details)


def load_example(label: str | None, current: str) -> str:
    filled = _change_text_by_label(label)
    return filled or current


def build_app() -> gr.Blocks:
    with gr.Blocks(title="ChangeRadar") as demo:
        gr.Markdown(
            """
# ChangeRadar
Score a Kubernetes / Helm change against past incidents using Hugging Face embeddings.

Paste a change (or pick a seeded example). The app embeds your text and ranks
lookalike outages by cosine similarity.
            """
        )
        with gr.Row():
            with gr.Column():
                picker = gr.Dropdown(
                    choices=example_labels(),
                    label="Seeded example (optional)",
                    value=None,
                )
                text = gr.Textbox(
                    lines=8,
                    label="Proposed change",
                    placeholder="Describe the Helm values / manifest change…",
                )
                top_k = gr.Slider(1, 8, value=5, step=1, label="How many lookalikes")
                btn = gr.Button("Score change", variant="primary")
            with gr.Column():
                out = gr.Markdown()

        picker.change(load_example, inputs=[picker, text], outputs=text)
        btn.click(score_change, inputs=[text, top_k], outputs=out)
        gr.Examples(examples=[[e, 5] for e in EXAMPLES], inputs=[text, top_k])
        gr.Markdown(
            f"Model: `{DEFAULT_MODEL_ID}` · corpus: `{Path(DEFAULT_INCIDENTS).name}`"
        )
    return demo


def launch(share: bool = False) -> None:
    get_index()  # fail fast / build once at startup
    build_app().launch(share=share, inbrowser=False)


if __name__ == "__main__":
    launch()
