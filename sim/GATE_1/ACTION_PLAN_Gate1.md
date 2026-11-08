# GATE 1 — Blind Onset Validity  
## Action Plan (Version synchronized with internal documentation)

**Document status:** v3  
**Date:** 2026-11-08  
**Target location:** `sim/GATE_1/ACTION_PLAN_Gate1.md`  
**Dependency:** Gate 0 CLOSED — `PARTIALLY_REPRODUCED`  
**Parent document:** `VoidProbe_Instrument_Characterization` (will remain non-public for a fucking long time 🙃)  
**Core Principle:** *The detector must find the wound without being handed the map.*

---

## 1. Position of Gate 1 in the Characterization Programme

According to VoidProbe v0.9, Gate 1 is **one of five independent questions** in the instrument characterization programme:

1. Gate 0 — Baseline & Provenance (closed as `PARTIALLY_REPRODUCED`)
2. **Gate 1 — Blind Onset Validity** ← current
3. Track A — Adversarial Dynamics & xxx
4. Track B — xxx
5. Track C — xxx
6. Gate 2 — xxx

**Key protocol principle:**  
A favourable result in one track **does not compensate** for failure or uncertainty in another.  
Gate 1 tests exclusively the ability to localize onset. It does not test many other things (which we will not discuss publicly for now) 😆

---

## 2. Objective and Research Question (exactly according to the protocol)

> Can XPT estimate a transition time without access to the true onset, a ground-truth-aligned evaluation window, or information that reveals the answer indirectly?

Gate 1 tests **temporal performance**, not geometric separation of clean/null trajectories.  
These two results must be reported separately.

Historical v0.7 results (late bias on Duffing/VdP, 0/32 on Rössler) constitute **motivation**.

---

## 3. Architecture — Blindness by Design (requirements from §7.3)

- The generator/evaluator holds the ground-truth onset separately from the detector input.
- The detector receives **only** permitted observation data and predeclared metadata.
- The truth record must not be mounted, imported, or queryable by the detector process.
- SHA-256 identifies the truth artifact, but a **hash alone does not provide isolation**. Isolation must be enforced by process, permissions, or interface.
- Onsets are randomized within a predeclared eligible range. The range and sampling rule are frozen before confirmation.
- No-transition controls and transitions of varying strength and duration are included.
- Rules are frozen for: missed detections, multiple candidates, edge events, ties, and minimum valid window length.

### Three isolated components

1. **`generator.py`** — generates trials, randomizes \( t_{true} \), writes `observations.npy` + locked `ground_truth.json`
2. **`detector.py`** — receives only `observations.npy` + frozen config. On failed health gates → mandatory `NO_VERDICT`
3. **`evaluator.py`** — reads predictions and truth only after the detector process has fully terminated

---

## 4. Systems (minimum required)

- **NLSE** — with explicit definition of the equation, initial condition, coefficient regime, and onset construction
- **Duffing** — with documented forcing and parameter switch
- **Van der Pol** — with parameters and transition construction
- **Rössler** — with explicit definition of the transition mechanism (promoted from OUT_OF_SCOPE in v0.8)

**Prohibition:** silently changing the transition mechanism solely because the detector has difficulty with it. Any change to a generator requires a new identifier and an amendment.

---

## 5. Metrics (according to §7.5)

Report per system and condition:

- absolute onset-time error (median + distribution)
- proportion of eligible transitions detected within the frozen tolerance
- false-alarm rate on no-transition controls (with denominator and uncertainty)
- missed-detection rate
- detection latency (where meaningful)
- fraction of runs with `NO_VERDICT` / invalid / incomplete
- performance by noise level, transition strength, duration, onset location
- comparison against a simple, independently implemented baseline change detector (e.g. local-MAD or a true CUSUM)

**Critical note:**  
The historical `≤ 1 s` criterion from LOG.md is a **candidate**, not an automatically inherited threshold.  
Before adopting it, sample rates, solver time units, and whether the tolerance is metrologically meaningful across all systems must be checked. If systems require different time scales, system-specific tolerances must be pre-registered.

---

## 6. Pre-Freeze Checklist (mandatory before any confirmatory seed)

According to the protocol and Gap Register (G3, G10):

- [ ] Exact definition of the onset/window algorithm (is it really CUSUM, or gradient + threshold?)
- [ ] Operational Ground Truth — mathematical definition of \( t_{true} \) per system (including correction for solver delays)
- [ ] Randomization Bounds and sampling rule
- [ ] Detector Health Gates (numerical thresholds that force `NO_VERDICT`)
- [ ] Time-Base Mapping (sample → physical/solver time)
- [ ] Blindness enforced by process/interface, not merely by hash
- [ ] Rules for missed detections, multiple candidates, edge events, ties, minimum valid window
- [ ] Comparison baseline detector (local-MAD / CUSUM) implemented independently
- [ ] Full provenance schema compliant with §14

