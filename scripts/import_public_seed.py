#!/usr/bin/env python3
"""
Build a ~1.5k public seed from published case labels.

Sources:
  - phamquiluan/RCAEval (735 Chaos/fault-injection cases, MIT)
  - LLM4Ops/Cloud-OpsBench (754 K8s incident snapshots, MIT)
  - EvoTestOps/AnoMod (24 Table-2 cases, MIT on GitHub) — labels only

We do NOT copy telemetry (no AnoMod.zip / Zenodo dump). We derive
incident + change text from published labels. Gold pairs are the same
case on both sides — retrieval labels, not "this change will page in
production with 90% probability."
"""

from __future__ import annotations

import json
from pathlib import Path

from huggingface_hub import hf_hub_download

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "public"

# Chaos / fault-injection → Helm-shaped change language (same meaning family).
RCA_CHANGE = {
    "cpu": "Helm values: raise or pin CPU limits/requests on {svc} Deployment; cluster showed CPU stress / throttling on that service.",
    "mem": "Helm values: cut resources.limits.memory on {svc} Deployment (or leave it below working set); pods risk OOMKilled.",
    "disk": "Helm / PVC: shrink storage or add disk IO pressure on {svc}; volume fill or disk latency on the workload.",
    "delay": "Mesh / NetworkPolicy / annotation change added extra latency on {svc} RPC path.",
    "loss": "NetworkPolicy or CNI change dropped packets to/from {svc}; error rate and retries climbed.",
    "socket": "ulimit / fd / socket exhaustion on {svc} after a chart or runtime limit change.",
}

RCA_SYMPTOMS = {
    "cpu": "CPU throttling, high p99, pod saturation",
    "mem": "OOMKilled, memory working-set at limit, restarts",
    "disk": "disk full / IO wait, PVC pressure",
    "delay": "elevated RPC latency, timeout errors",
    "loss": "packet loss, connection resets, 5xx",
    "socket": "too many open files, connect failures",
}

# AnoMod Table 2 (12 types × SocialNetwork + TrainTicket = 24).
# Targets come from EvoTestOps/AnoMod chaos YAMLs + SN README injection notes.
# Do not download https://zenodo.org/records/18342898 (AnoMod.zip ~202MB).
ANOMOD_CHANGE = {
    "cpu_contention": (
        "Helm values: raise or pin CPU limits/requests on {svc} Deployment; "
        "cluster showed CPU contention / throttling on that service."
    ),
    "network_degradation": (
        "Mesh / NetworkPolicy / annotation change dropped packets or added latency "
        "on {svc}; error rate and retries climbed."
    ),
    "disk_io_stress": (
        "Helm / PVC: shrink storage or add disk IO pressure on {svc}; "
        "volume fill or disk latency on the workload."
    ),
    "instance_failure": (
        "Replica / probe / disruptionBudget change so {svc} pods are killed or "
        "cannot stay Ready; traffic sees instance outages."
    ),
    "communication_failure": (
        "Service / DNS / CoreDNS change so {svc} cannot resolve a dependency; "
        "service discovery fails on the RPC path."
    ),
    "response_failure": (
        "Ingress / HTTP filter / abort annotation on {svc} so callers get "
        "incorrect or aborted responses (5xx) before business logic."
    ),
    "cache_pressure": (
        "Memory / cache-size Helm values on {svc} evict hot entries; "
        "repeated DB hits and cache misses."
    ),
    "connection_pool": (
        "JDBC / connection-pool limit change plus extra DB latency on {svc}; "
        "pool saturates and new queries wait or fail."
    ),
    "transaction_issues": (
        "DB timeout / transaction Helm or runtime change on {svc}; "
        "long-running SQL exceeds the timeout and rolls back."
    ),
    "method_return": (
        "New image/tag for {svc} that forces a Java method to return a "
        "predefined wrong value (logic defect)."
    ),
    "method_delay": (
        "New image/tag or runtime hook on {svc} that adds artificial delay "
        "inside a specific Java method."
    ),
    "inject_exception": (
        "New image/tag for {svc} that throws an injected exception from a "
        "targeted Java method."
    ),
}

