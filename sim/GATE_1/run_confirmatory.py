
#!/usr/bin/env python3
"""
GATE 1 - run_confirmatory.py  (spec v1.0, BASELINE-ONLY)

Confirmatory characterization of the BENCHMARK BASELINES (cusum_lv, spectral).
The XPT detector is NOT evaluated here. This run characterizes the instrument
chamber, not the XPT instrument. Verdicts are per system x noise, never pooled.

Hard stops (ACTION_PLAN_Gate1.md §8):
  - leakage canary dirty (pre or post)          -> BLOCKED, exit 1
  - calibration_report.json missing             -> BLOCKED_MISSING_ARTIFACTS, exit 1
  - tuned cfgs incomplete for any condition     -> BLOCKED, exit 1
No fallback parameters. No manual overrides.
"""
import hashlib
import json
import platform
import sys
import time

import numpy as np

import generator as G
import evaluator as E
import run_blind as R

SEED_CONFIRMATORY = 20261110   # distinct namespace from diag=20261108 / cal=20261109
N_TRIALS = 200                 # >= 32 required by spec; frozen here
METHODS = ("cusum_lv", "spectral")   # 'center' stays EXPLORATORY (leaked-prior probe)

CODE_FILES = ("generator.py", "evaluator.py", "baseline_detector.py",
              "run_blind.py", "run_calibration.py", "run_confirmatory.py")


def sha256(path):
    return hashlib.sha256(open(path, "rb").read()).hexdigest()


def main():
    print("=== GATE 1: CONFIRMATORY RUN (BASELINE-ONLY) ===", flush=True)
    t0 = time.time()

    # --- Hard stop 1: calibrated configs must exist and be complete ---------
    try:
        calib = json.load(open("calibration_report.json"))
        cfgs_all = calib["cfgs"]
    except (FileNotFoundError, KeyError):
        print("[!] BLOCKED_MISSING_ARTIFACTS: calibration_report.json with 'cfgs' "
              "is required. No fallback parameters are permitted.", flush=True)
        sys.exit(1)
    for cond in G.CONDITIONS:
        for m in METHODS:
            if m not in cfgs_all.get(cond, {}):
                print(f"[!] BLOCKED: tuned cfg missing for {cond}/{m}", flush=True)
                sys.exit(1)

    # --- Hard stop 2: leakage canary (pre) ----------------------------------
    ok_pre, canary_pre = R.leakage_canary()
    if not ok_pre:
        print("[!] BLOCKED: leakage canary dirty (pre-run).", flush=True)
        print(json.dumps(canary_pre, indent=2))
        sys.exit(1)
    print("[+] Canary clean (pre). Process isolation verified.", flush=True)

    report = {
        "label": "CONFIRMATORY_BASELINE_ONLY",
        "xpt_detector_status": "NOT_EVALUATED",
        "seed": SEED_CONFIRMATORY,
        "n_trials": N_TRIALS,
        "calibration_seeds": calib.get("seeds"),
        "provenance": {
            "code_sha256": {f: sha256(f) for f in CODE_FILES},
            "calibration_report_sha256": sha256("calibration_report.json"),
            "python": platform.python_version(),
            "numpy": np.__version__,
            "executor": "run_confirmatory.py (subprocess-isolated detectors)",
        },
        "leakage_canary_pre": canary_pre,
        "cells": {},
        "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(t0)),
    }

    # --- Execution -----------------------------------------------------------
    for cond in G.CONDITIONS:
        print(f"--- {cond} ---", flush=True)
        obs_t, tr = G.make_batch(cond, "transition", N_TRIALS, SEED_CONFIRMATORY)
        obs_c, _ct = G.make_batch(cond, "control", N_TRIALS, SEED_CONFIRMATORY)
        for nu in G.NOISE_LEVELS:
            cell = {}
            for m in METHODS:
                cfg = cfgs_all[cond][m]
                pt = R.run_detector("baseline_detector.py", obs_t[nu], cfg)
                pc = R.run_detector("baseline_detector.py", obs_c[nu], cfg)
                et = E.eval_transition(pt, tr, nu, G.SPT)
                ec = E.eval_control(pc)
                lab, adj, why = E.capability_verdict(et, ec)
                cell[m] = {"cfg": cfg, "transition": et, "control": ec,
                           "verdict": lab, "adjusted": adj, "why": why}
                print(f"  nu={nu:<4} [{m:9s}] {lab:26s} "
                      f"FA={ec['fa_rate']:.3f} med|err|={et['median_abs_err_Tc']}",
                      flush=True)
            report["cells"][f"{cond}|{nu}"] = cell

    # --- Hard stop 3: leakage canary (post) ---------------------------------
    ok_post, canary_post = R.leakage_canary()
    report["leakage_canary_post"] = canary_post
    report["leakage_canary_clean"] = bool(ok_pre and ok_post)
    report["runtime_s"] = time.time() - t0

    json.dump(report, open("confirmatory_report.json", "w"),
              indent=1, default=float)

    if not ok_post:
        print("[!] INVALID_RUN: post-run canary dirty. Report saved for audit; "
              "verdicts MUST NOT be quoted.", flush=True)
        sys.exit(1)

    print(f"DONE in {report['runtime_s']:.0f}s -> confirmatory_report.json",
          flush=True)


if __name__ == "__main__":
    main()