#!/usr/bin/env python3
"""Rebuild leaderboard.json from evidence/ and community/ receipts.

Rows carry hardware and measurements only: vendor, architecture, OS family,
browser major version, read ceiling, best-GEMV efficiency, E2B projection,
canary verdicts, date, and a link to the verbatim receipt. No usernames.
"""
import json
import glob
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO_BLOB = "https://github.com/Ar5en1c/headroom/blob/main/"


def ua_os(ua):
    if not ua:
        return ""
    if "Android" in ua:
        return "Android"
    if "CrOS" in ua:
        return "ChromeOS"
    if "Windows NT" in ua:
        return "Windows"
    if "Mac OS X" in ua or "Macintosh" in ua:
        return "macOS"
    if "Linux" in ua:
        return "Linux"
    return ""


def ua_browser(ua):
    if not ua:
        return ""
    m = re.search(r"Edg/(\d+)", ua)
    if m:
        return "Edge " + m.group(1)
    m = re.search(r"Chrome/(\d+)", ua)
    if m:
        return "Chrome " + m.group(1)
    return ""


def row_from(path):
    with open(path) as f:
        j = json.load(f)
    if j.get("tool") != "headroom" or j.get("collector") != "webgpu-page":
        return None
    d = j.get("device") or {}
    s = j.get("score") or {}
    if not s.get("readGBps"):
        return None
    pj = (s.get("projections") or [{}])[0]
    rel = os.path.relpath(path, ROOT)
    # canary verdicts are a claim about a NAMED vendor's driver; only rows the
    # author ran (evidence/) may carry one. Community receipts are structure-
    # validated, not silicon-validated, so their canary field is dropped.
    trusted = rel.replace(os.sep, "/").startswith("evidence/")
    return {
        "verified": trusted,
        "vendor": d.get("vendor") or "",
        "arch": d.get("architecture") or "",
        "device": d.get("device") or "",
        "os": ua_os(j.get("ua")),
        "browser": ua_browser(j.get("ua")),
        "readGBps": round(s["readGBps"], 1),
        "bestPct": round(100 * s["efficiency"]) if s.get("efficiency") else None,
        "e2bLo": round(pj["tokLo"]) if pj.get("tokLo") else None,
        "e2bHi": round(pj["tokHi"]) if pj.get("tokHi") else None,
        "derived": bool(pj.get("derived")),
        "canary": (s.get("canary") or "") if trusted else "",
        "canaryV2": (s.get("canaryV2") or "") if trusted else "",
        "ts": (j.get("ts") or "")[:10],
        "receipt": REPO_BLOB + rel.replace(os.sep, "/"),
    }


def main():
    rows = []
    for path in sorted(
        glob.glob(os.path.join(ROOT, "evidence", "*.json"))
        + glob.glob(os.path.join(ROOT, "community", "*.json"))
    ):
        try:
            r = row_from(path)
        except Exception as e:
            print(f"skip {path}: {e}", file=sys.stderr)
            continue
        if r:
            rows.append(r)
    rows.sort(key=lambda r: -r["readGBps"])
    out = {"schema": 1, "rows": rows}
    with open(os.path.join(ROOT, "leaderboard.json"), "w") as f:
        json.dump(out, f, indent=1)
        f.write("\n")
    print(f"leaderboard.json: {len(rows)} rows")


if __name__ == "__main__":
    main()
