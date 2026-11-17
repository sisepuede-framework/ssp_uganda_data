"""
How many questions does each E3 sub-experiment need? Simulated power of the pre-registered test (arm labels permuted
within question, two-sided, alpha 0.05), 2026-11-17.

Outcome: did the agent reach the variable holding the answer (binary). Questions differ: each has its own baseline
(question random effect) and its own response to the arm (random slope), in logit units. The baseline rates and the
spread between questions are taken from E1/E2 (A4): Map+ on share-type targets reached 2 of 30 (S50, S3, R1, R3, R6
0 of 5; R8 2 of 5).

    /opt/miniconda3/envs/uganda_metamodel_env/bin/python results_analysis/code/power_e3.py
    → results_analysis/power_e3.csv (never overwritten)
"""
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.special import expit, logit

OUT = Path("results_analysis/power_e3.csv")
RNG = np.random.default_rng(20261117)
N_SIM, N_PERM = 600, 600
SD_Q, SD_SLOPE = 1.2, 0.6          # between-question spread of the baseline and of the effect (logit units)

SCENARIOS = {   # contrast: (mean rate in arm A, mean rate in arm B)
    "E3a cause: P 0.07 vs H 0.40": (0.07, 0.40),
    "E3a cause: P 0.07 vs H 0.60": (0.07, 0.60),
    "E3b fix: P 0.07 vs L or T 0.30": (0.07, 0.30),
    "E3b fix: P 0.07 vs L or T 0.50": (0.07, 0.50),
    "E3b placement: L 0.30 vs T 0.50": (0.30, 0.50),
    "E3b placement: L 0.40 vs T 0.70": (0.40, 0.70),
    "E3c wording: general 0.07 vs explicit 0.30": (0.07, 0.30),
    "control: other targets P 0.60 vs H 0.70": (0.60, 0.70),
}


def simulate(pa: float, pb: float, n_q: int, reps: int) -> float:
    la, lb = logit(pa), logit(pb)
    hits = 0
    for _ in range(N_SIM):
        base = la + RNG.normal(0, SD_Q, n_q)
        slope = (lb - la) + RNG.normal(0, SD_SLOPE, n_q)
        ya = RNG.random((n_q, reps)) < expit(base)[:, None]
        yb = RNG.random((n_q, reps)) < expit(base + slope)[:, None]
        y = np.concatenate([ya, yb], axis=1).astype(float)          # n_q × 2reps; first reps = arm A
        obs = y[:, reps:].mean() - y[:, :reps].mean()
        # permute arm labels within each question
        keys = RNG.random((N_PERM, n_q, 2 * reps))
        idx = np.argsort(keys, axis=2)
        yp = np.take_along_axis(np.broadcast_to(y, (N_PERM, n_q, 2 * reps)), idx, axis=2)
        null = yp[:, :, reps:].mean(axis=(1, 2)) - yp[:, :, :reps].mean(axis=(1, 2))
        p = (np.sum(np.abs(null) >= abs(obs) - 1e-12) + 1) / (N_PERM + 1)
        hits += p < 0.05
    return hits / N_SIM


def main():
    if OUT.exists():
        raise SystemExit(f"{OUT} exists; move it before re-running")
    rows = []
    for name, (pa, pb) in SCENARIOS.items():
        for n_q in (8, 12, 16, 20, 24):
            for reps in (3, 5):
                rows.append({"contrast": name, "questions": n_q, "repetitions per arm": reps,
                             "conversations per arm": n_q * reps, "power": simulate(pa, pb, n_q, reps)})
                print(rows[-1], flush=True)
    t = pd.DataFrame(rows)
    t.to_csv(OUT, index=False)
    print(t.pivot_table(index=["contrast", "questions"], columns="repetitions per arm", values="power").round(2))


if __name__ == "__main__":
    main()
