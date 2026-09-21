# Archive

## `chatbot_v1/` — the first deployed chatbot (archived 2026-09-08)

The original four-tool app, superseded by `metamodel/chatbot_deploy/`. Kept because it is
the only record of the previous version of the system; nothing outside this directory
referenced it, and it was pinned to the retired `2025-11-12t22;19;28.194097` run.

**Differences from `chatbot_deploy/` at the time of archiving**

| | `chatbot_v1` | `chatbot_deploy` |
|---|---|---|
| Tools | 4 (no `get_pathway_results`) | 5 |
| Sectors | ad-hoc display names | 23 official inventory categories, from the crosswalk |
| Model run | `2025-11-12t22;19;28.194097` | `2026-05-30t21;35;56.244639` |
| `agent.py` | 784 lines | ~1,300 lines, with the DMDU/RDM dialogue policy |
| Baseline | `sector_baseline_2019.json` (its only unique asset) | derived via `sector_crosswalk` |

Do not run it: its S3 index cannot resolve current-run `primary_id`s.