ANOMOD_SYMPTOMS = {
    "cpu_contention": "CPU throttling, high p99, pod saturation",
    "network_degradation": "packet loss, elevated RPC latency, connection resets, 5xx",
    "disk_io_stress": "disk full / IO wait, PVC pressure",
    "instance_failure": "CrashLoopBackOff / pod kills, readiness flaps, 502/503",
    "communication_failure": "DNS lookup failures, unknown host, dependency timeouts",
    "response_failure": "HTTP abort, unexpected 5xx before business logic",
    "cache_pressure": "cache misses, memory pressure, repeated DB hits",
    "connection_pool": "pool exhausted, checkout timeout, queued DB connections",
    "transaction_issues": "SQL timeout, rolled-back transactions, lock wait",
    "method_return": "wrong business result, silent logic defect",
    "method_delay": "method-level latency spike, downstream timeouts",
    "inject_exception": "uncaught exception, 500s from a specific method",
}

# Paper Table 2 × two systems. YAML names are TT Chaos Mesh files when they exist.
ANOMOD_CASES = [
    # TrainTicket — chaos-experiments/*.yaml
    {
        "sys": "TrainTicket",
        "ns": "default",
        "slug": "tt-cpu_contention",
        "level": "performance",
        "anomaly": "cpu_contention",
        "svc": "ts-preserve-service",
        "label": "CPU Contention",
        "yaml": "Lv_P_CPU_preserve.yaml",
        "detail": "Chaos Mesh StressChaos: 2 CPU workers at 80% on ts-preserve-service.",
    },
    {
        "sys": "TrainTicket",
        "ns": "default",
        "slug": "tt-network_degradation",
        "level": "performance",
        "anomaly": "network_degradation",
        "svc": "ts-preserve-service",
        "label": "Network Performance Degradation",
        "yaml": "Lv_P_NETLOSS_preserve.yaml",
        "detail": "Chaos Mesh NetworkChaos: 90% packet loss on ts-preserve-service.",
    },
    {
        "sys": "TrainTicket",
        "ns": "default",
        "slug": "tt-disk_io_stress",
        "level": "performance",
        "anomaly": "disk_io_stress",
        "svc": "ts-preserve-service",
        "label": "Disk I/O Stress",
        "yaml": "Lv_P_DISKIO_preserve.yaml",
        "detail": "Chaos Mesh StressChaos iomix on ts-preserve-service pods.",
    },
    {
        "sys": "TrainTicket",
        "ns": "default",
        "slug": "tt-instance_failure",
        "level": "service",
        "anomaly": "instance_failure",
        "svc": "ts-gateway-service",
        "label": "Service Instance Failure",
        "yaml": "Lv_S_KILLPOD_gateway.yaml",
        "detail": "Scheduled PodChaos pod-kill of ts-gateway-service every 3s.",
    },
    {
        "sys": "TrainTicket",
        "ns": "default",
        "slug": "tt-communication_failure",
        "level": "service",
        "anomaly": "communication_failure",
        "svc": "ts-preserve-service",
        "label": "Service Communication Failure",
        "yaml": "Lv_S_DNSFAIL_preserve_no_order.yaml",
        "detail": "DNSChaos: ts-preserve-service cannot resolve ts-order-service.",
    },
    {
        "sys": "TrainTicket",
        "ns": "default",
        "slug": "tt-response_failure",
        "level": "service",
        "anomaly": "response_failure",
        "svc": "ts-preserve-service",
        "label": "Service Response Failure",
        "yaml": "Lv_S_HTTPABORT_preserve.yaml",
        "detail": "HTTPChaos abort + 503 on POST /api/v1/preserveservice/* (70% of requests).",
    },
    {
        "sys": "TrainTicket",
        "ns": "default",
        "slug": "tt-cache_pressure",
        "level": "database",
        "anomaly": "cache_pressure",
        "svc": "tsdb-mysql",
        "label": "Cache Pressure",
        "yaml": "Lv_D_cachelimit.yaml",
        "detail": "StressChaos memory 85% on tsdb-mysql to evict cache and force DB hits.",
    },
    {
        "sys": "TrainTicket",
        "ns": "default",
        "slug": "tt-connection_pool",
        "level": "database",
        "anomaly": "connection_pool",
        "svc": "tsdb-mysql",
        "label": "Connection Pool Exhaustion",
        "yaml": "Lv_D_CONNECTION_POOL_exhaustion.yaml",
        "detail": "8s delay from ts-order/preserve/user to tsdb-mysql so JDBC pools saturate.",
    },
    {
        "sys": "TrainTicket",
        "ns": "default",
        "slug": "tt-transaction_issues",
        "level": "database",
        "anomaly": "transaction_issues",
        "svc": "tsdb-mysql",
        "label": "Transaction Issues",
        "yaml": "Lv_D_TRANSACTION_timeout.yaml",
        "detail": "15s delay on tsdb-mysql responses so SQL transactions time out.",
    },
    {
        "sys": "TrainTicket",
        "ns": "default",
        "slug": "tt-method_return",
        "level": "code",
        "anomaly": "method_return",
        "svc": "ts-preserve-service",
        "label": "Manipulating Method Return Values",
        "yaml": "",
        "detail": "ChaosBlade JVM sandbox forces a Java method on ts-preserve-service to return a predefined value.",
    },
    {
        "sys": "TrainTicket",
        "ns": "default",
        "slug": "tt-method_delay",
        "level": "code",
        "anomaly": "method_delay",
        "svc": "ts-order-service",
        "label": "Method Execution Delay",
        "yaml": "",
        "detail": "ChaosBlade adds artificial delay inside a Java method on ts-order-service.",
    },
    {
        "sys": "TrainTicket",
        "ns": "default",
        "slug": "tt-inject_exception",
        "level": "code",
        "anomaly": "inject_exception",
        "svc": "ts-preserve-service",
        "label": "Injecting Exceptions",
        "yaml": "",
        "detail": "ChaosBlade throws a specified exception from a targeted Java method on ts-preserve-service.",
    },
    # SocialNetwork — same Table 2 types; SN README: ChaosBlade + container restarts
    # (CPU, network, disk, Redis cache, service kills). No Chaos Mesh YAML tree.
    {
        "sys": "SocialNetwork",
        "ns": "social-network",
        "slug": "sn-cpu_contention",
        "level": "performance",
        "anomaly": "cpu_contention",
        "svc": "compose-post-service",
        "label": "CPU Contention",
        "yaml": "",
        "detail": "ChaosBlade CPU stress on compose-post-service (write-path hub).",
    },
    {
        "sys": "SocialNetwork",
        "ns": "social-network",
        "slug": "sn-network_degradation",
        "level": "performance",
        "anomaly": "network_degradation",
        "svc": "nginx-web-server",
        "label": "Network Performance Degradation",
        "yaml": "",
        "detail": "ChaosBlade network loss/delay on nginx-web-server ingress.",
    },
    {
        "sys": "SocialNetwork",
        "ns": "social-network",
        "slug": "sn-disk_io_stress",
        "level": "performance",
        "anomaly": "disk_io_stress",
        "svc": "media-service",
        "label": "Disk I/O Stress",
        "yaml": "",
        "detail": "Disk I/O pressure on media-service storage path.",
    },
    {
        "sys": "SocialNetwork",
        "ns": "social-network",
        "slug": "sn-instance_failure",
        "level": "service",
        "anomaly": "instance_failure",
        "svc": "nginx-web-server",
        "label": "Service Instance Failure",
        "yaml": "",
        "detail": "Targeted container restart / kill of nginx-web-server.",
    },
    {
        "sys": "SocialNetwork",
        "ns": "social-network",
        "slug": "sn-communication_failure",
        "level": "service",
        "anomaly": "communication_failure",
        "svc": "compose-post-service",
        "label": "Service Communication Failure",
        "yaml": "",
        "detail": "compose-post-service cannot reach social-graph / user-timeline dependencies.",
    },
    {
        "sys": "SocialNetwork",
        "ns": "social-network",
        "slug": "sn-response_failure",
        "level": "service",
        "anomaly": "response_failure",
        "svc": "home-timeline-service",
        "label": "Service Response Failure",
        "yaml": "",
        "detail": "home-timeline-service returns aborted or incorrect HTTP responses.",
    },
    {
        "sys": "SocialNetwork",
        "ns": "social-network",
        "slug": "sn-cache_pressure",
        "level": "database",
        "anomaly": "cache_pressure",
        "svc": "home-timeline-redis",
        "label": "Cache Pressure",
        "yaml": "",
        "detail": "Redis cache constraint on home-timeline-redis; repeated backend hits.",
    },
    {
        "sys": "SocialNetwork",
        "ns": "social-network",
        "slug": "sn-connection_pool",
        "level": "database",
        "anomaly": "connection_pool",
        "svc": "post-storage-mongodb",
        "label": "Connection Pool Exhaustion",
        "yaml": "",
        "detail": "MongoDB connection pool on post-storage-mongodb saturates under extra latency.",
    },
    {
        "sys": "SocialNetwork",
        "ns": "social-network",
        "slug": "sn-transaction_issues",
        "level": "database",
        "anomaly": "transaction_issues",
        "svc": "post-storage-mongodb",
        "label": "Transaction Issues",
        "yaml": "",
        "detail": "Write-path transaction / timeout faults on post-storage-mongodb.",
    },
    {
        "sys": "SocialNetwork",
        "ns": "social-network",
        "slug": "sn-method_return",
        "level": "code",
        "anomaly": "method_return",
        "svc": "compose-post-service",
        "label": "Manipulating Method Return Values",
        "yaml": "",
        "detail": "ChaosBlade forces a method on compose-post-service to return a predefined value.",
    },
    {
        "sys": "SocialNetwork",
        "ns": "social-network",
        "slug": "sn-method_delay",
        "level": "code",
        "anomaly": "method_delay",
        "svc": "user-timeline-service",
        "label": "Method Execution Delay",
        "yaml": "",
        "detail": "ChaosBlade adds method-level delay on user-timeline-service.",
    },
    {
        "sys": "SocialNetwork",
        "ns": "social-network",
        "slug": "sn-inject_exception",
        "level": "code",
        "anomaly": "inject_exception",
        "svc": "compose-post-service",
        "label": "Injecting Exceptions",
        "yaml": "",
        "detail": "ChaosBlade injects an exception from a targeted method on compose-post-service.",
    },
]


