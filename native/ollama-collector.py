#!/usr/bin/env python3
"""Headroom native collector: Ollama.

Measures real decode + prefill tok/s via the local Ollama API and emits a
Headroom receipt JSON. Medians of 3 runs; token accounting comes from Ollama's
own eval_count/eval_duration (not wall-clock guessing).

Usage: python3 ollama-collector.py [model] [host]
       model defaults to gemma3n:e2b, host to http://localhost:11434
"""
import json
import statistics
import sys
import urllib.request
from datetime import datetime, timezone

MODEL = sys.argv[1] if len(sys.argv) > 1 else "gemma3n:e2b"
HOST = (sys.argv[2] if len(sys.argv) > 2 else "http://localhost:11434").rstrip("/")
PROMPT = ("Write a detailed, factual explanation of how memory bandwidth limits "
          "the decoding speed of large language models on consumer hardware.")
RUNS, NUM_PREDICT = 3, 256


def api(path, payload=None):
    req = urllib.request.Request(HOST + path,
                                 data=json.dumps(payload).encode() if payload else None,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=600) as r:
        return json.loads(r.read())


def main():
    tags = api("/api/tags")
    size = next((m.get("size") for m in tags.get("models", [])
                 if m.get("name") == MODEL or m.get("model") == MODEL), None)
    ver = api("/api/version").get("version", "?")

    decode, prefill, receipts = [], [], []
    for i in range(RUNS):
        r = api("/api/generate", {"model": MODEL, "prompt": PROMPT, "stream": False,
                                  "options": {"num_predict": NUM_PREDICT}})
        d = r["eval_count"] / (r["eval_duration"] / 1e9)
        p = (r.get("prompt_eval_count", 0) / (r["prompt_eval_duration"] / 1e9)
             if r.get("prompt_eval_duration") else None)
        decode.append(d)
        if p:
            prefill.append(p)
        receipts.append({"probe": f"generate run {i + 1}",
                         "result": f"{d:.1f} tok/s decode ({r['eval_count']} tokens)",
                         "gate": "ollama eval_count/eval_duration"})

    out = {
        "tool": "headroom", "collector": "ollama", "version": "0.1.0",
        "ts": datetime.now(timezone.utc).isoformat(),
        "device": {"ollama": ver, "model": MODEL, "modelBytes": size},
        "method": {"runs": RUNS, "num_predict": NUM_PREDICT,
                   "timing": "ollama eval_duration medians, warm model",
                   "note": "first run may include load; inspect per-run receipts"},
        "score": {"decode_toks_median": round(statistics.median(decode), 1),
                  "decode_toks_all": [round(x, 1) for x in decode],
                  "prefill_toks_median": round(statistics.median(prefill), 1) if prefill else None},
        "receipts": receipts,
    }
    path = "headroom-receipt-ollama.json"
    with open(path, "w") as f:
        json.dump(out, f, indent=2)
    print(json.dumps(out["score"], indent=2))
    print(f"wrote {path}")


if __name__ == "__main__":
    main()
