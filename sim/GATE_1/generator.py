"""
GATE 1 - generator.py  (spec v1.0)

Generates blind observations + truth for the Blind Onset Validity benchmark.
Time base: every system is sampled at SPT samples per characteristic period T_c,
so "1 T_c" is the same *relative* tolerance for every system.

Conditions
  NLSE_A   focusing NLSE soliton, nonlinearity g: 1.0 -> 1.5      (amplitude/breathing transition)
  NLSE_P   focusing NLSE soliton, uniform potential V: 0 -> -0.25 (PHASE-ONLY transition: |psi| unchanged)
  DUFFING  driven Duffing, forcing gamma: 0.20 -> 0.50            (periodic -> chaotic switching)
  VDP      Van der Pol, mu: 1.0 -> 3.0                            (limit cycle -> relaxation oscillation)
  ROSSLER  Rossler a=b=0.2, c: 3.0 -> 5.7                         (periodic -> chaos)

Truth never has to touch disk: run_blind.py keeps it in memory until the
detector process has terminated.
"""
import numpy as np

SPT = 32                       # samples per characteristic period T_c
N_TC = 40                      # observed length in T_c
N_SAMPLES = SPT * N_TC         # 1280
BURN_TC = 10                   # unobserved burn-in
TRUE_MIN_TC, TRUE_MAX_TC = 12, 28   # eligible window for t_true (in T_c)
WARMUP_TC = 8                  # declared transition-free warm-up contract (< TRUE_MIN on purpose)
PRE_SAFE = TRUE_MIN_TC * SPT   # samples guaranteed pre-transition (used for noise scaling)
NOISE_LEVELS = (0.05, 0.20)    # observational noise sd / pre-transition signal sd
ORACLE_KAPPA, ORACLE_RUN = 3.0, 8   # oracle: deviation > 3*sigma for 8 consecutive samples

CONDITIONS = ("NLSE_A", "NLSE_P", "DUFFING", "VDP", "ROSSLER")
COND_ID = {c: i + 1 for i, c in enumerate(CONDITIONS)}
ROLE_ID = {"transition": 1, "control": 2}

# nominal T_c per system (dimensionless solver units) and RK4 substeps per sample
TC = {"NLSE_A": 4 * np.pi, "NLSE_P": 4 * np.pi, "DUFFING": 2 * np.pi / 1.2,
      "VDP": 6.663, "ROSSLER": 5.9}
SUB = {"DUFFING": 4, "VDP": 8, "ROSSLER": 8}
NLSE_SUB = 8
NX, LBOX = 128, 40.0


# ---------------------------------------------------------------- ODE systems
def _deriv(cond, t, y, p):
    if cond == "DUFFING":
        x, v = y[:, 0], y[:, 1]
        return np.stack([v, -0.3 * v + x - x ** 3 + p * np.cos(1.2 * t)], axis=1)
    if cond == "VDP":
        x, v = y[:, 0], y[:, 1]
        return np.stack([v, p * (1 - x ** 2) * v - x], axis=1)
    if cond == "ROSSLER":
        x, yy, z = y[:, 0], y[:, 1], y[:, 2]
        return np.stack([-yy - z, x + 0.2 * yy, 0.2 + z * (x - p)], axis=1)
    raise ValueError(cond)


PARAMS = {"DUFFING": (0.20, 0.50), "VDP": (1.0, 3.0), "ROSSLER": (3.0, 5.7)}


def _init_ode(cond, n, rng):
    if cond == "DUFFING":
        return np.stack([rng.uniform(-1, 1, n), rng.uniform(-0.5, 0.5, n)], axis=1)
    if cond == "VDP":
        return np.stack([rng.uniform(-2, 2, n), rng.uniform(-1, 1, n)], axis=1)
    return np.stack([rng.uniform(-2, 2, n), rng.uniform(-2, 2, n), rng.uniform(0, 1, n)], axis=1)


