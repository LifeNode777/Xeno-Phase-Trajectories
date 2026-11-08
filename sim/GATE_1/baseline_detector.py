"""
GATE 1 - baseline_detector.py  (spec v1.0)

Independent, deliberately simple reference detectors. They obey the same contract as the
XPT detector.py:   python baseline_detector.py --obs obs.npy --cfg cfg.json --out pred.json
Input : obs.npy, shape (n_trials, n_samples)   (NOTHING else: no seed, no truth, no window bounds)
Output: JSON list, one entry per trial:  {"status": "ONSET"|"NO_TRANSITION"|"NO_VERDICT", "t_hat": int|null}

Methods (cfg["method"]):
  center    PRIOR-GUESS REFERENCE. Always answers cfg["guess"]. It is told the eligible window, so it is
            not a detector - it measures how much a leaked prior alone would score.
  cusum_lv  causal rolling mean + log-variance, one-sided CUSUM on the standardised deviation.
            Blind BY CONSTRUCTION to transitions that preserve level and variance (NLSE_P).
  spectral  causal rolling dominant frequency, CUSUM on its standardised deviation.
All thresholds are standardised on the first cfg["warmup"] samples of the SAME trial.
"""
import argparse
import json
import numpy as np


def _cusum_alarm(u, k, h):
    """u: (n, m) standardised deviations (nan where undefined). Returns (alarm_idx, start_idx), -1 if none."""
    n, m = u.shape
    S = np.zeros(n)
    last_zero = np.zeros(n, dtype=int)
    alarm = np.full(n, -1)
    start = np.full(n, -1)
    for i in range(m):
        ui = np.nan_to_num(u[:, i], nan=0.0)
        S = np.maximum(0.0, S + ui - k)
        z = S == 0
        last_zero = np.where(z & (alarm < 0), i, last_zero)
        fire = (S > h) & (alarm < 0)
        alarm = np.where(fire, i, alarm)
        start = np.where(fire, last_zero, start)
    return alarm, start


def _rolling_lv(x, W):
    win = np.lib.stride_tricks.sliding_window_view(x, W, axis=1)
    m = win.mean(-1)
    v = np.log(win.var(-1) + 1e-12)
    pad = np.full((x.shape[0], W - 1), np.nan)
    return np.hstack([pad, m]), np.hstack([pad, v])


def _standardise(feat, ref_end):
    ref = feat[:, :ref_end]
    mu = np.nanmean(ref, axis=1, keepdims=True)
    sd = np.nanstd(ref, axis=1, keepdims=True)
    return (feat - mu) / np.where(sd > 1e-12, sd, np.nan), sd[:, 0]


def run_cusum_lv(obs, cfg):
    W, wu, k, h, lag = cfg["W"], cfg["warmup"], cfg["k"], cfg["h"], cfg["lag_comp"]
    m, v = _rolling_lv(obs, W)
    zm, sdm = _standardise(m, wu)
    zv, sdv = _standardise(v, wu)
    u = np.fmax(np.abs(zm), np.abs(zv))
    u[:, :wu] = np.nan                      # alarms only after warm-up
    alarm, start = _cusum_alarm(u, k, h)
    return alarm, start + lag, (sdm <= 1e-12) & (sdv <= 1e-12)


def run_spectral(obs, cfg):
    Wf, step, wu, k, h, lag = cfg["Wf"], cfg["step"], cfg["warmup"], cfg["k"], cfg["h"], cfg["lag_comp"]
    n, T = obs.shape
    ends = np.arange(Wf - 1, T, step)
    hann = np.hanning(Wf)
    feat = np.full((n, len(ends)), np.nan)
    freqs = np.fft.rfftfreq(1024)
    for i in range(n):
        win = np.lib.stride_tricks.sliding_window_view(obs[i], Wf)[ends - (Wf - 1)]
        win = (win - win.mean(axis=1, keepdims=True)) * hann
        spec = np.abs(np.fft.rfft(win, 1024, axis=1))
        spec[:, 0] = 0
        feat[i] = freqs[spec.argmax(axis=1)]
    ref_cols = ends < wu
    mu = feat[:, ref_cols].mean(axis=1, keepdims=True)
    sd = feat[:, ref_cols].std(axis=1, keepdims=True)
    sd = np.maximum(sd, 0.004)               # floor: one padded-FFT bin neighbourhood, avoids 0/0 on pure tones
    u = np.abs(feat - mu) / sd
    u[:, ref_cols] = np.nan
    alarm_c, start_c = _cusum_alarm(u, k, h)
    alarm = np.where(alarm_c >= 0, ends[np.clip(alarm_c, 0, None)], -1)
    start = np.where(alarm_c >= 0, ends[np.clip(start_c, 0, None)], -1)
    return alarm, start + lag, np.zeros(n, dtype=bool)


def detect(obs, cfg):
    obs = np.asarray(obs, dtype=float)
    n, T = obs.shape
    out = []
    bad = ~np.isfinite(obs).all(axis=1) | (obs[:, :cfg.get("warmup", 256)].std(axis=1) < 1e-9)
    method = cfg["method"]
    if method == "center":
        for i in range(n):
            out.append({"status": "NO_VERDICT", "t_hat": None} if bad[i]
                       else {"status": "ONSET", "t_hat": int(cfg["guess"])})
        return out
    obs_c = np.where(np.isfinite(obs), obs, 0.0)
    alarm, t_hat, flat = (run_cusum_lv if method == "cusum_lv" else run_spectral)(obs_c, cfg)
    for i in range(n):
        if bad[i] or flat[i]:
            out.append({"status": "NO_VERDICT", "t_hat": None})
        elif alarm[i] < 0:
            out.append({"status": "NO_TRANSITION", "t_hat": None})
        else:
            out.append({"status": "ONSET", "t_hat": int(max(0, min(T - 1, t_hat[i])))})
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--obs", required=True)
    ap.add_argument("--cfg", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    cfg = json.load(open(a.cfg))
    json.dump(detect(np.load(a.obs), cfg), open(a.out, "w"))
