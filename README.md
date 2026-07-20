# HEADROOM_

**How fast is your machine, really?** A 30-second, in-browser WebGPU test of your
device's true memory-bandwidth ceiling for local AI (the number that decides your
tokens/s), plus a check for the driver bug that makes some in-browser LLM engines
silently produce garbage.

No model download (the probes use deterministic synthetic weights). No account,
no ads, no telemetry. One outbound request: a ~0.4 MB public-metadata fetch from
Hugging Face to derive exact bytes per token, with no run data attached. Your
numbers leave the browser only when you share them.

## Why this exists

Batch-1 LLM decode is memory-bound: every generated token streams the resident
weights through the GPU once, so your ceiling is simply

```
tokens/s ceiling = memory bandwidth / model bytes
```

Vendors quote TOPS, which predicts nothing about decode. Headroom measures the
bandwidth three independent ways, then runs a from-scratch GEMV ladder to show
how much of that ceiling real kernels actually reach on your device.

## The probes

| probe | what it measures |
|---|---|
| copy | `copyBufferToBuffer` bandwidth (2× bytes) |
| triad | `C = A + s·B` read/write mix (3× bytes) |
| read ceiling ★ | pure-read grid-stride reduction, the GEMV-shaped number |
| gemv ladder | naive → coalesced → vec4 → multirow → subgroup, one optimization per rung |
| subgroup canary | the non-uniform `subgroupAdd` pattern that shipped in real engines, vs a guarded control |

The canary reproduces the pattern behind the NVIDIA/Windows subgroup bug found
in Xenova's Gemma 4 WebGPU engine (July 2026, [full post-mortem](https://github.com/Ar5en1c/gemma4-webgpu-nvidia-subgroup-fix)).
Guarded must pass everywhere; if bare fails on your machine, engines using that
pattern are computing wrong numbers fast.

## The rules

- Deterministic inputs: hash-derived, identically regenerable on CPU.
- **A kernel that fails the FP64 reference gate gets no performance number.**
- The quoted ceiling is max(read probe, best FP64-gated kernel): a ceiling your
  own kernels can exceed would not be a ceiling.
- Wall-clock timing over large amortized dispatch blocks, median of 5. Medians, not bests.
- Every number ships with its method in the JSON receipt.
- If it hits 70% of the ceiling, it says 70%.

Same methodology as
[gemma4-webgpu-nvidia-subgroup-fix](https://github.com/Ar5en1c/gemma4-webgpu-nvidia-subgroup-fix)
and the CUDA companion study (decode at the memory ceiling on RTX 5070).

## How it differs from other numbers you may have

| source | what it measures | what it misses for local AI |
|---|---|---|
| vendor spec sheets | theoretical peak bandwidth / TOPS | what your machine actually delivers through a browser, driver, OS |
| graphics benchmarks | shader/raster throughput | decode is memory-bound; FLOPs do not predict tok/s |
| native LLM tools (llama-bench, MLPerf) | one engine's tok/s on your install | no ceiling to compare against, no browser stack, no correctness canary |
| engine demo pages | that engine, that build | conflates hardware and harness; no receipts |
| **Headroom** | your delivered bandwidth ceiling, verified kernels vs it, and a driver-correctness canary, all receipted | engine-by-engine utilization (import receipts or wait for the engine round) |

## Community leaderboard

The page shows community ceilings: hardware-only rows built from submitted
receipts. Submission is opt-in and public by design: the button on the page
copies your receipt JSON and opens a GitHub issue with it, a validation
action ([leaderboard/ingest.py](leaderboard/ingest.py)) checks structure and
plausibility, stores the receipt under [community/](community/), rebuilds
[leaderboard.json](leaderboard.json), and closes the issue. No accounts on
the board, no server anywhere. Community rows are structure-validated and carry no canary verdict; canary
verdicts appear only on runs the author executed and receipted. The action validates structure, not silicon: the
audit trail (receipt + public submission issue per row) is the trust model.

## Run it

Any static server:

```
python3 -m http.server 8734
# open http://localhost:8734
```

Requires WebGPU (Chrome/Edge desktop, recent Android Chrome). Subgroup rung and
canary need the `subgroups` feature and degrade to N/A without it.

MIT.
