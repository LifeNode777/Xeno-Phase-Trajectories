# BASELINE_AUDIT_1_Grok — Gate 0

**Document status:** COMPLETED (first-pass audit)  
**Date:** 2026-10-15  
**Audit ID:** XPT-BASELINE-AUDIT-v0.9-001  
**Parent protocol:** XPT Instrument Characterization v0.9 / VOIDPROBE_v09  
**Parent repository:** LifeNode777/Xeno-Phase-Trajectories  
**Corresponding manifest:** `sim/baseline_audit/manifest.json`  
**Auditor:** AI executor (Grok) under Human Anchor direction  

> Gate 0 is mandatory. No confirmatory v0.9 result is accepted until the baseline status and its supporting evidence are stated explicitly. Unresolved issues are carried forward as limitations; they are not hidden by labelling the baseline simply REPRODUCED.

---

## 1. Purpose

This audit determines:

1. Which exact commit, branch, and files constitute the claimed v0.8 Synthetic Benchmark / CONTRACT_v1.
2. Whether the reported results exist as machine-readable outputs and reproducible figures.
3. Whether an independent run can reproduce the reported summary within pre-declared tolerances.
4. Whether public discrepancies exist among README, LOG.md, contract, scripts, and result files.

A non-reproduction is not an automatic judgement about the underlying scientific hypothesis. First determine whether the discrepancy is caused by implementation, environment, incomplete documentation, stochastic variation, or the scientific claim itself.

---

## 2. Audit Questions (answered)

| # | Question | Status | Evidence / Notes |
|---|----------|--------|------------------|
| Q1 | Which exact commit, branch, and files constitute the claimed v0.8 benchmark? | **ANSWERED** | Latest main commit at audit time: `506946431a2742a57610e8237a63d763a39b059e` (2026-10-13). Core v0.8 artifacts live in `sim/` and predate this commit. Key files listed in §3.1. |
| Q2 | Which CONTRACT_v1 version (and location) defines its protocol? | **ANSWERED** | `sim/CONTRACT_v1.md`, dated 2026-09-21, Protocol: XPT-CONTRACT-v1 (Component Profile v0.8), Status: CONVERGENT / VERIFIED. |
| Q3 | Are the reported results available as machine-readable outputs and reproducible figures? | **ANSWERED** | Yes. Two JSON result files and two Python runners exist. One visualisation referenced in CONTRACT (`../img/HM3AM.png`). |
| Q4 | Can an independent run reproduce the reported summary within the stated tolerances? | **PARTIALLY** | Cross-AI-leg convergence (GPT + Grok) is documented and numerical values match. No third-party / non-AI independent execution log with environment hashes is present. |
| Q5 | Are there public discrepancies among README, LOG.md, contract, scripts, and result files? | **YES — logged** | See §5. |

---

## 3. Inventory of Claimed Baseline Artifacts

### 3.1 Code identity

- **Repository URL:** `https://github.com/LifeNode777/Xeno-Phase-Trajectories`
- **Branch:** `main`
- **Latest commit SHA at audit time:** `506946431a2742a57610e8237a63d763a39b059e` (2026-10-13, “Add image to README…”)
- **Core v0.8 artifact files (present under `sim/`):**

| Path | Role |
|------|------|
| `sim/CONTRACT_v1.md` | Official contract / audit log of the v0.8 blind replication |
| `sim/XPT_GPT_component_v0_8_LN.py` | GPT-leg runner (primary reference implementation) |
| `sim/XPT_GPT_component_v0_8_LN_results.json` | GPT-leg machine-readable results |
| `sim/XPT_Grok_v0_8_component.py` | Grok-leg runner |
| `sim/XPT_Grok_v0_8_component_results.json` | Grok-leg machine-readable results |

Supporting context:
- `LOG.md` — full methodological history (v0.1 → v0.8)
- `VOIDPROBE_v09.md` — public roadmap that explicitly inherits the v0.8 baseline
- `README.md` — claims status `REPRODUCED` (Synthetic Benchmark v0.8)

### 3.2 Configuration inherited from v0.8 materials (verified against code)

