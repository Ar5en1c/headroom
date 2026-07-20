#!/usr/bin/env python3
"""Validate a leaderboard submission (GitHub issue body) and store the receipt.

Reads ISSUE_BODY and ISSUE_NUMBER from the environment. Extracts the first
fenced JSON block (or the whole body as JSON), validates structure and
plausibility, strips unknown top-level keys, and writes the receipt to
community/<vendor>-<arch>-<hash>.json. Exits nonzero on validation failure so
the workflow can comment with instructions.

This validates structure, not silicon: the board's trust model is that every
row links to its verbatim receipt and its public submission issue.
"""
import hashlib
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KEEP_KEYS = [
    "tool", "collector", "version", "ts", "ua",
    "device", "shapes", "method", "score", "receipts",
]


def fail(msg):
    print(f"VALIDATION FAILED: {msg}")
    sys.exit(1)


def main():
    body = os.environ.get("ISSUE_BODY") or ""
    if len(body) > 200_000:
        fail("issue body too large")

    m = re.search(r"```(?:json)?\s*\n(.*?)\n```", body, re.S)
    raw = m.group(1) if m else body
    start = raw.find("{")
    if start < 0:
        fail("no JSON object found in the issue body")
    try:
        j = json.loads(raw[start:raw.rfind("}") + 1])
    except Exception as e:
        fail(f"could not parse JSON: {e}")

    if j.get("tool") != "headroom":
        fail("tool must be 'headroom'")
    if j.get("collector") != "webgpu-page":
        fail("v1 board accepts collector 'webgpu-page' receipts only")
    if not isinstance(j.get("version"), str) or len(j["version"]) > 20:
        fail("missing or bad version")
    if not re.match(r"^\d{4}-\d{2}-\d{2}T", str(j.get("ts") or "")):
        fail("ts must be an ISO timestamp")

    d = j.get("device") or {}
    if not isinstance(d.get("vendor"), str) or not d["vendor"]:
        fail("device.vendor required")

    s = j.get("score") or {}
    read = s.get("readGBps")
    if not isinstance(read, (int, float)) or not (1 <= read <= 8000):
        fail("score.readGBps out of plausible range (1..8000)")
    eff = s.get("efficiency")
    if not isinstance(eff, (int, float)) or not (0.05 <= eff <= 1.15):
        fail("score.efficiency out of plausible range (0.05..1.15)")
    if not (s.get("projections") or []):
        fail("score.projections required")

    receipts = j.get("receipts") or []
    if not isinstance(receipts, list) or len(receipts) < 5:
        fail("receipts list missing or too short")
    probes = " | ".join(str(r.get("probe", "")) for r in receipts)
    gates = " | ".join(str(r.get("gate", "")) for r in receipts)
    if "fp64 reference" not in probes:
        fail("receipts must include the fp64 reference probe")
    if "PASS (rel" not in gates:
        fail("receipts must include FP64-gated kernel results")

    clean = {k: j[k] for k in KEEP_KEYS if k in j}
    blob = json.dumps(clean, sort_keys=True).encode()
    if len(blob) > 100_000:
        fail("receipt too large")
    h = hashlib.sha256(blob).hexdigest()[:10]
    slug = re.sub(r"[^a-z0-9]+", "-", (d.get("vendor", "") + "-" + d.get("architecture", "")).lower()).strip("-") or "device"
    os.makedirs(os.path.join(ROOT, "community"), exist_ok=True)
    path = os.path.join(ROOT, "community", f"{slug}-{h}.json")
    if os.path.exists(path):
        print(f"duplicate receipt, already stored: {os.path.basename(path)}")
        return
    with open(path, "w") as f:
        json.dump(clean, f, indent=1)
        f.write("\n")
    print(f"stored {os.path.relpath(path, ROOT)} (read {read} GB/s, {d.get('vendor')} {d.get('architecture', '')})")


if __name__ == "__main__":
    main()