# Cloud-OpsBench taxonomy → change phrasing.
COB_CHANGE = {
    "admission": "Admission / RBAC / ServiceAccount change in the Helm chart for {obj}.",
    "scheduling": "Scheduling change (requests, affinity, taints) for {obj} so pods cannot place as before.",
    "runtime": "Runtime / container spec change for {obj} (command, probes, or securityContext).",
    "codedefect": "New image/tag for {obj} that includes a code-level defect.",
    "service": "Service / selector / ports change affecting {obj} traffic.",
    "startup": "Startup / initContainer / config change so {obj} cannot become Ready.",
    "performance": "Resource or concurrency change that overloaded {obj}.",
    "infrastructure": "Node / CNI / cluster infra change impacting {obj}.",
}


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def from_rcaeval() -> tuple[list[dict], list[dict], list[dict]]:
    import pandas as pd

    parquet = hf_hub_download("phamquiluan/RCAEval", "cases.parquet", repo_type="dataset")
    df = pd.read_parquet(parquet)
    incidents, changes, gold = [], [], []
    for row in df.to_dict(orient="records"):
        iid = f"rca-{row['case']}"
        cid = f"chg-{iid}"
        fault = str(row.get("fault") or "unknown")
        svc = str(row.get("root_cause_service") or "unknown")
        desc = str(row.get("fault_description") or fault)
        system = str(row.get("system_name") or row.get("system") or "microservice")
        change_tpl = RCA_CHANGE.get(fault, "Change on {svc} corresponding to injected fault: " + desc)
        change_txt = change_tpl.format(svc=svc)
        incidents.append(
            {
                "id": iid,
                "title": f"{svc}-{fault}-in-{system.replace(' ', '-').lower()}",
                "namespace": str(row.get("system") or "default"),
                "date": "2023-05-01",
                "summary": (
                    f"Injected {desc} on {svc} in {system} ({row.get('dataset')}, "
                    f"rep {row.get('repetition')}). Duration ~{row.get('duration_minutes')} min."
                ),
                "symptoms": RCA_SYMPTOMS.get(fault, desc),
                "root_cause": f"Labeled injected fault '{fault}' ({desc}) on service {svc}.",
                "blast_radius": svc,
                "tags": ["rcaeval", "k8s", fault, svc, system.lower().replace(" ", "-")],
                "source": "phamquiluan/RCAEval",
            }
        )
        changes.append(
            {
                "id": cid,
                "kind": "derived_from_label",
                "service": svc,
                "title": f"{fault} change on {svc}",
                "description": change_txt,
                "source": "phamquiluan/RCAEval",
            }
        )
        gold.append(
            {
                "change_id": cid,
                "incident_id": iid,
                "source": "phamquiluan/RCAEval",
                "pair_type": "same_case_label",
            }
        )
    return incidents, changes, gold


