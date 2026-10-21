---
title: ChangeRadar
emoji: 📡
colorFrom: gray
colorTo: yellow
sdk: static
pinned: false
license: mit
short_description: Score K8s/Helm changes against past incidents in the browser
---

# ChangeRadar

Score a Kubernetes / Helm change against past incidents **in the browser**.

Uses Hugging Face **Transformers.js** + `Xenova/all-MiniLM-L6-v2` (same MiniLM family as the local Python CLI). Cosine similarity ranks lookalike outages. This is retrieval, not an outage prediction.

First load downloads the embedding model to your browser (~20MB). After that, scoring is local — no Gradio compute Space required.
