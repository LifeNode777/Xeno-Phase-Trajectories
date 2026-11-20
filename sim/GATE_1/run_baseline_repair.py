#!/usr/bin/env python3
"""XPT baseline calibration repair v1.1 (diagnostic only).

Add beside generator.py. Does not modify historical scripts or reports.
This procedure characterises classical baseline detectors only.
It does NOT evaluate or confirm the XPT detector.

Run:
  python sim/GATE_1/run_baseline_repair.py --out /new/output/directory
  python sim/GATE_1/run_baseline_repair.py --out /tmp/tune --tune-only
  python sim/GATE_1/run_baseline_repair.py --self-test
"""
from __future__ import annotations

import argparse
import contextlib
import csv
import hashlib
import io
import json
import math
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import time
import traceback

import numpy as np

HERE = Path(__file__).resolve().parent
PROTOCOL_VERSION = "XPT-BASELINE-REPAIR-1.1"
BASE_COMMIT = "70d0e245d9e97eaf4b02a05d702eec93365a32ca"

# SHA256 of the four core modules this procedure is allowed to trust.
# Update deliberately when those files change; never silently.
EXPECTED = {
    "generator.py": "55d65ec0be194b0c5be65fb31c363134b48abe03e76e933e5073769220d514ea",
    "baseline_detector.py": "120afae400473904416e7105295d8cecaa357d6f554496be8e49eecda4d2c4d5",
    "evaluator.py": "63cf738db2ed77dfaf721ce1bbc5114a713d2a81a53b7478a5bec0d56b0a996f",
    "run_blind.py": "146059d158afc6581bc470bd55b8eff2734851218ab9bad2ebf02dd164926f3a",
}

METHODS = ("cusum_lv", "spectral")
H_GRID = (3, 5, 8, 12, 20, 30, 50, 80, 120, 200, 300, 500, 800, 1500, 3000, 6000)
FA_TUNE = 0.02
N_DIAG = 120
DEFAULT_SEED_DIAG = 20261108

# First held-out stage matches the historical exploratory report.
# Second stage is a public engineering check, not a hidden XPT confirmation.
STAGES = (
    ("exploratory_recheck", 20261109, 150),
    ("diagnostic_verification", 20261116, 200),
)

G = B = E = R = None


class Blocked(RuntimeError):
    pass


class Untunable(Blocked):
    def __init__(self, trace):
        super().__init__(
            "UNTUNABLE: no candidate threshold meets FA <= 2% at both noise levels"
        )
        self.trace = trace