def from_cloud_opsbench() -> tuple[list[dict], list[dict], list[dict]]:
    path = hf_hub_download("LLM4Ops/Cloud-OpsBench", "index.jsonl", repo_type="dataset")
    incidents, changes, gold = [], [], []
    with Path(path).open() as f:
        for line in f:
            row = json.loads(line)
            key = row["case_key"].replace("/", "-")
            iid = f"cob-{key}"
            cid = f"chg-{iid}"
            cat = str(row.get("category") or "runtime")
            obj = str(row.get("fault_object") or "workload")
            rc = str(row.get("root_cause") or cat).replace("_", " ")
            query = str(row.get("query") or rc)
            change_txt = COB_CHANGE.get(cat, "Kubernetes change on {obj}.").format(obj=obj)
            change_txt += f" Ground-truth root cause label: {rc}."
            incidents.append(
                {
                    "id": iid,
                    "title": f"{cat}-{rc.replace(' ', '-')}",
                    "namespace": str(row.get("namespace") or "default"),
                    "date": "2026-01-01",
                    "summary": f"{query} System={row.get('system')} object={obj} taxonomy={row.get('fault_taxonomy')}.",
                    "symptoms": query,
                    "root_cause": rc,
                    "blast_radius": obj,
                    "tags": ["cloud-opsbench", "k8s", cat, rc.split()[0]],
                    "source": "LLM4Ops/Cloud-OpsBench",
                }
            )
            changes.append(
                {
                    "id": cid,
                    "kind": "derived_from_label",
                    "service": obj,
                    "title": f"{cat} change: {rc}",
                    "description": change_txt,
                    "source": "LLM4Ops/Cloud-OpsBench",
                }
            )
            gold.append(
                {
                    "change_id": cid,
                    "incident_id": iid,
                    "source": "LLM4Ops/Cloud-OpsBench",
                    "pair_type": "same_case_label",
                }
            )
    return incidents, changes, gold