---

## 7. Implementation Roadmap

### Phase 0 — Specification Closure + Protocol Freeze
- Resolve gaps G3 and G10 from the Gap Register
- Commit the frozen Gate 1 specification
- Update / create the corresponding section in `EXPECTED_RESULTS_v0.9.md`

### Phase 1 — Implementation of isolated components
- `generator.py` (including no-transition mode + varied strength/duration)
- `detector.py` (blind, with health gates)
- `evaluator.py`
- Independent baseline change detector
- Full provenance compliant with the schema in §14

### Phase 2 — Diagnostic / Exploratory Run
- Separate seed
- Verification of isolation and pipeline
- Results labelled as `EXPLORATORY` — do not enter confirmation

### Phase 3 — Freeze + Confirmatory Run
- Freeze of code + config + seed family
- Confirmatory run with a new seed
- Automatic evaluation

### Phase 4 — Blind Replication / Independent Review
- Handover of the frozen code to an independent leg / reviewer
- Required convergence on a predeclared subset

### Phase 5 — Adjudication
- Report using the status vocabulary from §3 (`COMPLETED` / `INVALID_RUN` / `INCONCLUSIVE` / `BLOCKED`, etc.)
- Update of LOG.md
- Decision on Gate 1 status (validated / partially validated / contradicted / inconclusive / blocked)

---

## 8. Hard-Stops and Stop Rules (synchronized with §12)

Mandatory stop of the confirmatory batch upon:

1. Ground-truth leakage (detector has access to the truth fixture)
2. Configuration / provenance mismatch
3. Technical integrity failure (schema, identity checks, incorrect decision rule)
4. Pre-registered false-alarm budget exceeded
5. Control detection requiring diagnosis (sentinel control meets the full multi-component rule)

**Principle:**  
A stop does not mean erasing the result. Triggering data remain in the record with their actual status.  
“Hard-stop” ≠ “erase the result”.

---

## 9. Statuses and Verdicts (use exclusively the vocabulary from §3)

**Run-level:** `COMPLETED` | `INVALID_RUN` | `INCOMPLETE` | `BLOCKED`  
**System-level:** `STABLE` | `PARTIAL` | `INVISIBLE` | `FALSE_POSITIVE_CANDIDATE` | `INCONCLUSIVE` | `NO_VERDICT`  

`INVISIBLE`, `INCONCLUSIVE`, `NO_VERDICT` and `INVALID_RUN` are **not** interchangeable.

---

## 10. What Gate 1 is **not**

According to the Non-goals and §15.4 of the protocol:

- Gate 1 **does not** open the path to biological data analysis
- Gate 1 **does not** authorize claims that the instrument is ready for biological transfer
- Gate 1 **does not** compensate for weak results in Tracks A/B/C
- Gate 1 **does not** allow a declaration of “characterization complete”

Only after xxx and fulfilment of the conditions listed in xxx may a separate biological study be **considered**.  
Passing Gate 1 alone is not sufficient.

---

## 11. Expected Deliverables

- `sim/GATE_1/` with full code, configs, results and figures
- Audit report using the status vocabulary from v0.9
- Update of LOG.md
- Entry in the Gap Register (closure of G3 and G10)
- Materials for later xxx

---

## 12. Operational Checklist

- [ ] 1. Resolve gaps G3 (onset algorithm) and G10 (blindness by process)
- [ ] 2. Close the Pre-Freeze Checklist
- [ ] 3. Implement isolated generator / detector / evaluator
- [ ] 4. Implement independent baseline change detector
- [ ] 5. Add full provenance compliant with the schema in §14
- [ ] 6. Diagnostic / Exploratory run
- [ ] 7. Protocol Freeze + pre-registration update
- [ ] 8. Confirmatory run
- [ ] 9. Independent review / Blind Replication
- [ ] 10. Report + update of LOG.md and Gap Register
- [ ] 11. Gate 1 status (without drawing conclusions about biology)

---

**Overarching principle (closing the protocol):**

> XPT should not be judged by whether every test confirms its current interpretation.  
> It should be judged by whether its behaviour can be measured, its limits can be named, surprising outcomes can survive scrutiny, and its claims can be reconstructed from public evidence.

**No v0.9 result is established by the existence of this document.**

---

**End of document — ACTION_PLAN_Gate1.md**
