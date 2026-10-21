"""Turn Helm / kubectl-style diffs into a short change description for embedding."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

# Signals we care about as SREs — keep this list boring and explicit.
SIGNAL_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("memory", re.compile(r"\bmemory\b", re.I)),
    ("cpu", re.compile(r"\bcpu\b", re.I)),
    ("replicas", re.compile(r"\breplicas\b", re.I)),
    ("maxReplicas", re.compile(r"\bmaxReplicas\b", re.I)),
    ("minReplicas", re.compile(r"\bminReplicas\b", re.I)),
    ("maxUnavailable", re.compile(r"\bmaxUnavailable\b", re.I)),
    ("NetworkPolicy", re.compile(r"\bNetworkPolicy\b", re.I)),
    ("PodDisruptionBudget", re.compile(r"\bPodDisruptionBudget\b|\bminAvailable\b", re.I)),
    ("image", re.compile(r"\bimage:\b", re.I)),
    ("livenessProbe", re.compile(r"\blivenessProbe\b|\btimeoutSeconds\b", re.I)),
    ("ConfigMap", re.compile(r"\bConfigMap\b", re.I)),
    ("tls.secretName", re.compile(r"\bsecretName\b|\btls\b", re.I)),
    ("initContainer", re.compile(r"\binitContainer", re.I)),
    ("ResourceQuota", re.compile(r"\bResourceQuota\b", re.I)),
    ("ServiceMonitor", re.compile(r"\bServiceMonitor\b", re.I)),
]

KIND_RE = re.compile(
    r"\b(Deployment|StatefulSet|DaemonSet|HorizontalPodAutoscaler|Service|"
    r"Ingress|NetworkPolicy|PodDisruptionBudget|ConfigMap|Secret|"
    r"CronJob|Job|ResourceQuota)\b"
)


@dataclass
class DiffSummary:
    title: str
    description: str
    signals: list[str] = field(default_factory=list)
    resources: list[str] = field(default_factory=list)

    def embed_text(self) -> str:
        # Lead with field swaps — those match postmortem language best.
        return "\n".join(
            p
            for p in (self.description, self.title, ", ".join(self.signals))
            if p
        )


def summarize_diff(raw: str) -> DiffSummary:
    lines = raw.splitlines()
    plus = [ln[1:].strip() for ln in lines if ln.startswith("+") and not ln.startswith("+++")]
    minus = [ln[1:].strip() for ln in lines if ln.startswith("-") and not ln.startswith("---")]
    body = "\n".join(plus + minus + lines)

    resources: list[str] = []
    for ln in lines:
        if "has changed" in ln.lower():
            kind_m = KIND_RE.search(ln)
            parts = [p.strip() for p in ln.split(",")]
            if kind_m and len(parts) >= 2:
                name = parts[1].split()[0]
                resources.append(f"{kind_m.group(1)}/{name}")
        elif ln.strip().startswith("kind:"):
            kind_m = KIND_RE.search(ln)
            if kind_m:
                resources.append(kind_m.group(1))
    seen: set[str] = set()
    uniq_resources = []
    for r in resources:
        if r in seen:
            continue
        if "/" not in r and any(x.startswith(r + "/") for x in resources):
            continue
        seen.add(r)
        uniq_resources.append(r)

    signals: list[str] = []
    for name, pat in SIGNAL_PATTERNS:
        if pat.search(body) and name not in signals:
            signals.append(name)

    swaps = _value_swaps(minus, plus)
    swap_txt = "; ".join(swaps) if swaps else "see added/removed lines"
    resource_txt = ", ".join(uniq_resources[:4]) or "cluster manifests"
    signal_txt = ", ".join(signals) if signals else "generic chart/manifest edit"
    title = f"Diff touching {resource_txt} ({signal_txt})"
    description = (
        f"Helm/kubectl diff on {resource_txt}. "
        f"Notable field changes: {swap_txt}. "
        f"Ops signals: {signal_txt}."
    )
    return DiffSummary(
        title=title,
        description=description,
        signals=signals,
        resources=uniq_resources,
    )


def _value_swaps(minus: list[str], plus: list[str]) -> list[str]:
    """Pair simple 'key: value' removals/additions (memory: 1Gi → 256Mi)."""
    def kv(lines: list[str]) -> dict[str, str]:
        out: dict[str, str] = {}
        for ln in lines:
            if ":" not in ln:
                continue
            k, _, v = ln.partition(":")
            k, v = k.strip(), v.strip().strip("\"'")
            if k and v and len(k) < 40:
                out[k] = v
        return out

    before, after = kv(minus), kv(plus)
    swaps = []
    for k in before:
        if k in after and before[k] != after[k]:
            swaps.append(f"{k}: {before[k]} -> {after[k]}")
    return swaps[:8]
