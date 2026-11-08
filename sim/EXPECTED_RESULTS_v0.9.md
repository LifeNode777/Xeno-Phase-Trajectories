# EXPECTED_RESULTS_v0.9.md

**Status:** PRE-REGISTRATION (DRAFT)  
**Date:** 2026-10-12  
**Protocol:** XPT Instrument Characterization v0.9  
**Parent repository:** LifeNode777/Xeno-Phase-Trajectories  
**Corresponding documents:**  
- `sim/XPT_Instrument_Characterization_v0.9.md`  
- `sim/baseline_audit/` (Gate 0)  
- `sim/CONTRACT_v0.9.md` (to be created at closure)

> This document is the **pre-registration container**.  
> It MUST be frozen and committed **before** the first confirmatory run that produces a verdict.  
> Any change after the first confirmatory run is allowed only as a prospective amendment recorded in LOG.md with a new version identifier.  
> Retroactive editing of thresholds, budgets, or success criteria after inspecting results is forbidden.

---

## 0. Purpose of Pre-Registration

This file records, in advance:

1. The exact detection rules and thresholds that will be used.
2. The run budgets, seed family, and replication counts.
3. The stop-rules and hard-stop conditions.
4. The falsifiable hypotheses and expected directional outcomes.
5. The definition of every allowed verdict.
6. What will be treated as a successful characterization versus a trigger for revision.

A result that contradicts these pre-registered expectations is **evidence**, not a reason to rewrite the expectations after the fact.

---

## 1. Verdict Dictionary (frozen)

The following labels are the only permitted system-level and component-level outcomes:

| Label | Meaning |
|-------|---------|
| `STABLE` | All required components pass the dual-gate rule **and** temporal-shift stability under the frozen protocol. |
| `PARTIAL` | One or more components pass, but the complete multi-component stable signature is not met. |
| `INVISIBLE` | The declared detection rule is not met under the tested conditions. This is a valid positive result about the instrument’s operating envelope. |
| `FALSE_POSITIVE_CANDIDATE` | A nominally non-target or control system meets the detection rule. Requires mandatory investigation. |
| `INCONCLUSIVE` | Results cannot support a defensible classification (excessive run failures, uncertain threshold, etc.). |
| `INVALID_RUN` | The run violates protocol, has incomplete artifacts, or fails a technical validity check. |
| `MISCALIBRATED` | Cross-system sensitivity comparison (especially NLSE vs Van der Pol) produces a directional result opposite to the pre-registered hypothesis after fair normalization. |
| `NO_VERDICT` | Explicitly recorded absence of a decision (first-class outcome, not an error). |

`INVISIBLE`, `INCONCLUSIVE`, and `INVALID_RUN` MUST NOT be used interchangeably.

---

## 2. Frozen Detection Rule (inherited from v0.8, subject to Gate 0 verification)

**Primary separation gate:**  
`q95(D_CC) < q05(D_CN)`

**Secondary separation gate:**  
`median(D_CN) / median(D_CC) > 10`

**Shift stability requirement:**  
Detection remains valid under temporal shifts of `±5` and `±10` samples.

**Component set:**  
`onset`, `deformation`, `relaxation`, `new_regime`

**Stable detection (Track B working definition):**  
At least two of the four components pass the dual-gate rule **and** satisfy shift stability.

Exact definitions of `D_CC` and `D_CN`, quantile method, treatment of near-zero denominators, and aggregation rules MUST be taken from the verified v0.8 contract after Gate 0. They are not to be re-invented here.

---

## 3. Seed Family and Determinism

- **Base seed:** `20260921`
- **Offset rule:** deterministic per-system and per-track offset documented in each runner.
- Seeds identify complete generated trajectories and individual null realizations.
- Generator version + configuration version MUST be recorded alongside every seed.
- Re-using a seed without fixing generator and configuration versions does **not** constitute reproducibility.

---

## 4. Track-Specific Pre-Registered Expectations

### 4.1 Gate 0 — Baseline & Provenance Audit

**Required outcome before any confirmatory track:**  
One of the four allowed statuses must be declared:

- `REPRODUCED`
- `PARTIALLY_REPRODUCED`
- `NOT_REPRODUCIBLE`
- `BLOCKED_MISSING_ARTIFACTS`

