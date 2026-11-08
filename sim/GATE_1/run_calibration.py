"""
GATE 1 - run_calibration.py  (spec v1.0)

BENCHMARK calibration, not a Gate 1 verdict. No XPT detector is involved.
  * baselines are tuned ONLY on the diagnostic seed (FA <= 2 % on diagnostic controls, lag bias removed)
  * they are then evaluated on a separate EXPLORATORY seed through the blind subprocess runner
  * purpose: show that the benchmark discriminates (prior-guess fails, scalar CUSUM is blind to NLSE_P, etc.)
All output is labelled EXPLORATORY and must not enter the confirmatory record.
"""
import json
import sys
import time
import numpy as np
import generator as G
import evaluator as E
import baseline_detector as B
import run_blind as R

SEED_DIAG, SEED_CAL = 20261108, 20261109      # exploratory namespaces; confirmatory seed is separate and secret
N_DIAG, N_CAL = int(sys.argv[1]) if len(sys.argv) > 1 else 150, int(sys.argv[2]) if len(sys.argv) > 2 else 200
H_GRID = [3, 5, 8, 12, 20, 30, 50, 80, 120, 200, 300, 500, 800, 1500, 3000, 6000]
FA_TUNE = 0.02


def base_cfg(method):
    if method == "cusum_lv":
        return {"method": method, "W": G.SPT, "warmup": G.WARMUP_TC * G.SPT, "k": 1.5, "h": 20, "lag_comp": 0}
    if method == "spectral":
        return {"method": method, "Wf": 3 * G.SPT, "step": 4, "warmup": G.WARMUP_TC * G.SPT, "k": 1.5, "h": 20,
                "lag_comp": 0}
    return {"method": "center", "guess": 20 * G.SPT, "warmup": G.WARMUP_TC * G.SPT}


def tune(method, cond, data):
    """Tune h (FA budget) and lag_comp on DIAGNOSTIC data of this condition only."""
    obs_t, tr_t, obs_c, _ = data
    cfg = base_cfg(method)
    chosen = H_GRID[-1]
    for h in H_GRID:
        cfg["h"] = h
        fa = max(np.mean([p["status"] == "ONSET" for p in B.detect(obs_c[nu], cfg)]) for nu in G.NOISE_LEVELS)
        if fa <= FA_TUNE:
            chosen = h
            break
    cfg["h"] = chosen
    cfg["lag_comp"] = 0
    errs = []
    for nu in G.NOISE_LEVELS:
        pr = B.detect(obs_t[nu], cfg)
        for p, tt in zip(pr, tr_t["t_true"]):
            if p["status"] == "ONSET":
                errs.append(p["t_hat"] - tt)
    if errs:
        cfg["lag_comp"] = int(-np.median(errs))
    return cfg


def main():
    t0 = time.time()
    report = {"label": "EXPLORATORY", "seeds": {"diag": SEED_DIAG, "cal": SEED_CAL}, "n_diag": N_DIAG, "n_cal": N_CAL,
              "cells": {}, "cfgs": {}}
    for cond in G.CONDITIONS:
        diag = (*G.make_batch(cond, "transition", N_DIAG, SEED_DIAG), *G.make_batch(cond, "control", N_DIAG, SEED_DIAG))
        d_obs_t, d_tr, d_obs_c, d_ct = diag
        cfgs = {"center": base_cfg("center")}
        for m in ("cusum_lv", "spectral"):
            cfgs[m] = tune(m, cond, (d_obs_t, d_tr, d_obs_c, d_ct))
        report["cfgs"][cond] = cfgs
        obs_t, tr = G.make_batch(cond, "transition", N_CAL, SEED_CAL)
        obs_c, ct = G.make_batch(cond, "control", N_CAL, SEED_CAL)
        for nu in G.NOISE_LEVELS:
            cell = {}
            for m, cfg in cfgs.items():
                pt = R.run_detector("baseline_detector.py", obs_t[nu], cfg)
                pc = R.run_detector("baseline_detector.py", obs_c[nu], cfg)
                et = E.eval_transition(pt, tr, nu, G.SPT)
                ec = E.eval_control(pc)
                lab, adj, why = E.capability_verdict(et, ec)
                cell[m] = {"transition": et, "control": ec, "verdict": lab, "adjusted": adj, "why": why}
            report["cells"][f"{cond}|{nu}"] = cell
        print(f"[{time.time() - t0:6.0f}s] {cond} done", flush=True)
    ok, rep = R.leakage_canary()
    report["leakage_canary_clean"] = ok
    json.dump(report, open("calibration_report.json", "w"), indent=1, default=float)

    print("\ncond|noise      ceil  | center hit  | cusum_lv hit  med  FA  verdict | spectral hit  med  FA  verdict")
    for key, cell in report["cells"].items():
        c, l, s = cell["center"], cell["cusum_lv"], cell["spectral"]
        ceil = l["transition"]["oracle_ceiling_primary"]
        f = lambda x: f"{x['transition']['hit_tol1.0_t_true']['rate']:.2f}"
        print(f"{key:14s} {ceil:5.2f} | {f(c)}        | {f(l)}  {l['transition']['median_abs_err_Tc']:5.2f} "
              f"{l['control']['fa_rate']:.2f} {l['verdict']:<24s}| {f(s)}  {s['transition']['median_abs_err_Tc']:5.2f} "
              f"{s['control']['fa_rate']:.2f} {s['verdict']}")
    print("canary clean:", ok)


if __name__ == "__main__":
    main()
