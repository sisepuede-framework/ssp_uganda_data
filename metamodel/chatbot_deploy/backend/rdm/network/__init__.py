"""
The SISEPUEDE network: which variables are used to compute which, read from the SISEPUEDE code
(plan and rules: docs/rdm_network_plan.md). Scripts run in two environments:

  aws_columns.py   uganda_metamodel_env   the fields the run has in AWS (from the cached sample)
  inventory.py     ssp_uganda_env         SISEPUEDE's model variables, their fields and attributes

Outputs go to backend/rdm/network/out/.
"""
