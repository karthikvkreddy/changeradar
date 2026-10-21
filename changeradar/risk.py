"""Heuristic cosine bands for MiniLM on the demo corpus — not outage probability."""

HIGH = 0.55
MED = 0.40


def risk_band(score: float) -> str:
    if score >= HIGH:
        return "HIGH"
    if score >= MED:
        return "MED"
    return "LOW"
