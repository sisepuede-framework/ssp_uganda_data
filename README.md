# ssp_uganda_data — branch `dmdu-agent`

This branch holds only the AI-agent + surrogate project for the DMDU 2026 paper: an agent that helps non-technical
users explore Uganda's climate-policy questions with a surrogate of SISEPUEDE, through the three RDM components.

The team's other work (`ssp_modeling/`, `data_processing/`, `employment_estimates/`, `inventory_summary_excel/`) is not
on this branch; it stays on `main`, `metamodel` and `rdm-tools`.

| Where | What |
|---|---|
| `metamodel/chatbot_deploy/backend/rdm/` | the agent experiment: tools, harness, evaluation, network |
| `metamodel/chatbot_deploy/docs/` | current documents: question bank v3, plan log (`rdm_network_plan.md`), pre-registration and results; older ones in `docs/archive/` |
| `metamodel/chatbot_deploy/backend/`, `frontend/` | the deployed chatbot that the RDM tools build on |
| `metamodel/surrogate_model_sector/` | the XGBoost surrogate |
| `metamodel/data/` | local run data (not in git) |