def from_anomod() -> tuple[list[dict], list[dict], list[dict]]:
    """Table 2 labels only. Never fetches AnoMod.zip telemetry."""
    incidents, changes, gold = [], [], []
    for case in ANOMOD_CASES:
        iid = f"anom-{case['slug']}"
        cid = f"chg-{iid}"
        svc = case["svc"]
        anomaly = case["anomaly"]
        yaml_bit = f" Experiment file: {case['yaml']}." if case["yaml"] else ""
        incidents.append(
            {
                "id": iid,
                "title": f"{svc}-{anomaly}-in-{case['sys'].lower()}",
                "namespace": case["ns"],
                "date": "2026-01-01",
                "summary": (
                    f"AnoMod {case['level']}-level '{case['label']}' on {svc} "
                    f"in {case['sys']}.{yaml_bit} {case['detail']}"
                ),
                "symptoms": ANOMOD_SYMPTOMS[anomaly],
                "root_cause": (
                    f"Labeled injected fault '{anomaly}' ({case['label']}) on {svc}."
                ),
                "blast_radius": svc,
                "tags": [
                    "anomod",
                    "k8s",
                    case["level"],
                    anomaly,
                    svc,
                    case["sys"].lower(),
                ],
                "source": "EvoTestOps/AnoMod",
                "source_license": "MIT",
            }
        )
        changes.append(
            {
                "id": cid,
                "kind": "derived_from_label",
                "service": svc,
                "title": f"{anomaly} change on {svc}",
                "description": ANOMOD_CHANGE[anomaly].format(svc=svc)
                + f" AnoMod {case['sys']} case: {case['detail']}",
                "source": "EvoTestOps/AnoMod",
                "source_license": "MIT",
            }
        )
        gold.append(
            {
                "change_id": cid,
                "incident_id": iid,
                "source": "EvoTestOps/AnoMod",
                "source_license": "MIT",
                "pair_type": "same_case_label",
            }
        )
    return incidents, changes, gold


