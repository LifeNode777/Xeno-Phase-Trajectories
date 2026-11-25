# GROK_line — Geometric Onset Detector (Gate 1)

Parallel developmental track for a blind onset localizer based on local trajectory geometry.

This folder contains the Grok-line candidate for Gate 1 of the Xeno-Phase-Trajectories characterization programme. It is maintained independently of the GPT/Qwen track. Both tracks are judged by the same frozen evaluator (`evaluator.py` v1.1) and are compared against the same classical baselines (spectral and cusum_lv).

## Design Intent

Most change-point detectors operate on amplitude, variance, or spectral content. The Grok line deliberately avoids those cues. Instead it measures a purely geometric quantity: the average distance to the k nearest neighbours of each point in a short Takens embedding of a sliding window. When the underlying dynamical regime changes, the local geometry of the reconstructed trajectory typically changes as well — even if the amplitude and power spectrum remain nearly constant (the classic phase-only case).

The detector is intentionally minimal:

- Embedding parameters are fixed (`m=4`, `τ=1`) so that detection remains causal and does not require mutual-information searches at runtime.
- Each window is amplitude-normalized before embedding, giving approximate scale invariance.
- The resulting scalar feature series is monitored by a magnitude CUSUM. The CUSUM is required to accumulate; isolated spikes do not trigger an alarm.
- All decisions are strictly causal. No retrospective peak or relaxation search is performed.

Health gates force a `NO_VERDICT` rather than a forced guess when the observation is too short, too constant, or otherwise unsuitable for embedding.

## Contract

The detector obeys the Gate 1 interface exactly:

```bash
python detector_v04.py --obs observations.npy --cfg cfg.json --out pred.json
```

- Input: only the observation array and a frozen configuration.
- Output: a list of records `{"status": "ONSET"|"NO_TRANSITION"|"NO_VERDICT", "t_hat": int|null}`.
- No imports of the generator, evaluator, ground truth, or any seed information are permitted.

## Contents

| Path | Purpose |
|------|---------|
| `detector_v04.py` | Current candidate implementation |
| `configs/cfg_v04_start.json` | Starting hyper-parameters (require calibration) |
| `tests/test_candidate.py` | Unit tests for accumulation behaviour, schema, and CLI contract |
| `docs/DEVELOPMENT_PROTOCOL.md` | Hard rules and mandatory development sequence for this line |
| `docs/MANIFEST_TEMPLATE.md` | Template for freezing a candidate |

## Relation to the Wider Programme

Gate 1 asks a single question: can a detector localize the physical intervention time from the observable trajectory alone, under a strict false-alarm budget, without access to ground-truth timing or pre-aligned windows?

The classical baselines already answer parts of that question. The Grok line exists to test whether a deliberately non-classical, geometry-first feature can complement or, in selected regimes (especially phase-only transitions), surpass them. Results are reported per system and noise level; aggregate scores are secondary.

No claim of Gate 1 success is made until a configuration has been frozen on diagnostic controls, a confirmatory run on a fresh seed has been executed, and the raw artefacts have been evaluated by the common judge.
