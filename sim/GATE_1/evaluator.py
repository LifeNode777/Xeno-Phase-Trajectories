"""
GATE 1 - evaluator.py  (spec v1.0)

Reads predictions and truth ONLY after the detector process has terminated.
Implements the frozen metrics and verdict rules of GATE1_SPEC_v1.md. No manual override.
"""
import numpy as np

TOL_PRIMARY = 1.0      # in T_c
TOL_SECONDARY = 0.5    # in T_c
CEILING_MIN = 0.95     # ideal-detector ceiling needed for the primary (t_true) criterion to be attainable
HIT_MIN, HIT_LB_MIN, MED_MAX_FRAC = 0.90, 0.85, 0.5
FA_MAX, FA_UB_MAX = 0.05, 0.10
ABSTAIN_MAX = 0.30
ELIGIBLE_MIN = 0.80
PARTIAL_MIN = 0.50


def wilson(k, n, z=1.96):
    if n == 0:
        return (float("nan"), float("nan"))
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    w = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (c - w, c + w)


def eval_transition(preds, truth, nu, spt):
    n = len(preds)
    t_true, t_det = truth["t_true"], truth["t_det"][nu]
    elig = t_det >= 0
    st = np.array([p["status"] for p in preds])
    th = np.array([p["t_hat"] if p["t_hat"] is not None else -10 ** 9 for p in preds])
    onset = st == "ONSET"
    out = {"n": n, "eligible_frac": float(elig.mean())}
    ne = int(elig.sum())
    out["n_eligible"] = ne
    ceiling = float((np.abs(t_det - t_true) <= TOL_PRIMARY * spt)[elig].mean()) if ne else float("nan")
    out["oracle_ceiling_primary"] = ceiling
    for name, tol in (("tol1.0", TOL_PRIMARY), ("tol0.5", TOL_SECONDARY)):
        for ref_name, ref in (("t_true", t_true), ("t_det", t_det)):
            hit = onset & (np.abs(th - ref) <= tol * spt) & elig
            k = int(hit.sum())
            lo, hi = wilson(k, ne)
            out[f"hit_{name}_{ref_name}"] = {"rate": k / ne if ne else float("nan"), "lo": lo, "hi": hi}
    err = np.abs(th - t_true)[onset & elig]
    out["median_abs_err_Tc"] = float(np.median(err) / spt) if err.size else float("nan")
    out["frac_onset"] = float(onset[elig].mean()) if ne else float("nan")
    out["frac_no_verdict"] = float((st == "NO_VERDICT")[elig].mean()) if ne else float("nan")
    out["frac_no_transition"] = float((st == "NO_TRANSITION")[elig].mean()) if ne else float("nan")
    return out


def eval_control(preds):
    n = len(preds)
    st = np.array([p["status"] for p in preds])
    fa = int((st == "ONSET").sum())
    lo, hi = wilson(fa, n)
    return {"n": n, "fa_rate": fa / n, "fa_hi": hi, "no_transition": float((st == "NO_TRANSITION").mean()),
            "no_verdict": float((st == "NO_VERDICT").mean())}


def capability_verdict(tr, ct):
    """Returns (label, adjusted_flag, reason)."""
    if ct["fa_rate"] > FA_MAX or ct["fa_hi"] > FA_UB_MAX:
        return "FALSE_POSITIVE_CANDIDATE", False, "control veto"
    if tr["eligible_frac"] < ELIGIBLE_MIN:
        return "INCONCLUSIVE", False, "too few oracle-detectable trials"
    if tr["frac_no_verdict"] > ABSTAIN_MAX or ct["no_verdict"] > ABSTAIN_MAX:
        return "INCONCLUSIVE", False, "abstention above budget"
    adjusted = tr["oracle_ceiling_primary"] < CEILING_MIN
    ref = "t_det" if adjusted else "t_true"
    h = tr[f"hit_tol1.0_{ref}"]
    if h["rate"] >= HIT_MIN and h["lo"] >= HIT_LB_MIN and tr["median_abs_err_Tc"] <= MED_MAX_FRAC * TOL_PRIMARY:
        return "STABLE", adjusted, "meets all capability criteria"
    if h["rate"] >= PARTIAL_MIN:
        return "PARTIAL", adjusted, "hit rate between 0.50 and the STABLE criteria"
    return "INVISIBLE", adjusted, "hit rate below 0.50"