Unresolved issues are carried forward as explicit limitations.  
Gate 0 status remains `PENDING` until the checklist in `BASELINE_AUDIT.md` is complete.

---

### 4.2 Gate 1 / Track D — Blind Onset Validity

**Systems (minimum):** NLSE, Duffing, Van der Pol, Rössler  

**Pre-registered metrics:**
- Absolute onset-time error (median and distribution)
- Proportion of eligible transitions detected within tolerance
- False-alarm rate on no-transition controls
- Missed-detection rate
- Fraction of runs returning `NO_VERDICT`

**Candidate timing criterion (inherited, to be confirmed):**  
Median absolute error ≤ 1 second **and** ≥ 90 % of detections within 1 second  
(Units, sample rate, and time-base MUST be verified before confirmatory runs.)

**False-alarm budget:**  
Must be declared numerically before execution (exact number or rate to be frozen in the final pre-registration commit).

**Interpretation rule:**  
High performance on NLSE does **not** compensate for systematic failure on other systems.  
Results are reported per system and per condition.

**Hard-stop:**  
If onset localization demonstrably depends on ground-truth-informed windows or leaks the transition time → `FAIL_RECORDED` + prospective amendment.

---

### 4.3 Track A — Adversarial Dynamics Suite

**Required systems and initial directional hypotheses (frozen before runs):**

| ID     | System                                      | Initial expected pattern (hypothesis, not acceptance rule) |
|--------|---------------------------------------------|------------------------------------------------------------|
| ADV-01 | High-dimensional Lorenz-96 (N=40)           | Likely `INVISIBLE`                                         |
| ADV-02 | Mackey–Glass delayed-feedback oscillator    | `INVISIBLE` or `PARTIAL`                                   |
| ADV-03 | Pure amplitude-modulated limit cycle        | `INVISIBLE`                                                |
| ADV-04 | Discontinuous jump map                      | `INVISIBLE`                                                |
| ADV-05 | Driven Duffing with strong additive noise   | `INVISIBLE`, `PARTIAL`, or unstable                        |
| ADV-06 | Coupled Van der Pol network (N=8)           | `INVISIBLE`                                                |
| ADV-07 | Focusing NLSE with strong linear damping    | `PARTIAL` (initial prediction)                             |
| ADV-08 | Defocusing NLSE                             | `INVISIBLE` (initial prediction)                           |

**Minimum run plan (per system):**
- 32 clean runs
- 64 nulls
- Same trajectory length after embedding as verified v0.8 baseline
- Same component windows and pipeline configuration
- Seed family based on `20260921` + documented offset

**Suite-level criterion:**
- Zero `STABLE` for systems without the target focusing-related construction (unless investigated as `FALSE_POSITIVE_CANDIDATE`)
- At most one documented `PARTIAL` among pure non-target controls before mandatory investigation

**Hard-stop (Qwen doctrine):**  
If a designated dead-math / state-based / amplitude-only control returns `STABLE` → `HALT` + `FAIL_RECORDED` + prospective amendment.  
Control passing is a stop signal, not a result to be explained away.

---

### 4.4 Track B — Hidden Perturbation Sensitivity

**Base systems:**  
- Unperturbed NLSE soliton  
- Unperturbed Van der Pol limit cycle  

**Perturbation classes:**
- **P1** Localized phase shift (`ε`, `δt`)
- **P2** Local curvature injection (amplitude + spatial width)
- **P3** Transient focusing potential (height + width + duration)

**Minimum sweep:**  
≥ 8 values of strength parameter × ≥ 6 values of duration/width  
16 clean + 32 nulls per sweep point  

**Pre-registered directional hypothesis:**  
Detection threshold on NLSE is expected to be clearly lower than on Van der Pol after fair normalization.  
This is a **hypothesis**, not a calibration rule.

**If the directional result reverses after proper normalization and controls** → label `MISCALIBRATED` + `FAIL_RECORDED` + mandatory diagnosis of scale, perturbation implementation, and null construction.

**Stable detection definition for sensitivity curves:**  
At least two components pass the dual-gate rule and shift stability (exact definition frozen before execution).