def digest(path: Path | str) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def plain(value):
    """Strict JSON: replace diagnostic NaN/inf with null, preserve counts."""
    if isinstance(value, dict):
        return {str(k): plain(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [plain(v) for v in value]
    if isinstance(value, np.ndarray):
        return plain(value.tolist())
    if isinstance(value, np.generic):
        return plain(value.item())
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def write_json(path: Path, value) -> None:
    path = Path(path)
    temp = path.with_name(path.name + ".tmp")
    temp.write_text(
        json.dumps(plain(value), indent=2, ensure_ascii=False, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    temp.replace(path)


def base_cfg(method: str) -> dict:
    """Deliberately identical to historical run_calibration.py base_cfg."""
    cfg = {
        "method": method,
        "warmup": G.WARMUP_TC * G.SPT,
        "k": 1.5,
        "h": 20,
        "lag_comp": 0,
    }
    if method == "cusum_lv":
        cfg["W"] = G.SPT
    else:
        cfg.update(Wf=3 * G.SPT, step=4)
    return cfg


def choose_threshold(measure):
    """No fallback. A failed grid is a recorded stop, never a usable config."""
    trace = []
    for h in H_GRID:
        rates = measure(h)
        trace.append({"h": h, "fa_by_noise": rates})
        if all(math.isfinite(v) and 0 <= v <= FA_TUNE for v in rates.values()):
            return h, trace
    raise Untunable(trace)


def tune(method, obs_t, truth_t, obs_c):
    cfg = base_cfg(method)

    def measure(h):
        cfg["h"] = h
        return {
            str(nu): float(
                np.mean([p["status"] == "ONSET" for p in B.detect(obs_c[nu], cfg)])
            )
            for nu in G.NOISE_LEVELS
        }

    h, trace = choose_threshold(measure)
    if h not in H_GRID:
        raise Blocked(f"Internal error: chosen h={h} not in H_GRID")
    cfg["h"] = h

    # Offset learned from diagnostic transitions only, then frozen.
    errs = []
    for nu in G.NOISE_LEVELS:
        for p, tt in zip(B.detect(obs_t[nu], cfg), truth_t["t_true"]):
            if p["status"] == "ONSET":
                errs.append(p["t_hat"] - int(tt))
    cfg["lag_comp"] = int(-np.median(errs)) if errs else 0

    measured = measure(h)
    if max(measured.values()) > FA_TUNE:
        raise Blocked("FA recheck failed after calibration")

    return cfg.copy(), {
        "status": "TUNED",
        "trace": trace,
        "diagnostic_fa": measured,
        "lag_samples_used": len(errs),
        "lag_status": "ESTIMATED" if errs else "NO_ALARMS_OFFSET_ZERO",
    }


def validate_predictions(preds, n, samples):
    if not isinstance(preds, list) or len(preds) != n:
        raise Blocked("Prediction count/schema mismatch")
    for p in preds:
        if not isinstance(p, dict) or set(p) != {"status", "t_hat"}:
            raise Blocked("Prediction schema mismatch")
        st, t = p["status"], p["t_hat"]
        if st not in ("ONSET", "NO_TRANSITION", "NO_VERDICT"):
            raise Blocked("Unknown prediction status")
        if st == "ONSET":
            if isinstance(t, bool) or not isinstance(t, int) or not 0 <= t < samples:
                raise Blocked("Invalid onset sample")
        elif t is not None:
            raise Blocked("Non-onset prediction has a time")


def check_sources():
    mismatches = []
    for name, expected in EXPECTED.items():
        p = HERE / name
        if not p.is_file() or digest(p) != expected:
            mismatches.append(name)
    if mismatches:
        raise Blocked(
            "SOURCE_MISMATCH: "
            + ", ".join(mismatches)
            + f". Package targets base commit {BASE_COMMIT}; "
            "review changed files and update EXPECTED hashes deliberately "
            "before using this procedure."
        )


def load_modules():
    global G, B, E, R
    import generator as G
    import baseline_detector as B
    import evaluator as E
    import run_blind as R


def canary():
    ok, info = R.leakage_canary()
    if not ok:
        raise Blocked("CANARY_DIRTY: " + json.dumps(info))
    info = dict(info)
    info["numpy"] = np.__version__
    info["platform"] = platform.platform()
    return info


def provenance():
    try:
        commit = subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=HERE,
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        commit = None

    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        np.show_config()

    return {
        "git_commit": commit,
        "python": sys.version,
        "numpy": np.__version__,
        "platform": platform.platform(),
        "numpy_build": buf.getvalue(),
        "source_sha256": {p.name: digest(p) for p in HERE.glob("*.py")},
        "github": {
            k: os.environ.get(k)
            for k in (
                "GITHUB_REPOSITORY",
                "GITHUB_SHA",
                "GITHUB_RUN_ID",
                "GITHUB_RUN_ATTEMPT",
                "GITHUB_WORKFLOW",
                "GITHUB_REF",
            )
        },
    }


def build_capability_matrix(report: dict) -> list[dict]:
    """Flat, machine-readable matrix for later comparison across protocol versions."""
    rows = []
    for stage, data in report.get("stages", {}).items():
        for key, cell in data["cells"].items():
            for method, result in cell.items():
                tr, ct = result["transition"], result["control"]
                rows.append(
                    {
                        "protocol": PROTOCOL_VERSION,
                        "stage": stage,
                        "condition": key,
                        "method": method,
                        "h": result["cfg"]["h"],
                        "lag_comp": result["cfg"]["lag_comp"],
                        "verdict": result["verdict"],
                        "n_eligible": tr["n_eligible"],
                        "n_transition": tr["n"],
                        "hit_rate": tr["hit_tol1.0_t_true"]["rate"],
                        "median_error_Tc": tr["median_abs_err_Tc"],
                        "false_alarm_rate": ct["fa_rate"],
                        "false_alarm_upper": ct["fa_hi"],
                        "reason": result["why"],
                    }
                )
    return rows


def render(report: dict, out: Path) -> None:
    rows = build_capability_matrix(report)

    if rows:
        with (out / "metrics.csv").open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(plain(rows))
        write_json(out / "capability_matrix.json", rows)

    lines = [
        "# XPT — diagnostyczne sprawdzenie baseline'ów",
        "",
        f"**Protocol:** `{PROTOCOL_VERSION}`",
        f"**Status wykonania:** {report['status']}",
        "",
        "**XPT detector: NOT_EVALUATED.**",
        "To nie jest walidacja XPT ani nowa konfirmacja Gate 1.",
        "",
        f"Progi wybierane tylko na diagnostyce (N={report['design']['n_diag']}, "
        f"seed={report['design']['seed_diag']}).",
        "Dalsze zbiory są sprawdzane bez ponownego strojenia.",
        "",
        "Czysty canary sprawdza ograniczony zakres plików i środowiska; "
        "nie dowodzi pełnej izolacji OS.",
        "",
    ]

    if report.get("error"):
        lines += ["## Powód zatrzymania", "", "```text", report["error"], "```", ""]

    if report.get("cfgs"):
        lines += [
            "## Zamrożone konfiguracje",
            "",
            "| Układ | Metoda | h | Korekta czasu (próbki) |",
            "|---|---|---:|---:|",
        ]
        for cond, cfgs in report["cfgs"].items():
            for method, cfg in cfgs.items():
                lines.append(
                    f"| {cond} | {method} | {cfg['h']} | {cfg['lag_comp']} |"
                )

    for stage, _, _ in STAGES:
        selected = [r for r in rows if r["stage"] == stage]
        if not selected:
            continue
        lines += [
            "",
            f"## {stage}",
            "",
            "| Warunek | Metoda | Werdykt | Hit | Mediana błędu T_c | FA | N kwal./wszystkie |",
            "|---|---|---|---:|---:|---:|---:|",
        ]
        for r in selected:
            lines.append(
                f"| {r['condition']} | {r['method']} | {r['verdict']} | "
                f"{r['hit_rate']:.3f} | {r['median_error_Tc']:.3f} | "
                f"{r['false_alarm_rate']:.3f} | "
                f"{r['n_eligible']}/{r['n_transition']} |"
            )

    lines += [
        "",
        "## Jak czytać",
        "",
        "- COMPLETED: procedura wykonana; wynik naukowy znajduje się w tabeli, nie w kolorze workflow.",
        "- STABLE / PARTIAL / INVISIBLE: zdolność lokalizacji onsetu danego baseline'u w danym warunku.",
        "- FALSE_POSITIVE_CANDIDATE: przekroczony budżet alarmów na kontrolach bez przejścia.",
        "- INCONCLUSIVE: za mało kwalifikujących się prób lub zbyt dużo NO_VERDICT.",
        "- Hit liczony na próbach z t_det >= 0; NO_VERDICT w tej grupie liczy się jako nietrafienie.",
        "- T_c to charakterystyczny okres układu, nie uniwersalna sekunda.",
        "- Nie zmieniaj progów po obejrzeniu weryfikacji. Zachowaj ten raport przed kolejną wersją.",
        "",
        f"Artefakty: `capability_matrix.json`, `metrics.csv`, `frozen_configs.json`, `SHA256SUMS.json`.",
        "",
    ]
    (out / "SUMMARY.md").write_text("\n".join(lines), encoding="utf-8")


def self_test() -> int:
    import unittest

    class Checks(unittest.TestCase):
        def test_first_acceptable_threshold(self):
            h, trace = choose_threshold(
                lambda x: {"0.05": 0.01, "0.2": 0.03 if x < 8 else 0.02}
            )
            self.assertEqual(h, 8)
            self.assertEqual(len(trace), 3)
            self.assertIn(h, H_GRID)

        def test_untunable_never_falls_back(self):
            with self.assertRaises(Untunable) as ctx:
                choose_threshold(lambda h: {"0.05": 0.0, "0.2": 0.03})
            self.assertEqual(len(ctx.exception.trace), len(H_GRID))

        def test_nan_cannot_pass(self):
            with self.assertRaises(Untunable):
                choose_threshold(lambda h: {"0.05": float("nan"), "0.2": 0.0})

        def test_prediction_validation(self):
            validate_predictions([{"status": "ONSET", "t_hat": 3}], 1, 10)
            for p in (
                {"status": "ONSET", "t_hat": -1},
                {"status": "NO_TRANSITION", "t_hat": 3},
                {"status": "ONSET", "t_hat": True},
                {"status": "UNKNOWN", "t_hat": None},
            ):
                with self.assertRaises(Blocked):
                    validate_predictions([p], 1, 10)
            with self.assertRaises(Blocked):
                validate_predictions([], 1, 10)

        def test_fixed_reference_and_control_veto(self):
            tr = {
                "eligible_frac": 1,
                "frac_no_verdict": 0,
                "median_abs_err_Tc": 0.1,
                "hit_tol1.0_t_true": {"rate": 1, "lo": 0.95},
                "hit_tol1.0_t_det": {"rate": 0, "lo": 0},
                "oracle_ceiling_primary": 0,
            }
            ct = {"fa_rate": 0, "fa_hi": 0.02, "no_verdict": 0}
            self.assertEqual(E.capability_verdict(tr, ct)[0], "STABLE")
            self.assertEqual(
                E.capability_verdict(tr, dict(ct, fa_rate=0.06))[0],
                "FALSE_POSITIVE_CANDIDATE",
            )

        def test_misses_in_eligible_denominator(self):
            preds = [
                {"status": "ONSET", "t_hat": 100},
                {"status": "NO_VERDICT", "t_hat": None},
            ]
            truth = {
                "t_true": np.array([100, 100]),
                "t_det": {0.05: np.array([100, 100])},
            }
            tr = E.eval_transition(preds, truth, 0.05, 32)
            self.assertEqual(tr["hit_tol1.0_t_true"]["rate"], 0.5)
            self.assertEqual(tr["n_eligible"], 2)

        def test_strict_json(self):
            text = json.dumps(
                plain({"x": np.array([float("nan"), 1.0])}), allow_nan=False
            )
            self.assertEqual(json.loads(text), {"x": [None, 1.0]})

    result = unittest.TextTestRunner(verbosity=2).run(
        unittest.defaultTestLoader.loadTestsFromTestCase(Checks)
    )
    return 0 if result.wasSuccessful() else 1


def execute(out: Path, tune_only: bool = False, seed_diag: int = DEFAULT_SEED_DIAG) -> int:
    started = time.time()
    # Refuse an existing path: no accidental replacement of past evidence.
    out.mkdir(parents=True, exist_ok=False)

    report = {
        "protocol": PROTOCOL_VERSION,
        "status": "RUNNING",
        "label": "DIAGNOSTIC_BASELINE_REPAIR",
        "xpt_detector_status": "NOT_EVALUATED",
        "base_commit": BASE_COMMIT,
        "started_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "design": {
            "n_diag": N_DIAG,
            "seed_diag": seed_diag,
            "fa_tune": FA_TUNE,
            "h_grid": list(H_GRID),
            "stages": STAGES if not tune_only else [],
            "tune_only": tune_only,
        },
        "tuning": {},
        "cfgs": {},
        "stages": {},
    }
    code = 0

    try:
        check_sources()
        load_modules()
        report["provenance"] = provenance()

        archive = out / "sources"
        archive.mkdir()
        for p in HERE.glob("*.py"):
            shutil.copy2(p, archive / p.name)
        for name in ("calibration_report.json", "confirmatory_report.json", "calib.log"):
            p = HERE / name
            if p.exists():
                shutil.copy2(p, archive / ("HISTORICAL_" + name))

        workflow = HERE.parents[1] / ".github" / "workflows" / "xpt-baseline-repair.yml"
        if workflow.exists():
            shutil.copy2(workflow, archive / workflow.name)

        report["canary_pre"] = canary()

        for cond in G.CONDITIONS:
            print("TUNING", cond, flush=True)
            ot, tt = G.make_batch(cond, "transition", N_DIAG, seed_diag)
            oc, _ = G.make_batch(cond, "control", N_DIAG, seed_diag)
            report["tuning"][cond] = {}
            report["cfgs"][cond] = {}

            for method in METHODS:
                try:
                    cfg, detail = tune(method, ot, tt, oc)
                except Untunable as exc:
                    report["tuning"][cond][method] = {
                        "status": "UNTUNABLE",
                        "trace": exc.trace,
                    }
                    raise
                report["cfgs"][cond][method] = cfg
                report["tuning"][cond][method] = detail
                print(" ", method, cfg, "FA", detail["diagnostic_fa"], flush=True)

            write_json(out / "report.json", report)

        write_json(out / "frozen_configs.json", report["cfgs"])
        frozen_hash = digest(out / "frozen_configs.json")
        report["frozen_configs_sha256"] = frozen_hash

        if tune_only:
            report["status"] = "COMPLETED_TUNE_ONLY"
            report["canary_post"] = canary()
            return 0

        raw = out / "predictions_and_truth"
        raw.mkdir()

        for stage, seed, n in STAGES:
            data = {
                "seed": seed,
                "n_trials": n,
                "label": "DIAGNOSTIC_NOT_CONFIRMATORY",
                "cells": {},
            }
            report["stages"][stage] = data

            for cond in G.CONDITIONS:
                print(stage, cond, flush=True)
                ot, tt = G.make_batch(cond, "transition", n, seed)
                oc, _ = G.make_batch(cond, "control", n, seed)

                for nu in G.NOISE_LEVELS:
                    key = f"{cond}|{nu}"
                    cell = data["cells"][key] = {}

                    for method in METHODS:
                        cfg = report["cfgs"][cond][method]
                        pt = R.run_detector(
                            str(HERE / "baseline_detector.py"), ot[nu], cfg
                        )
                        pc = R.run_detector(
                            str(HERE / "baseline_detector.py"), oc[nu], cfg
                        )
                        validate_predictions(pt, n, G.N_SAMPLES)
                        validate_predictions(pc, n, G.N_SAMPLES)

                        tr = E.eval_transition(pt, tt, nu, G.SPT)
                        ct = E.eval_control(pc)
                        label, adjusted, reason = E.capability_verdict(tr, ct)

                        cell[method] = {
                            "cfg": cfg.copy(),
                            "transition": tr,
                            "control": ct,
                            "verdict": label,
                            "adjusted": adjusted,
                            "why": reason,
                        }

                        # Truth persisted only AFTER both detector processes have exited.
                        write_json(
                            raw / f"{stage}_{cond}_{nu}_{method}.json",
                            {
                                "transition_predictions": pt,
                                "control_predictions": pc,
                                "t_true": tt["t_true"],
                                "t_det": tt["t_det"][nu],
                                "observation_sha256": {
                                    "transition": hashlib.sha256(
                                        ot[nu].tobytes()
                                    ).hexdigest(),
                                    "control": hashlib.sha256(
                                        oc[nu].tobytes()
                                    ).hexdigest(),
                                },
                                "observation_shape": list(ot[nu].shape),
                                "observation_dtype": ot[nu].dtype.str,
                            },
                        )
                        print(" ", key, method, label, "FA", ct["fa_rate"], flush=True)

                write_json(out / "report.json", report)
                render(report, out)

        if digest(out / "frozen_configs.json") != frozen_hash:
            raise Blocked("Frozen config file changed after freeze")
        if plain(report["cfgs"]) != json.loads(
            (out / "frozen_configs.json").read_text(encoding="utf-8")
        ):
            raise Blocked("In-memory configurations changed after freeze")

        report["canary_post"] = canary()
        report["status"] = "COMPLETED"

    except Blocked as exc:
        report["status"] = "BLOCKED"
        report["error"] = str(exc)
        code = 2
    except Exception:
        report["status"] = "ERROR"
        report["error"] = traceback.format_exc()
        code = 1
    finally:
        report["runtime_s"] = round(time.time() - started, 3)
        write_json(out / "report.json", report)
        render(report, out)
        manifest = {
            str(p.relative_to(out)): digest(p)
            for p in sorted(out.rglob("*"))
            if p.is_file()
        }
        write_json(out / "SHA256SUMS.json", manifest)
        print(report["status"], "->", out / "SUMMARY.md", flush=True)
        if report.get("error"):
            print(report["error"], file=sys.stderr, flush=True)

    return code


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, help="NEW output directory (must not exist)")
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument(
        "--tune-only",
        action="store_true",
        help="Stop after diagnostic tuning; do not run held-out stages",
    )
    ap.add_argument(
        "--seed-diag",
        type=int,
        default=DEFAULT_SEED_DIAG,
        help=f"Diagnostic seed (default {DEFAULT_SEED_DIAG})",
    )
    args = ap.parse_args()

    if args.self_test:
        check_sources()
        load_modules()
        return self_test()

    if args.out is None:
        ap.error("--out must name a NEW output directory")

    return execute(args.out.resolve(), tune_only=args.tune_only, seed_diag=args.seed_diag)


if __name__ == "__main__":
    sys.exit(main())