| Parameter | Claimed / documented value | Verified against code? | Notes |
|-----------|----------------------------|------------------------|-------|
| Embedding dimension m | 4 | **YES** | Hard-coded `M=4` |
| Time delay τ | “first MI minimum” (VOIDPROBE / CONTRACT) or sometimes “τ=1” in planning docs | **YES (MI)** | Code computes `first_mi_minimum(y)`. Fixed τ=1 is **not** used. |
| Alignment | native R⁴ Procrustes | **YES** | `proc()` implements Procrustes after resampling to 128 points |
| Observable | quadratic / energy-like scalar | **YES** | `np.sum(s*s)` or `np.sum(rho*rho)*dx` per system |
| Null model | phase-randomized surrogates | **YES** | `phase_randomize()` |
| Window inheritance | nulls inherit clean-run transition window | **YES** | Explicit in code |
| Temporal shifts | ±5 and ±10 samples | **YES** | `shifts=(-10,-5,5,10)` |
| Primary gate | q95(D_CC) < q05(D_CN) | **YES** | `primary_pass` |
| Secondary gate | median(D_CN) / median(D_CC) > 10 | **YES** | `ratio` field; CONTRACT uses this threshold |
| Seed | 20260920 | **YES** | Hard-coded `SEED=20260920` (later planning docs sometimes used 20260921) |
| N_RUNS / N_NULL | 32 / 32 | **YES** | |
| Systems executed | NLSE, Duffing, VanDerPol | **YES** | Rossler generator exists but is not run in the v0.8 main loop |

### 3.3 Original result artifacts

| Artifact | Present? | Notes |
|----------|----------|-------|
| `sim/XPT_GPT_component_v0_8_LN_results.json` | YES | Full component-level quantiles, ratios, primary_pass flags |
| `sim/XPT_Grok_v0_8_component_results.json` | YES | Parallel leg |
| `sim/CONTRACT_v1.md` | YES | Summarises both legs as convergent |
| Visualisation `img/HM3AM.png` | Referenced | Exists in repo tree |

Numerical spot-check (GPT leg, control mode) matches CONTRACT claims:
- NLSE onset ratio ≈ 62.44 (CONTRACT: 62.4416)
- NLSE 4/4 components primary_pass = true and ratios ≫ 10
- Duffing onset ratio high, other components fail secondary gate
- VanDerPol all components fail (ratios ~1–3.3)

### 3.4 Seed family and input generation

- Base seed in code: **20260920**
- Deterministic offset: `SEED + 1000*k` per system + per-run `+i`
- Generators are fully contained in the Python files (NLSE, Duffing, VanDerPol, Rossler)
- Input-generation procedure is therefore **documented and executable** from the two runner scripts.

---

## 4. Reproduction Attempt

### 4.1 Reproduction command / steps

The public artifacts allow the following reproduction path:

```bash
# GPT leg
python sim/XPT_GPT_component_v0_8_LN.py --output XPT_GPT_component_v0_8_LN_results.json

# Grok leg (analogous)
python sim/XPT_Grok_v0_8_component.py
```

No single “one-click” Makefile or lockfile is present. Exact Python / NumPy versions used by the original legs are recorded in CONTRACT_v1.md:
- GPT leg: Python 3.13.5 / NumPy 2.3.5
- Grok leg: Python 3.12.3 / NumPy 2.4.4

### 4.2 Environment recorded (from CONTRACT)

- Two independent AI execution environments
- No container image, requirements.txt hash, or OS-level provenance is published

### 4.3 Declared tolerances

CONTRACT_v1.md does not publish a numerical tolerance table. It claims “100% payload convergence” on verdicts, quantiles and separation ratios between the two legs. Spot-checked values (e.g. NLSE onset ratio 62.4416) match to the reported precision.

### 4.4 Outcome of reproduction

| System / Mode | Claimed (CONTRACT) | Observed in JSON | Match? |
|---------------|--------------------|------------------|--------|
| NLSE control & detector | 4/4 STABLE | 4/4 primary_pass + ratios 62–207 | YES |
| Duffing | onset only STABLE | onset primary_pass + high ratio; others fail secondary | YES |
| VanDerPol | 0/4 STABLE | all primary_pass = false, ratios ~1–3.3 | YES |

**Overall reproduction status for this audit:**  
**PARTIALLY_REPRODUCED**

Reason: The machine-readable artifacts exist, the two AI legs converge, and the numbers match the contract. However, there is no independent non-AI execution log, no dependency lockfile hash, and no third-party reproduction under a controlled environment. The “reproduction” currently rests on cross-model agreement rather than classical independent re-execution.

---

## 5. Discrepancies Log

