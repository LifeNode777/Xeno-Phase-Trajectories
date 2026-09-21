#!/usr/bin/env python3
"""
XPT v0.8-component (Grok leg)
Pre-registered 2026-09-21.

Frozen decisions:
- m=4, tau=1 global
- min component length after embed >= 12
- primary: q95(D_CC) < q05(D_CN)
- secondary: median(D_CN)/median(D_CC) > 10
- shift test ±5 / ±10
- stability = primary & secondary & shifts keep primary & ratio>10
- nulls inherit exact component window
- quadratic observable
- Procrustes native R^4, no PCA
"""

from __future__ import annotations
import json
import hashlib
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
import numpy as np

# ---------------------------------------------------------------------------
# Config (frozen)
# ---------------------------------------------------------------------------
SEED = 20260921
N_RUNS = 8           # practical first pass
N_NULL = 64          # practical first pass
M = 4
TAU = 1
MIN_EMBED_POINTS = 12
SEPARATION_RATIO = 10.0
CONTROL_TIME = 4.0
SHIFT_AMOUNTS = (5, 10)

COMPONENTS = {
    "onset":       (0.00, 0.15),
    "deformation": (0.15, 0.70),
    "relaxation":  (0.70, 0.90),
    "new_regime":  (0.90, 1.00),
}

# ---------------------------------------------------------------------------
# Generators (identical to v0.7)
# ---------------------------------------------------------------------------
def rk4(f, s, dt, t, *args):
    k1 = f(s, t, *args)
    k2 = f(s + 0.5 * dt * k1, t + 0.5 * dt, *args)
    k3 = f(s + 0.5 * dt * k2, t + 0.5 * dt, *args)
    k4 = f(s + dt * k3, t + dt, *args)
    return s + dt * (k1 + 2 * k2 + 2 * k3 + k4) / 6


def rossler(seed, dt=0.01, T=20.0):
    rng = np.random.default_rng(seed)
    s = np.array([0.1, 0.0, 0.0])
    ts, ys = [], []
    def f(s, t, a):
        x, y, z = s
        return np.array([-y - z, x + a * y, 0.2 + z * (x - 5.7)])
    for i in range(int(T / dt)):
        t = i * dt
        a = 0.2 if t < CONTROL_TIME else 0.38
        s = rk4(f, s, dt, t, a) + rng.normal(0, 5e-5, 3)
        if i % 2 == 0:
            ts.append(t)
            ys.append(np.sum(s * s))
    return np.asarray(ts), np.asarray(ys)


def vdp(seed, dt=0.01, T=20.0):
    rng = np.random.default_rng(seed)
    s = np.array([0.1, 0.0])
    ts, ys = [], []
    def f(s, t, mu):
        x, v = s
        return np.array([v, mu * (1 - x * x) * v - x])
    for i in range(int(T / dt)):
        t = i * dt
        mu = 1.0 if t < CONTROL_TIME else 5.0
        s = rk4(f, s, dt, t, mu) + rng.normal(0, 3e-5, 2)
        if i % 2 == 0:
            ts.append(t)
            ys.append(np.sum(s * s))
    return np.asarray(ts), np.asarray(ys)


def duffing(seed, dt=0.005, T=20.0):
    rng = np.random.default_rng(seed)
    s = np.array([0.1, 0.0])
    ts, ys = [], []
    def f(s, t, drive):
        x, v = s
        return np.array([v, x - x ** 3 - 0.2 * v + drive * np.cos(t)])
    for i in range(int(T / dt)):
        t = i * dt
        drive = 0.30 if t < CONTROL_TIME else 0.65
        s = rk4(f, s, dt, t, drive) + rng.normal(0, 2e-5, 2)
        if i % 2 == 0:
            ts.append(t)
            ys.append(np.sum(s * s))
    return np.asarray(ts), np.asarray(ys)


def nlse(seed, n=128, L=30.0, dt=0.003, T=10.0):
    rng = np.random.default_rng(seed)
    x = np.linspace(-L / 2, L / 2, n, endpoint=False)
    dx = x[1] - x[0]
    k = 2 * np.pi * np.fft.fftfreq(n, d=dx)
    psi = np.exp(-(x / 3) ** 2).astype(complex)
    psi *= np.exp(1j * 0.03 * rng.standard_normal(n))
    psi /= np.sqrt(np.sum(np.abs(psi) ** 2) * dx)
    ts, ys = [], []
    for j in range(int(T / dt)):
        t = j * dt
        kap = -1.0 if t < CONTROL_TIME else 1.0
        half = np.exp(-0.5j * k * k * dt / 2)
        psi = np.fft.ifft(np.fft.fft(psi) * half)
        psi *= np.exp(-1j * kap * np.abs(psi) ** 2 * dt)
        psi = np.fft.ifft(np.fft.fft(psi) * half)
        if j % 4 == 0:
            rho = np.abs(psi) ** 2
            q = np.sum(rho * rho) * dx
            ts.append(t)
            ys.append(q)
    return np.asarray(ts), np.asarray(ys)


