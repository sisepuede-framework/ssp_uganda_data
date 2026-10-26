# RDM tools v2 — first build and evaluation

*Branch `rdm-tools`, 2026-10-12. Design: `rdm_tools_design.md` (draft v2). Run: 30 May 2026.
Numbers from `python -m backend.rdm.eval.evaluate_tools` → `backend/rdm/eval/results/run_2026_05_30.json`;
tests: `python -m pytest tests/rdm` (37 pass: 15 existing, 22 new).*

## What was built

| Piece | File | State |
|---|---|---|
| Batched surrogate (ensembles, derived totals) | `backend/rdm/surrogate.py` | works |
| `exploratory_modeling`, `vulnerability_analysis`, `scenario_discovery`, `trade_off_analysis` | `backend/rdm/tools/technical.py` | work |
| `lever_x_profile`, `output_levers` (v0 / v1) | `backend/rdm/tools/information.py` | work; v1 replies too large (below) |
| `country_context` | `backend/rdm/tools/context.py` (wraps `services/context.py`) | error path works; data not checked (AWS SSO token expired) |
| Harness: 7 schemas, dispatch by version, state, rules, JSONL log | `backend/rdm/harness/` | works with scripted calls; **no LLM loop yet** |
| Evaluation script | `backend/rdm/eval/evaluate_tools.py` | works |
| Run manifest: `crosswalk`, `surrogate_targets` | `backend/rdm/runs/` | added (defaults keep old manifests valid) |

Not built yet: the agent loop (Claude calling the tools), the system prompt, the simulated user.

## What works

- **All seven tools run end to end** in a scripted flow per question category (A–E), in v0 and v1
  (`tests/rdm/test_harness.py`). Technical replies are identical across versions; information
  replies differ.
- **The treatment is clean.** v0 replies contain no value, unit, range, correlation or effect, and
  their lists are alphabetical (never ranked). v1 carries the same relations plus the values
  (`tests/rdm/test_information.py`).
- **Rules are enforced in code:** lever outside [0, 1], unknown ids, an uncertainty fixed at one
  value, a policy named BAU and too few futures are refused with a message the agent can act on.
  Errors come back as `{"error": …}` and are logged.
- **Vulnerability asks instead of guessing.** Without a threshold it returns `needs_threshold`
  with the distribution, so the agent has to ask the user.
- **Scenario discovery recovers a planted rule.** For failures defined as high GDP growth with high
  population, it picks exactly that pair and a box with density > 0.9.
  On a real case (all levers at 0.5, failure = less than a 40% cut vs BAU in 2050, 12% of futures
  fail), it finds GDP growth × agricultural exports: high GDP growth (top quarter) with high exports
  fails 63% of the time and holds 69% of the failures. The pair explains failures almost as well
  as all 13 uncertainties together (balanced accuracy 0.91 vs 0.94).
- **Speed is not an issue.** 4 policies × 500 futures: 1.0 s. Scenario discovery (78 pairs): 0.1 s.
  Information tools: under 0.5 s. Loading the run sample: 1.4 s.
- **Results are stable at the default size.** The share of futures failing one test, over 5 seeds:
  sd 0.014 at 500 futures, 0.007 at 1,000, 0.004 at 2,000.

## The bridge: do the runs and the surrogate agree?

The information tools describe the runs, where every other lever varies at random; the surrogate
experiments set every other lever to 0 (BAU). For each category and each lever linked to it
(149 pairs), the runs' effect (output_levers v1) was compared with the surrogate's effect of
that lever at 1 vs BAU:

- **Same direction in 85% of the non-trivial pairs** (115 pairs with an effect > 0.05 Mt).
- **The ranking of levers agrees** (rank correlation ≥ 0.8) in 18 of 20 categories with three or
  more levers. Exceptions: forest-land sequestration (0.3), forest-land methane (0.4) and
  other not-estimated conversion (0.4).
- **The runs show about 80% of the surrogate's effect** (median ratio 0.79).
- **The disagreements are land-use interactions.** "Set FORESTS SECONDARY MAX" (lever 17) lowers
  forest-land sequestration by 4.9 Mt in the runs, but barely moves it alone on the surrogate (+0.2).
  This is the "marginal vs BAU" difference: the lever's effect depends on what the other land-use
  levers do.

**Consequence:** the information tools point the agent to the right levers in most sectors, but a
v1 value is not the effect the agent will see in an experiment, especially in land use. The tool
replies say values are marginal; the system prompt should say it too.

## What does not work yet

1. **v1 `lever_x_profile` replies are too large.** Median 22,000 characters (~5,500 tokens), maximum
   71,000 (~18,000 tokens), even with the 30-variable cap. A few calls would fill the agent's context.
   v0: median 5,000, maximum 29,000. `output_levers` is fine (v1 median 3,600, maximum 6,200).
   *Proposal:* 3 lever levels (0, 0.5, 1) instead of 5, drop the low-end range, cap variables at 15.
   That should bring the v1 median under ~6,000 characters. Needs your OK, since it changes what v1
   shows.
2. **Units are missing for 267 of the 694 linked variables** (e.g. livestock demand), which then
   show "unknown". A units table from SISEPUEDE's attribute files is needed.
3. **The uncertainties have no real units.** They are reported as positions in their range
   (0 = low end, 1 = high end). Scenario discovery says "GDP growth in the top quarter", not a
   growth rate.
4. **Coverage gaps:**
   - Levers 6 (CLEAN HYDROGEN), 13 (Reduce N2O), 14 (Reduce PFCS) and 16 (Increase SILVOPASTURE) have
     no reportable link. Levers 13 and 14 act on industrial gases outside the 505 crosswalk fields,
     so the surrogate cannot see them either.
   - Levers 5, 32 and 36 move variables but no reportable emission.
   - Uncertainties 59 and 61 (the two elasticities to GDP per capita) move nothing reportable.
5. **Cost signs need the team.** At BAU the surrogate's cost types are fuel +0.05, system +5.0 and
   technical −2.9 billion USD (2050). At full ambition they are +2.2, +9.6 and −14.2. So
   "cost_total" (the sum, sign-flipped) is −2.3 at BAU. The tools report cost as a change vs BAU in
   the same futures, which is consistent, but the sign convention of each cost type should be
   confirmed before the trade-off numbers are shown to users.
6. **`country_context` was not checked against data:** the AWS SSO token had expired (`aws sso login`).

## Next steps

1. Decide the v1 size reduction (item 1) and apply it.
2. Agent loop + system prompt (identical in v0 and v1, no lever effects, explains "marginal").
3. Pilot: 2–3 questions × 3 repetitions in v0 and v1, reading the logs.
4. Units table; cost-sign check with the team; real units for the 13 uncertainties.
