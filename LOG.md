# XPT_LOG — Transition Geometry Testbed

> XPT_LOG records implementation history, experimental results, audits, rejected methods, and methodological decisions. It does not treat any intermediate PASS as validation of XPT.

## 2026-09-20: v0.1-v0.3 (ChatGPT)
- **Goal**: Does the amplitude metric separate the transition from noise?
- **Result**: No. distance(clean, null) ≈ distance(null, null). Metric is blind to phase.
- **Conclusion**: Pivot to trajectory geometry.

## 2026-09-20: v0.4 (ChatGPT)
- **Goal**: Is R_sigma universal?
- **Result**: No. "NLSE-surrogate" is a synthetic curve, not actual NLSE.
- **Status**: DIAGNOSTIC CODE EXPERIMENT, not a result.

## 2026-09-20: v0.6 (ChatGPT) + audit (Qwen)
- **Goal**: Trajectory geometry (Procrustes distance).
- **Bug**: procrustes_distance() silently drops 3D→2D (z-drop). Table is internally inconsistent.
- **Status**: FAILED / METHODOLOGICAL PROTOTYPE.
- **Next step**: v0.7 with the fix + H0 baseline.

## 2026-09-20: v0.7 result + audit patch v0.7.1 (Qwen leg)
- v0.7 (ChatGPT leg) ran the registered design; decision rule FAILED on all 4 systems.
- Audit findings (Qwen leg): F1 nulls re-detected own windows -> D_NN measures window arbitrariness, not H0 spread; F2 rule denominator wrong - disjointness q95(CC)<q05(CN) already holds for NLSE (0.008<0.374) and Duffing (0.224<0.779); F3 VdP D_CC=0.78 traces to relax-band bistability (durations 5.78/11.58, ratio 2.0); F4 NLSE null rejection 934/1024 = selection bias.
- Patch v0.7.1 = 3 hunks: CUSUM changepoint relax; nulls evaluated in clean window; rule v2 (disjointness) primary. Predictions P1-P5 pre-registered BEFORE any run.
- Runner: ChatGPT leg (Qwen leg sandbox unavailable this session).
- Status: predictions pending. If P1-P5 fail, Qwen audit is falsified -> correction logged here.

## 2026-09-20: v0.7.2 (GPT leg) — audit (Qwen leg)
- Compliant: window inheritance, seed-pair D_CC, D_NN descriptor-only, gates v2, degenerate->NO_VERDICT, health gate, bimodality WARNING, tau-MI-once, real tests.
- **BLOCKER**: window = [onset, onset+16] fixed (relax never detected; causal anchor dropped); slice-then-embed makes embedding impossible for tau>=5 (16-3*tau<2); v0.7 taus (7-59) imply 100% rejection -> UNHEALTHY -> NO_VERDICT everywhere.
- Pre-registered P6: as-is run returns NO_VERDICT/UNHEALTHY for NLSE, Duffing, VdP.
- Proposed v0.7.3 = 3 hunks: embed-then-slice OR anchor+CUSUM window with end-onset >= (m-1)*tau+32; payload SHA-256 in provenance; split rejection rates.
- **Status: PROPOSED / NOT EXECUTED.**
- One run to settle P6. No further versions this leg.

## 2026-09-20: decision — TS definition retained from v0.7; v0.7A = v0.7 + H1-H4
- v0.7.2 PASS = VOID AS SCIENTIFIC RESULT (detector off-target: windows ~8.5-20 s vs control 4.0 s).
- v0.7.2 elements retained: window inheritance, gate v2, D_NN descriptor, health gates.
- v0.7.2 elements rejected: scalar detector, anchor removal, paired-only nulls.
- v0.7 frozen as historical result.
- v0.7A preregistered: P1-P4 + falsification clause.
- Detector-without-anchor question deferred to separate detector-validation package.

## 2026-09-20: blind detector audit (control t=4.0 s, anchor withheld)
- v0.7.2 scalar: 100% detection, 0% within 2 s -> REJECTED (detects late attractor events).
- v0.7 trajectory: NLSE on-target blind (0.23 s); VdP/Duffing systematic late bias (2.2-2.8 s) => v0.7 verdicts for these systems are oracle-conditional; Rossler 0/32 honest.
- Decision: v0.7 RETAIN_AS_BASELINE, NOT_UNIVERSAL.
- Next preregistered question: blind onset fix (H-a local-MAD threshold / H-b CUSUM; H-c complexity detector for Rossler). Acceptance: median |err| <= 1 s, within_1s >= 0.9.
- Open: provenance fields (executor, code/ensemble sha256) for this audit JSON.
