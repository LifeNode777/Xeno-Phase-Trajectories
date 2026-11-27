# GPT_QWEN_line — Local Prediction-Error Onset Detector (Gate 1)

The GPT/Qwen line develops a blind onset detector for the Xeno-Phase-Trajectories programme. Its question is simple: **when a trajectory returns to a familiar state, does it still move the way it used to?** The detector learns what usually follows similar states during a reference interval. A sustained departure from that forecast gives it a candidate onset time.

This folder is the development record for that idea, from the first local-step prototype through the current six-step predictor. The sibling Grok line measures changes in the spacing of neighbouring states. Both lines address the same physical intervention, use the same Gate 1 evaluator (v1.1), and have the same classical references, `spectral` and `cusum_lv`. [Gate 1 protocol](../README.md) · [Grok line](../GROK_line/README.md) · [Programme log](../../../LOG.md)

**Current candidate:** v0.4 · **Evidence:** local regression tests and an exploratory five-system pilot · **Formal Gate 1 status:** `NOT_EVALUATED`

## Design intent

A scalar measurement can pass through the same value on the rising and falling sides of an oscillation. To distinguish those states, the detector reconstructs each point from several time-delayed readings. It finds nearby examples in the reference trajectory and uses their subsequent motion to predict the displacement of the observed signal. Neighbour distance determines whether the forecast has enough local support. Forecast error supplies the evidence for an alarm.

This distinction matters when interpreting silence. A trajectory can change so much that it leaves the reference neighbourhood altogether. The detector may then have too little support to judge the new motion. Gate 1 records this separately from a supported scan that finishes without finding an onset.

## Development history

| Stage | Contribution | What the next revision had to resolve |
| --- | --- | --- |
| GPT v0.1 | The initial sketch carried the historical v0.8 procedure alongside an experimental one-step predictor, `local_step_v01`. The latter established the prediction-error line. | The prototype assumed 32 samples per period and used a high error quantile sensitive to the largest calibration errors. |
| Qwen v0.1 | Introduced adaptive embedding dimension, proportional reference intervals and a window that could accumulate intermittent errors. | The dimension estimate depended on a single query point. The reported coverage lacked a measurement of actual neighbour support. |
| Qwen v0.2 | Introduced SciPy tree-based neighbour search and revised the embedding and sliding-window logic. | Dimension selection could collapse to one coordinate. The timestamp could fall at the start of the window before the first observed error. |
| Joint v0.3 | Combined adaptive embedding, measured neighbour support and a one-step forecast in a self-contained NumPy candidate. | On a 1,280-sample Gate 1 record, the earliest possible timestamp was 641. Interventions can start at sample 384. Its self-test also stopped while stacking unequal-length fixtures. |
| Joint v0.4 | Fits the model and its error thresholds inside the declared warm-up. A single supported state supplies a six-step forecast, with separate timestamps for estimated onset and confirmation. | Timing coverage now includes the full intervention range. Control alarms and missed Rössler interventions remain visible in the pilot below. |

## Current detection pipeline

1. **Learn the reference.** With the starting configuration, samples 0–159 determine the mean, scale and training examples. The first local minimum of binned mutual information selects the delay, searching up to 24 samples and falling back to one. A false-nearest-neighbours estimate selects an embedding dimension from 2 to 6.
2. **Build the forecast.** For each reconstructed state, find its five nearest training neighbours. At each of the next six sample offsets, use their median displacement as the forecast. All six future labels of every training example fall inside the training interval.
3. **Calibrate before scanning.** Held-out targets through sample 255 set the thresholds. The support radius is the 95th percentile of the farthest-neighbour distance among calibration queries. Supported calibration errors set a separate limit at each horizon: median error plus six median absolute deviations, with a numerical floor on the deviation.
4. **Localise and confirm.** Sample 256 is the first possible onset estimate. At a supported anchor, the first forecast target must exceed its limit, and at least four of the six targets must exceed theirs. The first qualifying anchor supplies the onset estimate `t_hat`. The sixth target supplies `decision_sample = t_hat + 5`. Both are zero-based indices in the original recording.
5. **Account for silence.** If no alarm qualifies, the fraction of supported scan anchors determines whether to return `NO_TRANSITION` or `NO_VERDICT`. Each alarm already requires a supported anchor. The scan-wide coverage threshold applies only after a scan without an alarm.

## Blind interface and health gates

The detector reads one observation array shaped `trials × samples` and one JSON configuration. It writes one prediction per trial in input order. Each record has the fields `status` and `t_hat`. An onset carries an integer sample index. Both other outcomes carry JSON `null`. Optional diagnostics include a reason and, for an alarm, its confirmation time. The detector itself imports NumPy and the Python standard library. The separate pilot runner owns the generator, seed, truth and evaluator.