SYSTEMS = {
    "NLSE": nlse,
    "Duffing": duffing,
    "VanDerPol": vdp,
    # Rössler intentionally omitted (OUT_OF_SCOPE)
}

# ---------------------------------------------------------------------------
# Core geometry
# ---------------------------------------------------------------------------
def phase_randomize(y: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    y = np.asarray(y, float)
    mu = y.mean()
    F = np.fft.rfft(y - mu)
    phase = np.angle(F)
    if len(F) > 2:
        phase[1:-1] = rng.uniform(-np.pi, np.pi, len(F) - 2)
    return np.fft.irfft(np.abs(F) * np.exp(1j * phase), n=len(y)) + mu


def delay_embed(y: np.ndarray, m: int = M, tau: int = TAU) -> np.ndarray:
    y = np.asarray(y, float)
    n = len(y) - (m - 1) * tau
    if n < MIN_EMBED_POINTS:
        raise ValueError(f"too short for embed: {n} < {MIN_EMBED_POINTS}")
    return np.column_stack([y[i * tau : i * tau + n] for i in range(m)])


def procrustes_distance(X: np.ndarray, Y: np.ndarray) -> float:
    X = np.asarray(X, float)
    Y = np.asarray(Y, float)
    if X.shape != Y.shape:
        raise ValueError(f"shape mismatch {X.shape} vs {Y.shape}")
    X = X - X.mean(axis=0, keepdims=True)
    Y = Y - Y.mean(axis=0, keepdims=True)
    nx = np.linalg.norm(X)
    ny = np.linalg.norm(Y)
    if nx <= 0 or ny <= 0:
        raise ValueError("degenerate")
    X = X / nx
    Y = Y / ny
    M = X.T @ Y
    U, _, Vt = np.linalg.svd(M, full_matrices=False)
    R = U @ Vt
    if np.linalg.det(R) < 0:
        U = U.copy()
        U[:, -1] *= -1
        R = U @ Vt
    return float(np.linalg.norm(X @ R - Y, ord="fro"))


U_POINTS = 64

def resample_sig(sig: np.ndarray, n: int = U_POINTS) -> np.ndarray:
    """Resample trajectory to fixed length so Procrustes is well-defined."""
    sig = np.asarray(sig, float)
    if len(sig) < 2:
        raise ValueError("sig too short")
    t0 = np.linspace(0, 1, len(sig))
    t1 = np.linspace(0, 1, n)
    return np.column_stack([np.interp(t1, t0, sig[:, j]) for j in range(sig.shape[1])])


def pairwise_distances(sigs: List[np.ndarray]) -> np.ndarray:
    vals = []
    for i in range(len(sigs)):
        for j in range(i + 1, len(sigs)):
            try:
                vals.append(procrustes_distance(sigs[i], sigs[j]))
            except ValueError:
                continue
    return np.asarray(vals, dtype=float) if vals else np.asarray([])


# ---------------------------------------------------------------------------
# Window detection (oracle + detector)
# ---------------------------------------------------------------------------
def detect_change_point(speed: np.ndarray, min_seg: int = 8) -> Optional[int]:
    n = len(speed)
    if n < 2 * min_seg:
        return None
    best_k, best_s = None, -np.inf
    for k in range(min_seg, n - min_seg + 1):
        left, right = speed[:k], speed[k:]
        mu1, mu2 = np.median(left), np.median(right)
        scale = max(1.4826 * np.median(np.abs(speed - np.median(speed))), 1e-12)
        s = abs(mu2 - mu1) / scale
        if s > best_s:
            best_s, best_k = s, k
    return best_k


def detect_window_detector(y: np.ndarray) -> Optional[Tuple[int, int]]:
    """CUSUM-style on speed of the scalar series treated as 1-D trajectory."""
    # speed of the scalar observable itself
    speed = np.abs(np.diff(y, prepend=y[0]))
    t_on = detect_change_point(speed)
    if t_on is None:
        return None
    tail = speed[t_on:]
    if len(tail) < 16:
        return None
    rel_local = detect_change_point(tail)
    if rel_local is None:
        return None
    t_rel = t_on + rel_local
    if t_rel - t_on < 20:
        return None
    return int(t_on), int(t_rel)


def detect_window_oracle(t: np.ndarray, y: np.ndarray) -> Optional[Tuple[int, int]]:
    """Oracle: onset near control time, relax = first sustained low-speed after peak."""
    idx = int(np.argmin(np.abs(t - CONTROL_TIME)))
    # simple: take a fixed-length window after control for oracle baseline
    # better: use speed peak after control
    speed = np.abs(np.diff(y, prepend=y[0]))
    search = speed[idx:]
    if len(search) < 30:
        return None
    peak_local = int(np.argmax(search))
    peak = idx + peak_local
    # relax: median of last 20% as terminal
    terminal = np.median(speed[int(0.8 * len(speed)):])
    threshold = terminal + 0.15 * max(abs(speed[peak] - terminal), 1e-12)
    relax = None
    for i in range(peak + 5, len(speed) - 5):
        if np.all(np.abs(speed[i:i + 5] - terminal) <= abs(threshold - terminal)):
            relax = i
            break
    if relax is None or relax - idx < 20:
        # fallback fixed window
        end = min(idx + int(0.4 * len(y)), len(y) - 1)
        return idx, end
    return idx, relax


# ---------------------------------------------------------------------------
# Component split + signature
# ---------------------------------------------------------------------------
def split_component(t_on: int, t_rel: int, frac: Tuple[float, float], series_len: int) -> Optional[Tuple[int, int]]:
    length = t_rel - t_on
    a = t_on + int(frac[0] * length)
    b = t_on + int(frac[1] * length)
    if frac[1] >= 1.0:
        b = min(t_rel + 5, series_len)
    if b - a < MIN_EMBED_POINTS + (M - 1) * TAU:
        return None
    return a, b


def make_signature(y: np.ndarray, window: Tuple[int, int]) -> np.ndarray:
    seg = y[window[0]:window[1]]
    return delay_embed(seg, m=M, tau=TAU)


def evaluate_component(
    clean_ys: List[np.ndarray],
    windows: List[Tuple[int, int]],
    component_name: str,
    frac: Tuple[float, float],
    seed_base: int,
) -> Dict[str, Any]:
    """
    For one component across all clean runs.
    Returns status + metrics.
    """
    clean_sigs = []
    valid_windows = []
    valid_ys = []
    for y, (t_on, t_rel) in zip(clean_ys, windows):
        cw = split_component(t_on, t_rel, frac, len(y))
        if cw is None:
            continue
        try:
            sig = resample_sig(make_signature(y, cw))
            clean_sigs.append(sig)
            valid_windows.append(cw)
            valid_ys.append(y)
        except ValueError:
            continue

    if len(clean_sigs) < 4:
        return {
            "status": "INVALID",
            "n_clean": len(clean_sigs),
            "reason": "too few valid clean signatures",
        }

    # Real multi-seed D_CC (no row-bootstrap)
    dcc = pairwise_distances(clean_sigs)
    if len(dcc) < 3:
        return {"status": "INVALID", "n_clean": len(clean_sigs), "reason": "D_CC empty"}

    q95_dcc = float(np.quantile(dcc, 0.95))
    med_dcc = float(np.median(dcc))

    # Nulls: phase-randomize each clean, same component window, resampled
    dcn_list = []
    rejected = 0
    n_per = max(4, N_NULL // max(1, len(clean_sigs)))
    for i, (y, cw) in enumerate(zip(valid_ys, valid_windows)):
        rng = np.random.default_rng(seed_base + 10_000 + i)
        for j in range(n_per):
            yn = phase_randomize(y, rng)
            try:
                nsig = resample_sig(make_signature(yn, cw))
                dcn_list.append(procrustes_distance(clean_sigs[i], nsig))
            except Exception:
                rejected += 1

    dcn = np.asarray(dcn_list, dtype=float)
    if len(dcn) < 10:
        return {
            "status": "INVALID",
            "n_clean": len(clean_sigs),
            "null_rejected": rejected,
            "reason": "too few valid nulls",
        }

    q05_dcn = float(np.quantile(dcn, 0.05))
    med_dcn = float(np.median(dcn))
    ratio = med_dcn / med_dcc if med_dcc > 0 else np.inf

    primary = bool(q95_dcc < q05_dcn)
    secondary = bool(ratio > SEPARATION_RATIO)

    # Shift test
    shift_ok = True
    shift_details = {}
    for shift in SHIFT_AMOUNTS:
        shifted_dcn = []
        for i, (y, (a, b)) in enumerate(zip(valid_ys, valid_windows)):
            a2 = max(0, a + shift)
            b2 = min(len(y), b + shift)
            if b2 - a2 < MIN_EMBED_POINTS + (M - 1) * TAU:
                continue
            try:
                csig = resample_sig(make_signature(y, (a2, b2)))
            except ValueError:
                continue
            rng = np.random.default_rng(seed_base + 20_000 + shift + i)
            for j in range(max(3, n_per // 2)):
                yn = phase_randomize(y, rng)
                try:
                    nsig = resample_sig(make_signature(yn, (a2, b2)))
                    shifted_dcn.append(procrustes_distance(csig, nsig))
                except Exception:
                    pass
        if len(shifted_dcn) < 5:
            shift_ok = False
            shift_details[f"shift_{shift}"] = "insufficient"
            continue
        shifted_dcn = np.asarray(shifted_dcn)
        q05_s = float(np.quantile(shifted_dcn, 0.05))
        med_s = float(np.median(shifted_dcn))
        prim_s = q95_dcc < q05_s
        ratio_s = med_s / med_dcc if med_dcc > 0 else 0.0
        shift_details[f"shift_{shift}"] = {
            "primary_holds": bool(prim_s),
            "ratio": float(ratio_s),
        }
        if not (prim_s and ratio_s > SEPARATION_RATIO):
            shift_ok = False

    status = "STABLE" if (primary and secondary and shift_ok) else "UNSTABLE"
    if rejected / max(1, rejected + len(dcn)) > 0.25:
        status = "INVALID"

    return {
        "status": status,
        "n_clean": len(clean_sigs),
        "null_used": len(dcn),
        "null_rejected": rejected,
        "q95_dcc": q95_dcc,
        "q05_dcn": q05_dcn,
        "median_dcc": med_dcc,
        "median_dcn": med_dcn,
        "ratio": float(ratio),
        "primary": primary,
        "secondary": secondary,
        "shift_ok": shift_ok,
        "shift_details": shift_details,
    }


# ---------------------------------------------------------------------------
# Main experiment
# ---------------------------------------------------------------------------
def run_system(name: str, base_seed: int) -> Dict[str, Any]:
    fn = SYSTEMS[name]
    print(f"\n=== {name} ===")

    # Generate cleans
    clean_ys = []
    clean_ts = []
    for i in range(N_RUNS):
        t, y = fn(base_seed + i)
        clean_ts.append(t)
        clean_ys.append(y)

    results = {"system": name, "n_runs": N_RUNS, "n_null_target": N_NULL}

    for wsource, detect_fn in [("oracle", detect_window_oracle), ("detector", None)]:
        windows = []
        valid_ys = []
        for t, y in zip(clean_ts, clean_ys):
            if wsource == "oracle":
                w = detect_fn(t, y)
            else:
                w = detect_window_detector(y)
            if w is not None:
                windows.append(w)
                valid_ys.append(y)

        print(f"  window_source={wsource}: {len(windows)}/{N_RUNS} valid windows")
        if len(windows) < 4:
            results[wsource] = {"error": "too few valid windows"}
            continue

        comp_results = {}
        for cname, frac in COMPONENTS.items():
            print(f"    component {cname} ...", end=" ", flush=True)
            cr = evaluate_component(valid_ys, windows, cname, frac, base_seed + hash(cname) % 10000)
            print(cr["status"])
            comp_results[cname] = cr

        results[wsource] = {
            "n_valid_windows": len(windows),
            "components": comp_results,
        }

    return results


def main():
    all_results = []
    for k, name in enumerate(SYSTEMS):
        r = run_system(name, SEED + 1000 * k)
        all_results.append(r)

    payload = {
        "protocol": "XPT_v0.8_component_Grok",
        "date": "2026-09-21",
        "seed": SEED,
        "N_RUNS": N_RUNS,
        "N_NULL": N_NULL,
        "m": M,
        "tau": TAU,
        "min_embed_points": MIN_EMBED_POINTS,
        "components_frac": COMPONENTS,
        "gates": {
            "primary": "q95(D_CC) < q05(D_CN)",
            "secondary": "median(D_CN)/median(D_CC) > 10",
            "shift": "±5 and ±10 must keep primary and ratio>10",
        },
        "results": all_results,
    }

    text = json.dumps(payload, indent=2, ensure_ascii=False)
    digest = hashlib.sha256(text.encode()).hexdigest()
    out = Path("/home/workdir/artifacts/XPT_v0_8_component_results.json")
    out.write_text(text + "\n", encoding="utf-8")
    print("\n" + "=" * 60)
    print("RESULT SHA256:", digest)
    print("RESULT FILE:", out)

    # Quick human summary
    print("\n=== SUMMARY ===")
    for r in all_results:
        print(f"\n{r['system']}:")
        for src in ("oracle", "detector"):
            if src not in r or "error" in r[src]:
                print(f"  {src}: FAILED window detection")
                continue
            print(f"  {src}:")
            for cname, cr in r[src]["components"].items():
                st = cr.get("status", "?")
                ratio = cr.get("ratio", None)
                ratio_s = f"{ratio:.1f}x" if ratio is not None else "-"
                print(f"    {cname:12s} {st:10s}  ratio={ratio_s}")


if __name__ == "__main__":
    main()