**Reporting requirements:**
- Detection probability vs strength/duration
- False-alarm rate at unperturbed baseline
- Smallest tested perturbation meeting the consistency criterion
- Dominant component
- Uncertainty / repeatability across seeds
- Explicit status: `WITHIN_GRID` / `BELOW_GRID` / `ABOVE_GRID` / `UNRESOLVED`

---

### 4.5 Track C — Embedding & Parameter Stability Map

**Sweep grid:**
- Embedding dimension `m ∈ {3, 4, 5, 6}`
- Time delay `τ ∈ {1, 2, 3, 5}`
- Optional MI-optimal delay reported separately (selection method frozen before execution)

**Reference systems:** NLSE, Duffing, Van der Pol

**Pre-registered stability criterion (to be finalized in the freeze commit):**  
Qualitative verdict remains unchanged for `m = 3–5` and `τ = 1–3`.

**Alternative quantitative option (choose exactly one before runs):**  
`|Δ metric| > 5 %` → treat as verdict change.

Only one tolerance rule may be active. Post-hoc switching is forbidden.

**If verdicts change under modest parameter variation inside the pre-registered region** → instrument is described as parameter-sensitive; operating envelope must be narrowed or a new instrument version started.

---

## 5. Global Stop-Rules and Hard-Stops

1. **Control passing is a stop signal.**  
   Any designated non-target / dead-math / amplitude-only / no-transition control that returns `STABLE` triggers `HALT` + `FAIL_RECORDED` + prospective amendment.

2. **Missing artifacts block the claim.**  
   If required code, data, or parameters are unavailable → `BLOCKED_MISSING_ARTIFACTS` (Gate 0) or `INVALID_RUN` / `INCONCLUSIVE` downstream.

3. **No silent threshold adjustment.**  
   Thresholds and budgets may be changed only prospectively, with a new versioned entry in LOG.md, before the affected confirmatory runs.

4. **Negative results are retained.**  
   Failed runs, null outcomes, and `NO_VERDICT` cases are first-class data. They are never overwritten or deleted.

5. **Discovery vs confirmation separation.**  
   Exploratory runs used for debugging must be labelled as such. Confirmatory runs use new seeds or a reserved set under the frozen protocol.

---

## 6. Run Budgets Summary (minimum)

| Track / Gate          | Clean runs (per system / point) | Nulls (per system / point) | Notes |
|-----------------------|---------------------------------|----------------------------|-------|
| Gate 0                | N/A (audit)                     | N/A                        | Reproduction attempt required |
| Gate 1 / Blind Onset  | TBD (freeze before run)         | TBD + FA budget            | Per system × condition |
| Track A               | 32                              | 64                         | 8 systems |
| Track B               | 16 per sweep point              | 32 per sweep point         | ≥ 8 × 6 grid minimum |
| Track C               | Sufficient for stable estimate  | Matching nulls             | Full factorial m × τ |

Exact numbers for Gate 1 and any upward revisions must be frozen in the final pre-registration commit.

---

## 7. Rössler Scope Decision (open item to close before freeze)

Rössler is required in Gate 1 / Blind Onset.  
Whether Rössler is also included as a third base system in Track B is a **decision to be recorded here before confirmatory runs** (gap G6 from earlier analysis).  

Current status: **TO BE DECIDED IN FREEZE COMMIT**.

---

## 8. Final Characterization Outcomes (for CONTRACT_v0.9.md)

At programme closure the contract will select one of:

- `CHARACTERIZED — OPERATING ENVELOPE IDENTIFIED`
- `CHARACTERIZED — REQUIRES REVISION`
- `INCOMPLETE — EVIDENCE GAPS REMAIN`

No aggregate “ROBUST” label is permitted without explicit reference to system classes, perturbation magnitudes, null procedures, and parameter region.

---

## 9. Change Log for this Pre-Registration Document

| Date       | Change                                      | Author / Role      |
|------------|---------------------------------------------|--------------------|
| 2026-10-12 | Initial pre-registration draft created      | AI executor (draft)|
|            |                                             |                    |

**Freeze rule:**  
Once the first confirmatory run that produces a verdict has been executed, this document may only be amended prospectively. Any amendment receives a new version identifier and is logged.

---

**Closing principle:**  
We pre-register so that surprising results can survive.  
We do not pre-register so that every test confirms the current story.
