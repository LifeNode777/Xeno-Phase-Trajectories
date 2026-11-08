"""
GATE 1 - run_blind.py  (spec v1.0)  -  closes G10 (blindness by process, not by hash)

Layers of isolation
  1. Interface : the detector receives exactly two files, obs.npy and cfg.json. No seed, no truth, no window bounds.
  2. Memory    : truth is produced by generator.make_batch() inside THIS process and is never written to disk
                 before the detector process has terminated. It is regenerable only from the (secret) seed.
  3. Process   : detector runs as a subprocess, cwd = fresh temp dir, minimal environment, timeout.
  4. Canary    : leakage_canary() runs a probe with the same launch recipe and must find nothing.
For the confirmatory run the executor SHOULD additionally run this under a separate OS user or container
without access to the repo's generator/evaluator and without the seed.
"""
import json
import os
import subprocess
import sys
import tempfile
import numpy as np


def _run(argv_tail, obs, cfg, timeout=3600):
    with tempfile.TemporaryDirectory(prefix="g1_blind_") as d:
        np.save(os.path.join(d, "obs.npy"), obs)
        json.dump(cfg, open(os.path.join(d, "cfg.json"), "w"))
        env = {"PATH": os.environ.get("PATH", ""), "PYTHONHASHSEED": "0"}
        cmd = [sys.executable] + argv_tail(d)
        subprocess.run(cmd, cwd=d, env=env, check=True, timeout=timeout,
                       stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        return json.load(open(os.path.join(d, "pred.json")))


def run_detector(script_path, obs, cfg):
    script = os.path.abspath(script_path)
    return _run(lambda d: [script, "--obs", os.path.join(d, "obs.npy"),
                           "--cfg", os.path.join(d, "cfg.json"), "--out", os.path.join(d, "pred.json")], obs, cfg)


_PROBE = r"""
import os, json, sys, glob
found = []
for root in {os.getcwd(), os.path.dirname(os.getcwd())}:
    for pat in ("*truth*", "*seed*", "*.json"):
        for p in glob.glob(os.path.join(root, "**", pat), recursive=True):
            if os.path.basename(p) not in ("cfg.json", "pred.json"):
                found.append(p)
env_hits = [k for k in os.environ if k != "PYTHONHASHSEED" and ("SEED" in k.upper() or "TRUTH" in k.upper())]
json.dump({"files": sorted(set(found)), "env": env_hits, "argv": sys.argv[1:]}, open("pred.json", "w"))
"""


def leakage_canary():
    """Must return an empty report; otherwise the confirmatory batch is BLOCKED."""
    with tempfile.TemporaryDirectory(prefix="g1_probe_") as pd:
        probe = os.path.join(pd, "probe.py")
        open(probe, "w").write(_PROBE)
        rep = _run(lambda d: [probe, "--obs", os.path.join(d, "obs.npy"), "--cfg", os.path.join(d, "cfg.json"),
                              "--out", os.path.join(d, "pred.json")], np.zeros((1, 8)), {})
    leaked = rep["files"] or rep["env"] or any("seed" in a.lower() or "truth" in a.lower() for a in rep["argv"])
    return (not leaked), rep