| Diagnostic reason | Condition with the v0.4 starting configuration | Output |
| --- | --- | --- |
| `short_record` | Fewer than 262 samples, leaving insufficient room for the warm-up and one complete forecast | `NO_VERDICT` |
| `invalid_trace` | A sample is non-finite | `NO_VERDICT` |
| `flat_reference` | Training-prefix standard deviation below 1e-9 | `NO_VERDICT` |
| `short_embedding` | Fewer than 32 usable training anchors after embedding and forecast alignment | `NO_VERDICT` |
| `forecast_error` | First supported anchor meeting the four-of-six rule, including its first target | `ONSET` |
| `low_coverage` | No qualifying alarm and fewer than 80% of scan anchors supported | `NO_VERDICT` |
| `no_sustained_error` | No qualifying alarm and at least 80% of scan anchors supported | `NO_TRANSITION` |

The method assumes an intervention-free warm-up. A change during training can become part of the learned reference. At the other end of the recording, the final five samples cannot independently start a complete forecast. Unknown configuration keys, an incompatible method name or invalid settings raise an error before scoring.

## Folder contents and execution

| File | Purpose |
| --- | --- |
| [detektor_v04.py](detektor_v04.py) | Standalone detector and command-line interface |
| [configs/cfg_v04_start.json](configs/cfg_v04_start.json) | Starting configuration used by the tests and local pilot |
| [test_v04.py](test_v04.py) | Regression tests for boundary timing, prefix consistency, controls, invalid inputs and the subprocess interface |
| [run_pilot.py](run_pilot.py) | Exploratory runner for all five Gate 1 systems and both noise levels |
| [pilot_v04.json](pilot_v04.json) | Per-trial predictions, intervention timing references and evaluator metrics from the local run |
| [Manual GitHub Actions workflow](../../../.github/workflows/xpt-gpt-qwen-v04.yml) | Runs the tests and pilot and uploads their outputs |

Run from `sim/GATE_1/GPT_QWEN_line/` inside the XPT repository with Python 3.12 and NumPy 2.3.5. The middle command accepts an observation file supplied by the caller.

```bash
python test_v04.py
python detektor_v04.py --obs observations.npy --cfg configs/cfg_v04_start.json --out pred.json --diagnostics diag.json
python run_pilot.py > pilot_run.json
```

## Regression evidence

All four regression test methods passed locally. In the noisy-sinusoid fixture, the detector recovered phase jumps at samples 256, 384, 600 and 896 exactly. The estimates persisted when each recording was truncated at its confirmation sample. On the original v0.3 fixtures, the blind subprocess recovered the jump at 600, stayed quiet on the unchanged control and isolated spike, and abstained on a flat trace. The short record was tested separately. The jump at sample 100 returned `NO_TRANSITION`, documenting what happens when a change falls inside the assumed reference period.

## Exploratory Gate 1 results

The local v0.4 pilot used the public diagnostic seed `20261109` with the Gate 1 generator, subprocess wrapper and evaluator from commit `da3ef82`. Each system had eight intervention trials and eight controls at each noise level. A timing hit means an eligible intervention localised within ±1 characteristic period of its physical onset, `t_true`. All eight intervention trials were eligible in each cell. The two noise levels share underlying trajectories. [Raw pilot results](pilot_v04.json)

| System | Hits, ν = 0.05 | Control alarms, ν = 0.05 | Hits, ν = 0.20 | Control alarms, ν = 0.20 |
| --- | ---: | ---: | ---: | ---: |
| NLSE_A | 8/8 | 2/8 | 5/8 | 1/8 |
| NLSE_P | 8/8 | 1/8 | 3/8 | 1/8 |
| Duffing | 2/8 | 2/8 | 0/8 | 2/8 |
| Van der Pol | 1/8 | 4/8 | 0/8 | 1/8 |
| Rössler | 0/8 | 2/8 | 0/8 | 0/8 |

## Relation to the wider programme

NLSE_P addresses the original design question most directly. At low noise the predictor localised all eight phase interventions, but it also alarmed on one unchanged control. At higher noise it recovered three of eight interventions. The repaired classical baseline already classifies `spectral` as `STABLE` on NLSE_P at both noise levels. The pilot establishes that local forecast error can carry timing information in this condition. An advantage over the spectral baseline remains unproven.

Rössler provides a different test. In the archived November 20 baseline run, `spectral` had zero timing hits, while `cusum_lv` reached 72.0% at low noise and 57.5% at high noise. In the smaller v0.4 pilot, the predictor missed every Rössler onset at both noise levels. The development question is whether a later revision can recover interventions missed by the classical detectors while controlling alarms on unchanged trajectories. A paired comparison on identical observations can identify exactly which trials each method recovers. [Archived baseline run](../runs/2026-11-20-baseline-repair/SUMMARY.md)

**Formal Gate 1 status remains `NOT_EVALUATED`.** A confirmatory verdict requires a frozen candidate and configuration, execution on a fresh seed, and preserved predictions scored by the common evaluator.
