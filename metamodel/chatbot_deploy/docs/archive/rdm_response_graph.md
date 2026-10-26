# The response graph — design idea (draft, 2026-10-06)

*Status: idea agreed in discussion, not built. Decide the format, then prototype on the lever 35
chain. Context: `rdm_tools_design.md`, `rdm_build_plan.md`, `rdm_todo.md` ("Marginal vs
package").*

---

## The problem it solves

Every SISEPUEDE run varies all 54 levers and 13 uncertainties at once (LHC, design 4). The
(L_i, X_j) grid built so far (`backend/rdm/data/store.py`, `Store.pair`) is therefore
**marginal**: each cell averages over random levels of the other 53 levers (mean ≈ 0.5).

- **Valid for:** which outputs a lever moves, direction, relative size, how much an uncertainty
  matters. The LHC columns are independent (max |corr| between any two of the 67 = 0.047 in the
  sample) and the other drivers are balanced across cells (means 0.45–0.54).
- **Not valid as-is for:** absolute levels of a *specific* policy package, and translating a
  target when effects combine. Example: electric light-duty vehicle-km = total light-duty
  vehicle-km (moved by L41 mode shift, L31 demand, L34 occupancy, GDP; linear R² 0.93) × electric
  share (set by L35 alone, exactly linear, r = 1.000). The row "L35 = 0" is not the BAU world:
  it is L35 at BAU with every other lever random.

## The idea: follow the model's own causal chain

```
 L, X (0–1)  ──①──▶  input variables  ──②──▶  drivers (model_output)  ──③──▶  emissions (decomposed_emissions)
 decided or          what the lever SETS        what the system DOES          what is measured
 sampled             (electric share)           (vehicle-km, demand)          (Mt CO₂e)
```

Store a **response graph**: nodes are input variables, drivers and emissions; edges come from the
mappings; each node keeps a small function of its parents. The (L_i, X_j) grid becomes a *view*
computed from the graph, not stored data.

| Link | Behaviour | Format | Example (2026-05-30 run) |
|---|---|---|---|
| ① L → inputs | Deterministic, exact: linear between BAU (L = 0) and the maximum trajectory (L = 1); independent of other levers | Two trajectories per input field (BAU, maximum): value(L) = BAU + L × (max − BAU) | Electric share 2050 = 50% + 21.9 pts × L35 (r = 1.000; L = 0 reproduces BAU, L = 1 reproduces HBLE) — verified for lever 35 only |
| ② inputs + X → drivers | Where things combine, sometimes with interactions | Per driver: its **parents** (the few L and X that move it, from the mapping) and a **fitted function** of them, with R² and residual spread | Total light-duty vkm = f(L41, L31, L34, GDP), R² ≈ 0.93 |
| ③ drivers → emissions | Near-accounting: activity × emission factor | Per emission: the drivers that compose it (structural map) and the relation | Light-duty emissions = Σ vkm by fuel × factor |

## Why it fits the LHC design

- **Link ② is estimable without bias.** The LHC samples every L and X independently, like a
  randomised experiment, so L/X → driver effects are causal and interactions can be estimated with
  explicit terms.
- **It solves "marginal vs package".** A node's function is evaluated at the user's policy values
  for its parents (e.g. L41 = 0.6) with only the X sampled, so the answer belongs to *that*
  package.
- **Compact.** ~660 mapped outputs × 6 years, each with a few parents and a small function. No
  combinatorial grid.
- **Interactions only where they exist.** Detected per node and kept as terms; absent otherwise.

## Interactions: what we learned (2026-10-06)

Lever 35 (light-duty electrification) × lever 7 (renewable target), 2050, regression on ~4,960
sampled runs controlling for the other 65 inputs (effect of L35 from 0 to 1, Mt CO₂e, 95% CI):

| Output | L7 = 0 | L7 = 1 | Interaction |
|---|---|---|---|
| Transport | −1.35 ± 0.06 | −1.29 ± 0.06 | +0.05 ± 0.10 |
| Electricity | +0.11 ± 0.12 | +0.03 ± 0.12 | −0.08 ± 0.21 |
| Total | −1.53 ± 0.46 | −1.19 ± 0.45 | +0.34 ± 0.79 |

The mechanism exists (EVs add ~3.5 PJ ≈ 1 TWh of demand to the grid) but is small for Uganda's
mostly-hydro grid. **Lesson:** a difference of medians between 5 × 5 cells of ~200 runs showed a
spurious +0.54 Mt; interactions need regression or the full 100k store (~4,000 runs per cell).
The second axis of a view can be another lever, not only an uncertainty (`Store.pair` already
accepts it).

## How the tools use it

| Tool | On the graph |
|---|---|
| `get_lever_effects` | walk downstream from L: what it sets, drivers it moves, emissions that change |
| `get_output_drivers` | walk upstream from an emission or variable: its drivers and the L/X behind them |
| `solve_lever_level` | invert a node's function with the package's *other* levers fixed; use link ① directly when the target is a variable one lever sets alone (the electric share) |
| `explain_failure` | compare drivers along the path inside vs outside the failure region |
| (L_i, Z_j) view | evaluate the functions on a grid, Z = an uncertainty or another lever |

## Fit with the experiment and the paper

- **Natural placebo:** v0 gets the graph's **structure** (nodes, edges, units: what moves what);
  v1 gets the **functions** (how much). "Knowing what exists" vs "knowing how it responds".
- **The paper's recommendation made concrete:** the XGBoost maps 67 inputs straight to 258
  outcomes and cannot see drivers; the graph adds the intermediate nodes an agent needs to
  translate and explain.

## Caveats

- Only link ② is causal by design. Drivers are not randomised, so link ③ is defined by the
  structural map and treated as a decomposition.
- Every node reports its R²; where it fits poorly the tool says so and the final number comes
  from `run_experiment` (XGBoost, full policy vector).
- Link ① linearity is verified for lever 35 only; check other levers before relying on it.
- Interaction estimates want the full 100k store; the 5,000-run sample is for prototyping.

## Next steps

1. Decide: response graph as the knowledge layer's data format (vs the stored marginal grid).
2. Prototype the lever 35 chain: L35 → electric share; L41, L31, L34, GDP → total vkm; vkm ×
   share → electric vkm → transport emissions. Test case: "half of private cars electric, with
   passenger mode shift at 0.6" — the package case the marginal grid cannot answer.
3. Interaction screen per lever and output (regression with interaction terms), added to the
   mapping as an "interacts with" column for review.
4. Check link ① linearity on more levers (one land-use, one electricity).
5. Build the full 100k store (Athena CTAS, ≈ $0.73) before fitting the final functions.
