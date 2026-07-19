# Headroom native collectors

The browser page measures the **device ceiling** (what the hardware can do).
Native collectors measure **real engines** (what your stack actually does) and
emit the same receipt JSON, so every number — browser or native — lands on the
same card and the gap between them is visible instead of vibes.

```
one receipt schema  ·  many collectors  ·  one card
```

## Receipt schema (shared)

Every collector emits:

```json
{
  "tool": "headroom",
  "collector": "webgpu-page | ollama | llamacpp | cuda-ceiling | ...",
  "version": "0.1.0",
  "ts": "ISO-8601",
  "device": { "...": "adapter/GPU identity" },
  "method": { "...": "how numbers were produced — always present" },
  "score": { "...": "collector-specific measurements" },
  "receipts": [ { "probe": "...", "result": "...", "gate": "..." } ]
}
```

Rules carry over from the page: medians not bests, method recorded with every
number, and no number without its provenance.

## Collectors

| collector | measures | status |
|---|---|---|
| `webgpu-page` | device bandwidth ceiling, GEMV ladder, subgroup canary | ✅ (the page itself) |
| `ollama` | real decode + prefill tok/s via the local Ollama API | ✅ `ollama-collector.py` / `.ps1` |
| `llamacpp` | `llama-bench -o json` decode/prefill, mapped to receipts | planned (thin mapper) |
| `cuda-ceiling` | direct-GPU ceiling + GEMV ladder, no browser in the way | planned — the [cuda-decode-ceiling](https://github.com/Ar5en1c) study's binaries emit JSONL already |
| browser engine tier | real in-browser engines (transformers.js, WebLLM/MLC, ONNX Runtime Web) as an opt-in big-download run on the page | planned |

## Ollama

Ollama must be running (`ollama serve`, default port 11434) with the model pulled.

```bash
# macOS / Linux
python3 ollama-collector.py gemma3n:e2b

# Windows (no Python needed)
powershell -ExecutionPolicy Bypass -File ollama-collector.ps1 gemma3n:e2b
```

Runs 3 timed generations (median reported), reads `eval_count/eval_duration`
from the API (Ollama's own token accounting, not wall-clock guessing), and
writes `headroom-receipt-ollama.json`.

Compare the decode number against the page's ceiling for the same machine:
the ratio is your engine's efficiency, and the receipt records both sides.