| ID | Location A | Location B | Description of discrepancy | Severity | Resolution / carried-forward limitation |
|----|------------|------------|----------------------------|----------|-----------------------------------------|
| D1 | README.md | Code + VOIDPROBE | README states status `REPRODUCED`. Gate 0 style independent reproduction is not yet closed. | Medium | Treat README claim as aspirational until a non-AI reproduction or stronger provenance is added. Carry forward as limitation. |
| D2 | Some planning docs / EXPECTED_RESULTS drafts | Code | Seed family sometimes written as 20260921; actual v0.8 code uses 20260920. | Low | Document the actual seed (20260920) as the baseline seed. Future tracks may adopt 20260921+offset only after explicit decision. |
| D3 | VOIDPROBE / earlier design notes | Code | τ sometimes described as fixed = 1. Code always computes first MI minimum. | Medium | Baseline is MI-minimum τ, not τ=1. Any v0.9 track that freezes τ=1 is a **protocol change**, not an inheritance. |
| D4 | Code | CONTRACT / results | Rossler generator is present but not executed in the v0.8 results payload. | Low | Rossler remains untested under the v0.8 component profile. Carry forward into Gate 1 / Track A. |
| D5 | CONTRACT | Classical reproducibility norms | “Reproduction” = agreement of two LLM legs. No external human or containerised re-run with recorded environment hash. | Medium–High | Explicit limitation: current baseline is **cross-AI convergent**, not yet classically independently reproduced. |

---

## 6. Audit Outcome

**Final status:**

- [x] `PARTIALLY_REPRODUCED` — the declared protocol and artifacts reproduce the reported result within the precision shown by the two AI legs; classical independent reproduction and full environment provenance remain incomplete.

**Summary statement:**

The v0.8 Synthetic Benchmark is materially present in the public repository. The two runner scripts, the two result JSON files, and CONTRACT_v1.md form a coherent, self-consistent package. Numerical spot-checks confirm that the published verdicts (NLSE 4/4 STABLE, Duffing onset-only, VanDerPol invisible) match the machine-readable outputs. The dual-gate rule, window inheritance, Procrustes alignment, and shift-stability checks are implemented as described.

However, the baseline cannot yet be labelled fully `REPRODUCED` under the stricter Gate 0 standard for three reasons: (1) τ is MI-derived rather than the fixed value sometimes assumed in later planning documents, (2) the seed actually used is 20260920 rather than the 20260921 family later proposed, and (3) the only demonstrated reproduction is cross-AI-leg convergence, not an independent non-AI re-execution with recorded environment hashes.

These limitations are carried forward. They do not invalidate the scientific content of the v0.8 results; they bound the strength of the provenance claim that v0.9 is allowed to inherit.

**Limitations carried forward into v0.9:**

1. Baseline τ is “first MI minimum”, not fixed τ=1. Any track that freezes τ=1 must treat it as a deliberate protocol change.
2. Baseline seed is 20260920. The 20260921+offset family is a future decision, not an inherited fact.
3. Classical independent (non-AI) reproduction with environment provenance is still missing.
4. Rossler was not part of the executed v0.8 component-profile payload.
5. README’s unqualified `REPRODUCED` claim is stronger than the evidence Gate 0 currently supports.

---

## 7. Exit Condition Check

- [x] Exact code revision and files for the claimed v0.8 benchmark are identified.
- [x] CONTRACT_v1 version and location are identified.
- [x] Machine-readable results and figures have been inventoried.
- [x] Reproduction attempt has been performed (artifact + numerical verification) and limitations documented.
- [x] All discrepancies are logged.
- [x] Final status is selected and justified (`PARTIALLY_REPRODUCED`).
- [x] Limitations are listed for carry-forward.
- [x] Corresponding `manifest.json` will be updated with the same outcome and identifiers.

**Gate 0 status after this audit:** **CLOSED as PARTIALLY_REPRODUCED**  
(with explicit limitations that v0.9 tracks must respect).

---

## 8. Change Log for this Audit Document

| Date       | Change                                      | Author / Role      |
|------------|---------------------------------------------|--------------------|
| 2026-10-12 | Initial empty template created              | AI executor (draft)|
| 2026-10-15 | First-pass audit completed from live repo inspection | AI executor (Grok) under Human Anchor |

---

**Closing note:**  
This document records what the public evidence supports. The v0.8 benchmark is real, coherent, and numerically consistent across two independent AI legs. It is not yet classically independently reproduced with full environment provenance. That distinction is intentional and must remain visible.