def _sim_ode(cond, y0, t_true, switch):
    n = y0.shape[0]
    pre, post = PARAMS[cond]
    s = SUB[cond]
    dt_s = TC[cond] / SPT
    h = dt_s / s
    burn = BURN_TC * SPT
    y = y0.copy()
    out = np.empty((n, N_SAMPLES))
    for k in range(burn + N_SAMPLES):
        if k >= burn:
            out[:, k - burn] = y[:, 0]
        if switch:
            p = np.where(k - burn >= t_true, post, pre)
        else:
            p = np.full(n, pre)
        for j in range(s):
            t = k * dt_s + j * h
            k1 = _deriv(cond, t, y, p)
            k2 = _deriv(cond, t + h / 2, y + h / 2 * k1, p)
            k3 = _deriv(cond, t + h / 2, y + h / 2 * k2, p)
            k4 = _deriv(cond, t + h, y + h * k3, p)
            y = y + h / 6 * (k1 + 2 * k2 + 2 * k3 + k4)
    return out


# ------------------------------------------------------------------- NLSE
def _init_nlse(n, rng):
    a = rng.uniform(0.9, 1.1, n)
    phi = rng.uniform(0, 2 * np.pi, n)
    return a, phi


def _sim_nlse(cond, a, phi, t_true, switch):
    n = a.shape[0]
    dx = LBOX / NX
    x = (np.arange(NX) - NX // 2) * dx
    kk = 2 * np.pi * np.fft.fftfreq(NX, d=dx)
    dt = TC[cond] / SPT / NLSE_SUB
    lin = np.exp(-1j * kk ** 2 * dt / 4)          # half linear step (Strang)
    psi = (a[:, None] / np.cosh(a[:, None] * x[None, :])) * np.exp(1j * phi)[:, None]
    g_pre, V_pre = 1.0, 0.0
    g_post, V_post = (1.5, 0.0) if cond == "NLSE_A" else (1.0, -0.25)
    burn = BURN_TC * SPT
    out = np.empty((n, N_SAMPLES))
    for k in range(burn + N_SAMPLES):
        if k >= burn:
            out[:, k - burn] = psi[:, NX // 2].real
        if switch:
            sw = (k - burn >= t_true)[:, None]
            g = np.where(sw, g_post, g_pre)
            V = np.where(sw, V_post, V_pre)
        else:
            g, V = np.full((n, 1), g_pre), np.full((n, 1), V_pre)
        for _ in range(NLSE_SUB):
            psi = np.fft.ifft(np.fft.fft(psi, axis=1) * lin, axis=1)
            psi = psi * np.exp(1j * (g * np.abs(psi) ** 2 - V) * dt)
            psi = np.fft.ifft(np.fft.fft(psi, axis=1) * lin, axis=1)
    return out


# ---------------------------------------------------------------- public API
def _clean(cond, rng, n, t_true, switch, state=None):
    if cond.startswith("NLSE"):
        st = state if state is not None else _init_nlse(n, rng)
        return _sim_nlse(cond, st[0], st[1], t_true, switch), st
    st = state if state is not None else _init_ode(cond, n, rng)
    return _sim_ode(cond, st, t_true, switch), st


def make_batch(cond, role, n, seed, nus=NOISE_LEVELS):
    """Return (obs, truth). obs[nu] has shape (n, N_SAMPLES). truth is for the evaluator only."""
    rng = np.random.default_rng([int(seed), COND_ID[cond], ROLE_ID[role]])
    if role == "transition":
        t_true = rng.integers(TRUE_MIN_TC * SPT, TRUE_MAX_TC * SPT + 1, n)
        clean, state = _clean(cond, rng, n, t_true, True)
        twin, _ = _clean(cond, rng, n, t_true, False, state)
    else:
        t_true = np.full(n, -1)
        clean, _ = _clean(cond, rng, n, t_true, False)
        twin = None
    obs, t_det, sig = {}, {}, {}
    for nu in nus:
        sigma = nu * clean[:, :PRE_SAFE].std(axis=1)
        obs[nu] = clean + rng.normal(size=clean.shape) * sigma[:, None]
        sig[nu] = sigma
        if twin is not None:
            dev = np.abs(clean - twin) > ORACLE_KAPPA * sigma[:, None]
            run = np.lib.stride_tricks.sliding_window_view(dev, ORACLE_RUN, axis=1).all(-1)
            run[np.arange(N_SAMPLES - ORACLE_RUN + 1)[None, :] < t_true[:, None]] = False
            has = run.any(axis=1)
            t_det[nu] = np.where(has, run.argmax(axis=1), -1)
        else:
            t_det[nu] = np.full(n, -1)
    truth = {"cond": cond, "role": role, "t_true": t_true, "t_det": t_det, "sigma": sig,
             "tolerance_samples": SPT, "seed": int(seed)}
    return obs, truth
