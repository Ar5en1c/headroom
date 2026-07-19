# Evidence — first cross-device receipts (2026-07-19)

Three full runs of the deployed suite (v0.1.0, Chrome 150 on both platforms),
receipts verbatim in this directory. Every number FP64-gated and re-verified
post-timing; zero anomalies, zero uncaptured WebGPU errors.

| | RTX 5070 (Blackwell, Win11) | Apple M1 (metal-3, macOS) |
|---|---|---|
| read ceiling ★ | **577 GB/s** (86% of 672 GB/s spec) | 50.7–55.8 GB/s (74–82% of 68.25 spec) |
| copy / triad | 545 / 551 GB/s | 53 / 54 GB/s |
| gemv naive (uncoalesced) | 154 GB/s — **27%** | 25.5 GB/s — 46–50% |
| gemv coalesced | 545 GB/s — 94% | 55–57 GB/s — ~103% |
| gemv vec4 (best) | **580 GB/s — 100.4%** | 54–59 GB/s — ~105% |
| gemv subgroup | 573 GB/s — 99% | 48–59 GB/s |
| subgroup canary | control PASS · risky variants **BLOCKED** by compiler | same |
| E2B ceiling (derived 0.805 GB/token) | **≈717 tok/s** | ≈63–69 tok/s |
| real engine (Xenova E2B, our July measurements) | ~217 tok/s → **30% of ceiling** | 30–40 tok/s → ~50% |

## What the receipts establish

1. **Consumer Blackwell streams 577 GB/s through a browser tab.** WebGPU
   bandwidth efficiency on discrete GDDR7 (86% of spec) exceeds Apple unified
   memory (74–82%) on these runs.
2. **Coalescing is worth 3.7× on GDDR7.** The naive rung collapses to 27% on
   the 5070 but survives at ~50% on M1 — unified LPDDR forgives what discrete
   memory punishes.
3. **In-browser decode is launch-overhead-bound everywhere.** 5070: weight
   streaming needs 1.4 ms of each 4.6 ms token — ~70% of the budget is
   overhead. M1: ~14 ms of each ~29 ms token is overhead. The hardware ceiling
   is 2–3× above what engines deliver today.
4. **Current Chrome statically rejects the naive non-uniform subgroup class**
   (both platforms, both risky canary variants): `'subgroupAdd' must only be
   called from subgroup uniform control flow`. Note the shipped July engine
   compiled fine — its sites are analysis-clean shapes that still mis-executed
   on NVIDIA drivers at runtime. Replicating that exact shape is canary v2.
5. **Session variance is real:** the same M1 measured 50.7 (Pages tab) and
   55.8 GB/s (localhost tab) minutes apart — ±10% on a busy unified-memory
   laptop. Medians of 5 within a run; treat cross-run deltas <10% as noise.

Files: `5070-blackwell-win11.json`, `m1-pages.json`, `m1-localhost.json`.

## v0.2 canary evidence (2026-07-19, same day)

`5070-blackwell-win11-v0.2-canary-fail.json` — the headline receipt. Canary v2
runs the exact reduce shape that shipped in real in-browser LLM engines
(`subgroupAdd` after a lane-divergent store with an earlier reduction result
live across it — uniform per static analysis, so Chrome 150's compiler accepts
it). On RTX 5070 (Blackwell, Chrome 150 stable, Windows 11):

- **bare engine shape: 20/20 trials WRONG, max relative error 1.67×10⁻¹**
- butterfly control (`subgroupShuffleXor`): 0/20 wrong, max rel 5.56×10⁻⁷
- guarded v1 control: PASS (2.76×10⁻⁸) · naive v1 variants: rejected by compiler

Same run on Apple M1: 0/20 wrong on both variants ("engine shape verified").
Conclusion: the silent-corruption class found in July 2026 is **still live on
current stable Chrome on NVIDIA/D3D12** — static uniformity analysis blocks the
naive syntax but cannot see this shape, and only behavioral testing catches it.
Also in this run: read ceiling 589 GB/s, vec4 GEMV at 100.0% of it, E2B
ceiling 731 tok/s, `subgroupMaxSize: 128` reported by the adapter.