def _reuse_existing_mit_rows() -> tuple[list[dict], list[dict], list[dict]]:
    """Keep RCAEval + Cloud-OpsBench rows if Hub download is unavailable."""
    incidents, changes, gold = [], [], []
    for name, bucket in (
        ("incidents.jsonl", incidents),
        ("changes.jsonl", changes),
        ("gold_pairs.jsonl", gold),
    ):
        path = OUT / name
        if not path.exists():
            raise FileNotFoundError(path)
        for line in path.read_text().splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            src = str(row.get("source") or "")
            if src.startswith("EvoTestOps/AnoMod") or str(row.get("id", "")).startswith(
                ("anom-", "chg-anom-")
            ):
                continue
            if str(row.get("change_id", "")).startswith("chg-anom-"):
                continue
            bucket.append(row)
    if not incidents:
        raise RuntimeError("existing public seed has no MIT-derived rows")
    return incidents, changes, gold


def main() -> int:
    try:
        a, b, c = from_rcaeval()
        d, e, f = from_cloud_opsbench()
        mit_inc, mit_chg, mit_gold = a + d, b + e, c + f
    except Exception as exc:  # Hub cache / network
        print(f"Hub download failed ({exc}); reusing existing RCAEval/Cloud-OpsBench rows")
        mit_inc, mit_chg, mit_gold = _reuse_existing_mit_rows()
    g, h, i = from_anomod()
    incidents = mit_inc + g
    changes = mit_chg + h
    gold = mit_gold + i
    _write_jsonl(OUT / "incidents.jsonl", incidents)
    _write_jsonl(OUT / "changes.jsonl", changes)
    _write_jsonl(OUT / "gold_pairs.jsonl", gold)
    print(f"incidents: {len(incidents)}")
    print(f"changes:   {len(changes)}")
    print(f"gold pairs:{len(gold)}")
    print(f"wrote {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
