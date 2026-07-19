# HEADROOM_

**How fast is your machine, really?** A 30-second, in-browser WebGPU test of your
device's true memory-bandwidth ceiling for local AI — the number that decides your
tokens/s — plus a check for the driver bug that makes some in-browser LLM engines
silently produce garbage.

No model download (the probes use deterministic synthetic weights). No account,
no ads, no telemetry. Nothing leaves your machine unless you download and share
the receipt yourself.

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
| read ceiling ★ | pure-read grid-stride reduction — the GEMV-shaped number |
| gemv ladder | naive → coalesced → vec4 → multirow → subgroup, one optimization per rung |
| subgroup canary | the non-uniform `subgroupAdd` pattern that shipped in real engines, vs a guarded control |

The canary reproduces the pattern behind the NVIDIA/Windows subgroup bug found
in Xenova's Gemma 4 WebGPU engine (July 2026, [full post-mortem](https://github.com/Ar5en1c/gemma4-webgpu-nvidia-subgroup-fix)).
Guarded must pass everywhere; if bare fails on your machine, engines using that
pattern are computing wrong numbers fast.

## The rules

- Deterministic inputs: hash-derived, identically regenerable on CPU.
- **A kernel that fails the FP64 reference gate gets no performance number.**
- Wall-clock timing over large amortized dispatch blocks, median of 5 — medians, not bests.
- Every number ships with its method in the JSON receipt.
- If it hits 70% of the ceiling, it says 70%.

Same methodology as
[gemma4-webgpu-nvidia-subgroup-fix](https://github.com/Ar5en1c/gemma4-webgpu-nvidia-subgroup-fix)
and the CUDA companion study (decode at the memory ceiling on RTX 5070).

## Run it

Any static server:

```
python3 -m http.server 8734
# open http://localhost:8734
```

Requires WebGPU (Chrome/Edge desktop, recent Android Chrome). Subgroup rung and
canary need the `subgroups` feature and degrade to N/A without it.

MIT.
