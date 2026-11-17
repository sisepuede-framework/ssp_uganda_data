"""
Simulated power of E4's contrasts on set S (12 share-type questions × 5 or 10 repetitions per arm), 2026-11-17.
Result: 5 repetitions gave 0.35–0.74 for the contrasts that separate the two changes, so S runs 10. Same model
and test as power_e3.py (question random effect and random slope; arm labels permuted within question, two-sided).
Rates are taken from E3 (P reached 0.15, H 0.73, L/T 0.30, SX explicit 0.28). Power at alpha 0.05 and at 0.01 (the
strictest Holm step over the five primary contrasts).

    /opt/miniconda3/envs/uganda_metamodel_env/bin/python results_analysis/code/power_e4.py
    → results_analysis/power_e4.csv (never overwritten)
"""
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.special import expit, logit

OUT = Path("results_analysis/power_e4.csv")
RNG = np.random.default_rng(20261118)
N_SIM, N_PERM = 600, 600
SD_Q, SD_SLOPE = 1.2, 0.6
SCENARIOS = {
    "R vs P (on request helps a lot, as H)": (0.15, 0.70),
    "R vs P (on request helps half as much)": (0.15, 0.40),
    "F vs P (target statement, as SX)": (0.15, 0.30),
    "C vs R (target adds a moderate amount)": (0.40, 0.65),
    "C vs R (target adds a little near the ceiling)": (0.70, 0.85),
    "R vs H (on request loses part of H's gain)": (0.50, 0.73),
}


def simulate(pa, pb, n_q=12, reps=5):
    la, lb = logit(pa), logit(pb)
    ps = []
    for _ in range(N_SIM):
        base = la + RNG.normal(0, SD_Q, n_q)
        slope = (lb - la) + RNG.normal(0, SD_SLOPE, n_q)
        ya = RNG.random((n_q, reps)) < expit(base)[:, None]
        yb = RNG.random((n_q, reps)) < expit(base + slope)[:, None]
        y = np.concatenate([ya, yb], axis=1).astype(float)
        obs = y[:, reps:].mean() - y[:, :reps].mean()
        idx = np.argsort(RNG.random((N_PERM, n_q, 2 * reps)), axis=2)
        yp = np.take_along_axis(np.broadcast_to(y, (N_PERM, n_q, 2 * reps)), idx, axis=2)
        null = yp[:, :, reps:].mean(axis=(1, 2)) - yp[:, :, :reps].mean(axis=(1, 2))
        ps.append((np.sum(np.abs(null) >= abs(obs) - 1e-12) + 1) / (N_PERM + 1))
    ps = np.array(ps)
    return (ps < 0.05).mean(), (ps < 0.01).mean()


def main():
    if OUT.exists():
        raise SystemExit(f"{OUT} exists; move it before re-running")
    rows = []
    for name, (pa, pb) in SCENARIOS.items():
        for reps in (5, 10):
            p05, p01 = simulate(pa, pb, 12, reps)
            rows.append({"contrast": name, "rate A": pa, "rate B": pb, "repetitions per arm": reps,
                         "power alpha 0.05": p05, "power alpha 0.01": p01})
            print(rows[-1], flush=True)
    pd.DataFrame(rows).to_csv(OUT, index=False)


if __name__ == "__main__":
    main()
