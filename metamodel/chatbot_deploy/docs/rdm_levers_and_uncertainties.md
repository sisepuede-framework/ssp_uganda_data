# What the Explorer knows: RDM, the L's and the X's

**Uganda Climate Pathways Explorer — reference document for the technical team**
Status: draft for expert review · Last updated: 28 July 2026

## Why this document exists

The Explorer lets a user change two kinds of things: **what Uganda decides to do** (levers) and
**what the world does to Uganda** (uncertainties). That split is not a UI convention — it is the
core of Robust Decision Making (RDM), the method the Country Development Pathway Model was built to
support.

This document states, in one place, what the chatbot has been told about that structure. Everything
listed here is what the assistant "knows" when it answers a user. If a definition below is wrong or
badly worded, the assistant will repeat it to a policymaker — so this is the document to correct.

Please leave comments directly in the file (or in Word, using the comment tool). The two things most
worth your attention are marked **[EXPERT INPUT NEEDED]**.

---

## 1. What Robust Decision Making is

Conventional analysis *predicts then acts*: estimate the most likely future, then optimise a plan
for it. That works when the future is well characterised. It fails under **deep uncertainty** —
when the parties to a decision do not know, or cannot agree on, the probabilities of the key
uncertainties, or even on the models that relate actions to consequences. Long-horizon climate and
development planning is the standard example: nobody can hand you a probability distribution over
Uganda's 2070 GDP, population, fuel prices, and technology costs.

RDM inverts the order. Instead of asking *"what will happen?"*, it asks:

> **"Which strategies perform acceptably across a very large range of plausible futures — and where
> exactly do they fail?"**

The practical consequences, all of which show up in the Explorer:

- **Many futures, not one forecast.** The model is run over a large ensemble of futures, each one a
  different combination of assumptions.
- **Robustness instead of optimality.** A robust strategy is one that does well enough across many
  futures, rather than best in the single future we happened to assume.
- **Vulnerability, not just performance.** The interesting output is often *which* combinations of
  conditions break a strategy — that is what tells a policymaker what to hedge against.
- **Exploration is the point.** The user is meant to try combinations, including bad ones. This is
  why the tool is an *Explorer*, and why it must answer freely rather than serve six fixed answers.

## 2. XLRM, the framework behind the model

RDM organises a problem into four elements, usually elicited from stakeholders in a workshop and
written on a 2×2 matrix. This is the **XLRM framework** (Lempert, Groves, Popper & Bankes, 2006 —
see References):

| | Meaning |
|---|---|
| **X** — Exogenous uncertainties | Factors outside the decision-maker's control that could still determine whether a strategy succeeds. |
| **L** — Policy levers | The actions decision-makers can actually take. |
| **R** — Relationships | The models linking actions and uncertainties to consequences — how the future evolves. |
| **M** — Metrics / measures | The performance measures used to judge whether an outcome is desirable. |

A **strategy** is a particular setting of the L's. A **future** (or "state of the world") is a
particular setting of the X's. Running one strategy across many futures is the basic RDM experiment,
and it is exactly what the CDPM ensemble contains.

## 3. XLRM as implemented in this tool

### L — Sectoral transitions (54 levers, 16 sectors)

Each lever is a SISEPUEDE *transformation*: a defined change in how a part of Uganda's economy
operates (switch cooking fuels, expand renewable generation, reduce deforestation, improve manure
management, and so on).

- **Scale.** Every lever runs from **0 = no action** (that transformation is not pursued; the sector
  stays on its business-as-usual path) to **1 = maximum ambition** (deployed to its full technically
  feasible extent by 2070). 0.5 is a moderate, partial transition.
- **The transform.** The value the user picks is converted to a physical magnitude by
  `T = 0.9 × x + 0.1`, so an L of 0 still leaves a floor of 0.1 and an L of 1 gives the full 1.0.
- **It is a 2070 target, not a switch.** SISEPUEDE ramps each transformation from its baseline toward
  the 2070 target over roughly 20–30 years. Asking for "maximum ambition in transport" does not
  change 2026; it sets where transport ends up, and how steeply it gets there.
- **They combine.** Any subset of the 54 can be moved at once. The number of distinct combinations is
  enormous, but not unbounded — the tool says "a very large range of pathway combinations", never
  "infinite".

**[EXPERT INPUT NEEDED]** The per-lever descriptions in the catalogue (section 5) are currently generated
automatically from each lever's SISEPUEDE transformation code, which makes them accurate but thin
("*Reduce DEFORESTATION is deployed to its full technically feasible extent by 2070*"). The
assistant quotes these when a user asks what a lever means. The rightmost column of the table is
empty for you to write the description a Ugandan policymaker should actually read.

### X — Country conditions (13 uncertainties)

These are the external conditions Uganda cannot legislate: how fast the economy and population grow,
what fuels and technologies cost, and how strongly demand responds to income.

- **Scale.** Each factor runs from **0 = the low end of its uncertainty range**, through
  **0.5 = the median (central) future**, to **1 = the high end**. When a user says nothing about
  conditions, every X sits at 0.5.
- **These are relative positions, not percentages.** X = 0.8 on GDP growth means "toward the high end
  of the range the model explores", *not* "GDP is 80% higher". This is the single most common
  misreading, and the assistant is instructed to say so.
- **They are never set by a policy request.** Asking for more ambitious transport policy must not
  quietly change GDP growth. The assistant only moves an X when the user explicitly asks about a
  different future ("what if growth is faster?").

### R — The relationships (and where this tool is genuinely new)

There are two layers, and the difference between them is the thing users must understand:

1. **The CDPM itself**, built with the SISEPUEDE framework: the full integrated model of Uganda's
   emissions, costs, and development benefits. Six official pathways have been run through it, and
   those runs are stored. When a user clicks a pathway button, they get that stored run — an
   **official pathway result**. Nothing is estimated.
2. **The metamodel**: a machine-learning model (XGBoost) trained on ~99,000 CDPM simulations. It has
   learned the mapping from (L, X) settings to outcomes well enough to answer combinations that were
   never officially run. Its answers are **metamodel estimates** — available across a very large range
   of combinations, but less granular and less exact than an official simulation.

That pairing is the novelty. The six official pathways were previously readable only as a document.
Here they can be interrogated conversationally *and* extended: a user can ask what happens between
them, beyond them, or under conditions no official pathway assumed. The tool always labels which of
the two produced an answer — the "How I got this answer" panel shows the badge and the steps taken.

### M — What the tool measures

Reported for 2025, 2035, 2040, 2050 and 2070, always against the official BAU pathway, with the
official HBLE pathway drawn as the ambition frontier:

- **Emissions** — net economy-wide emissions, and emissions split across the **23 official inventory
  categories** (the same categories used in Uganda's inventory and the team's Tableau reporting).
- **Costs** — 3 cost types (fuel, system, technical), in billion USD.
- **Development benefits** — 16 benefit types (human health, indoor and outdoor air quality,
  consumer savings, congestion, road safety, crop and livestock value, ecosystem services, and so on),
  in billion USD.
- **Affordability** — cost and benefit as a share of GDP.

**[EXPERT INPUT NEEDED]** Is this the right metric set to put in front of a policymaker, and are
these the labels the team wants used?

## 4. What this means for a user of the Explorer

| The user asks about… | It is a… | And they get… |
|---|---|---|
| One of the six named pathways (BAU, NDC 2.0, NDC 2.5, NDC2 Unconditional, NDC2 Unconditional (Alt), HBLE / Candidate NDC3) | Official pathway | An **official pathway result** — a stored CDPM simulation |
| A different level of ambition in one or more sectors ("only part of the HBLE ambition in transport") | **L question** | A **metamodel estimate** |
| Different country conditions ("faster GDP growth", "higher fuel prices") | **X question** | A **metamodel estimate** |
| Both at once ("ambitious transport under faster growth") | L + X question | A **metamodel estimate** |
| Uganda's current baseline (energy mix, GDP, population, agriculture, transport) | Context question | Retrieved baseline data, not a model run |

The assistant declines, rather than guesses, when a request needs: another country; a metric,
pollutant or sector the model does not produce; years outside 2025–2070; or an intervention with no
corresponding lever.

---

## 5. Full catalogue

Everything below is generated directly from `backend/feature_registry.json` — the same file the
assistant reads when it builds its system prompt. So this section is not a description of what the
chatbot knows; it *is* what the chatbot knows. Regenerate it with:

```bash
python backend/scripts/build_rdm_catalogue.py
```

<!-- BEGIN GENERATED CATALOGUE -->

*Generated from `backend/feature_registry.json` (version 2.0.0, model run 2026-05-30t21;35;56.244639) — 54 policy levers, 13 exogenous uncertainties.*

### Exogenous uncertainties (X) — 13 factors

Scale for every factor: **0 = low end** of its uncertainty range · **0.5 = median (central) future** (the default when the user says nothing) · **1 = high end**. These are positions within the model's range, *not* percentage changes.

*Recognised as* lists the words the assistant matches when a user names the factor in plain language.

| ID | Factor | Domain | Recognised as | Expert description |
|---|---|---|---|---|
| 55 | Agricultural Export Volumes | Macroeconomic / Trade | agricultural, export, volumes, macroeconomic / trade |  |
| 56 | Fossil Fuel Prices | Energy Markets | fossil, fuel, prices, energy markets |  |
| 57 | GDP Growth Trajectory | Macroeconomic | gdp, growth, trajectory, macroeconomic |  |
| 58 | Industrial Output Elasticity (to GDP) | Industry | industrial, output, elasticity, gdp, industry |  |
| 59 | Industrial Product-Use Elasticity (to GDP/cap) | Industry | industrial, product, use, elasticity, gdp, cap, industry |  |
| 60 | Population Growth | Demographics | population, growth, demographics |  |
| 61 | Building Energy-Demand Elasticity (to GDP/cap) | Buildings | building, energy, demand, elasticity, gdp, cap, buildings |  |
| 62 | Battery Storage Capital Cost | Energy Technology | battery, storage, capital, cost, energy technology |  |
| 63 | Coal Power Plant Capital Cost | Energy Technology | coal, power, plant, capital, cost, energy technology |  |
| 64 | Nuclear Power Plant Capital Cost | Energy Technology | nuclear, power, plant, capital, cost, energy technology |  |
| 65 | Geothermal Power Plant Capital Cost | Energy Technology | geothermal, power, plant, capital, cost, energy technology |  |
| 66 | Freight Transport Demand Elasticity | Transport Demand | freight, transport, demand, elasticity, transport demand |  |
| 67 | Passenger Transport Demand Elasticity | Transport Demand | passenger, transport, demand, elasticity, transport demand |  |

### Policy levers (L) — 54 levers across 16 sectors

Scale for every lever: **0 = no action** (business as usual) → **1 = maximum technically feasible deployment by 2070**, reached via a ramp, not a step change.

The *Current wording* column is what the assistant says today; it is generated from the SISEPUEDE transformation code. **Expert description** is empty on purpose — please fill it in.

#### Transportation (11 levers)

| ID | Lever | SISEPUEDE transformation | Current wording at L = 1 | Expert description |
|---|---|---|---|---|
| 32 | Increase EFFICIENCY ELECTRIC | `TX:TRNS:INC_EFFICIENCY_ELECTRIC_STRATEGY_NZ` | Maximum ambition: "Increase EFFICIENCY ELECTRIC" is deployed to its full technically feasible extent by 2070. |  |
| 33 | Increase EFFICIENCY NON ELECTRIC | `TX:TRNS:INC_EFFICIENCY_NON_ELECTRIC_STRATEGY_NZ` | Maximum ambition: "Increase EFFICIENCY NON ELECTRIC" is deployed to its full technically feasible extent by 2070. |  |
| 34 | Increase OCCUPANCY LIGHT DUTY | `TX:TRNS:INC_OCCUPANCY_LIGHT_DUTY_STRATEGY_NZ` | Maximum ambition: "Increase OCCUPANCY LIGHT DUTY" is deployed to its full technically feasible extent by 2070. |  |
| 35 | Shift FUEL LIGHT DUTY | `TX:TRNS:SHIFT_FUEL_LIGHT_DUTY_STRATEGY_NZ` | Maximum ambition: "Shift FUEL LIGHT DUTY" is deployed to its full technically feasible extent by 2070. |  |
| 36 | Shift FUEL MARITIME | `TX:TRNS:SHIFT_FUEL_MARITIME_STRATEGY_NZ` | Maximum ambition: "Shift FUEL MARITIME" is deployed to its full technically feasible extent by 2070. |  |
| 37 | Shift FUEL MEDIUM DUTY | `TX:TRNS:SHIFT_FUEL_MEDIUM_DUTY_STRATEGY_NZ` | Maximum ambition: "Shift FUEL MEDIUM DUTY" is deployed to its full technically feasible extent by 2070. |  |
| 38 | Shift FUEL POWERED BIKES | `TX:TRNS:SHIFT_FUEL_POWERED_BIKES_STRATEGY_NZ` | Maximum ambition: "Shift FUEL POWERED BIKES" is deployed to its full technically feasible extent by 2070. |  |
| 39 | Shift FUEL RAIL | `TX:TRNS:SHIFT_FUEL_RAIL_STRATEGY_NZ` | Maximum ambition: "Shift FUEL RAIL" is deployed to its full technically feasible extent by 2070. |  |
| 40 | Shift MODE FREIGHT | `TX:TRNS:SHIFT_MODE_FREIGHT_STRATEGY_NZ` | Maximum ambition: "Shift MODE FREIGHT" is deployed to its full technically feasible extent by 2070. |  |
| 41 | Shift MODE PASSENGER | `TX:TRNS:SHIFT_MODE_PASSENGER_STRATEGY_NZ` | Maximum ambition: "Shift MODE PASSENGER" is deployed to its full technically feasible extent by 2070. |  |
| 42 | Shift MODE REGIONAL | `TX:TRNS:SHIFT_MODE_REGIONAL_STRATEGY_NZ` | Maximum ambition: "Shift MODE REGIONAL" is deployed to its full technically feasible extent by 2070. |  |

#### Solid Waste (7 levers)

| ID | Lever | SISEPUEDE transformation | Current wording at L = 1 | Expert description |
|---|---|---|---|---|
| 48 | Reduce CONSUMER FOOD WASTE | `TX:WASO:DEC_CONSUMER_FOOD_WASTE_STRATEGY_NZ` | Maximum ambition: "Reduce CONSUMER FOOD WASTE" is deployed to its full technically feasible extent by 2070. |  |
| 49 | Increase ANAEROBIC AND COMPOST | `TX:WASO:INC_ANAEROBIC_AND_COMPOST_STRATEGY_NZ` | Maximum ambition: "Increase ANAEROBIC AND COMPOST" is deployed to its full technically feasible extent by 2070. |  |
| 50 | Increase CAPTURE BIOGAS | `TX:WASO:INC_CAPTURE_BIOGAS_STRATEGY_NZ` | Maximum ambition: "Increase CAPTURE BIOGAS" is deployed to its full technically feasible extent by 2070. |  |
| 51 | Increase ENERGY FROM BIOGAS | `TX:WASO:INC_ENERGY_FROM_BIOGAS_STRATEGY_NZ` | Maximum ambition: "Increase ENERGY FROM BIOGAS" is deployed to its full technically feasible extent by 2070. |  |
| 52 | Increase ENERGY FROM INCINERATION | `TX:WASO:INC_ENERGY_FROM_INCINERATION_STRATEGY_NZ` | Maximum ambition: "Increase ENERGY FROM INCINERATION" is deployed to its full technically feasible extent by 2070. |  |
| 53 | Increase LANDFILLING | `TX:WASO:INC_LANDFILLING_STRATEGY_NZ` | Maximum ambition: "Increase LANDFILLING" is deployed to its full technically feasible extent by 2070. |  |
| 54 | Increase RECYCLING | `TX:WASO:INC_RECYCLING_STRATEGY_NZ` | Maximum ambition: "Increase RECYCLING" is deployed to its full technically feasible extent by 2070. |  |

#### Agriculture (4 levers)

| ID | Lever | SISEPUEDE transformation | Current wording at L = 1 | Expert description |
|---|---|---|---|---|
| 1 | Reduce CH4 RICE | `TX:AGRC:DEC_CH4_RICE_STRATEGY_NZ` | Maximum ambition: "Reduce CH4 RICE" is deployed to its full technically feasible extent by 2070. |  |
| 2 | Reduce LOSSES SUPPLY CHAIN | `TX:AGRC:DEC_LOSSES_SUPPLY_CHAIN_STRATEGY_NZ` | Maximum ambition: "Reduce LOSSES SUPPLY CHAIN" is deployed to its full technically feasible extent by 2070. |  |
| 3 | Increase CONSERVATION AGRICULTURE | `TX:AGRC:INC_CONSERVATION_AGRICULTURE_STRATEGY_NZ` | Maximum ambition: "Increase CONSERVATION AGRICULTURE" is deployed to its full technically feasible extent by 2070. |  |
| 4 | Increase PRODUCTIVITY | `TX:AGRC:INC_PRODUCTIVITY_STRATEGY_NZ` | Maximum ambition: "Increase PRODUCTIVITY" is deployed to its full technically feasible extent by 2070. |  |

#### Buildings & Other Combustion (4 levers)

| ID | Lever | SISEPUEDE transformation | Current wording at L = 1 | Expert description |
|---|---|---|---|---|
| 27 | Reduce DEMAND HEAT | `TX:SCOE:DEC_DEMAND_HEAT_STRATEGY_NZ` | Maximum ambition: "Reduce DEMAND HEAT" is deployed to its full technically feasible extent by 2070. |  |
| 28 | Increase EFFICIENCY APPLIANCE | `TX:SCOE:INC_EFFICIENCY_APPLIANCE_STRATEGY_NZ` | Maximum ambition: "Increase EFFICIENCY APPLIANCE" is deployed to its full technically feasible extent by 2070. |  |
| 29 | Increase EFFICIENCY HEAT | `TX:SCOE:INC_EFFICIENCY_HEAT_NZ` | Maximum ambition: "Increase EFFICIENCY HEAT" is deployed to its full technically feasible extent by 2070. |  |
| 30 | Shift FUEL HEAT | `TX:SCOE:SHIFT_FUEL_HEAT_STRATEGY_NZ` | Maximum ambition: "Shift FUEL HEAT" is deployed to its full technically feasible extent by 2070. |  |

#### Land Use (4 levers)

| ID | Lever | SISEPUEDE transformation | Current wording at L = 1 | Expert description |
|---|---|---|---|---|
| 15 | Reduce DEFORESTATION | `TX:LNDU:DEC_DEFORESTATION_STRATEGY_NZ` | Maximum ambition: "Reduce DEFORESTATION" is deployed to its full technically feasible extent by 2070. |  |
| 16 | Increase SILVOPASTURE | `TX:LNDU:INC_SILVOPASTURE` | Maximum ambition: "Increase SILVOPASTURE" is deployed to its full technically feasible extent by 2070. |  |
| 17 | Set FORESTS SECONDARY MAX | `TX:LNDU:SET_FORESTS_SECONDARY_MAX_NZ` | Maximum ambition: "Set FORESTS SECONDARY MAX" is deployed to its full technically feasible extent by 2070. |  |
| 18 | Set WETLANDS MINIMUM | `TX:LNDU:SET_WETLANDS_MINIMUM_NZ` | Maximum ambition: "Set WETLANDS MINIMUM" is deployed to its full technically feasible extent by 2070. |  |

#### Livestock Manure Management (4 levers)

| ID | Lever | SISEPUEDE transformation | Current wording at L = 1 | Expert description |
|---|---|---|---|---|
| 19 | Increase CAPTURE BIOGAS | `TX:LSMM:INC_CAPTURE_BIOGAS_STRATEGY_NZ` | Maximum ambition: "Increase CAPTURE BIOGAS" is deployed to its full technically feasible extent by 2070. |  |
| 20 | Increase MANAGEMENT CATTLE PIGS | `TX:LSMM:INC_MANAGEMENT_CATTLE_PIGS_STRATEGY_NZ` | Maximum ambition: "Increase MANAGEMENT CATTLE PIGS" is deployed to its full technically feasible extent by 2070. |  |
| 21 | Increase MANAGEMENT OTHER | `TX:LSMM:INC_MANAGEMENT_OTHER_STRATEGY_NZ` | Maximum ambition: "Increase MANAGEMENT OTHER" is deployed to its full technically feasible extent by 2070. |  |
| 22 | Increase MANAGEMENT POULTRY | `TX:LSMM:INC_MANAGEMENT_POULTRY_STRATEGY_NZ` | Maximum ambition: "Increase MANAGEMENT POULTRY" is deployed to its full technically feasible extent by 2070. |  |

#### Electricity (3 levers)

| ID | Lever | SISEPUEDE transformation | Current wording at L = 1 | Expert description |
|---|---|---|---|---|
| 5 | Reduce LOSSES | `TX:ENTC:DEC_LOSSES_STRATEGY_NZ` | Maximum ambition: "Reduce LOSSES" is deployed to its full technically feasible extent by 2070. |  |
| 6 | Target CLEAN HYDROGEN | `TX:ENTC:TARGET_CLEAN_HYDROGEN_STRATEGY_NZ` | Maximum ambition: "Target CLEAN HYDROGEN" is deployed to its full technically feasible extent by 2070. |  |
| 7 | Target RENEWABLE ELEC | `TX:ENTC:TARGET_RENEWABLE_ELEC_STRATEGY_NZ` | Maximum ambition: "Target RENEWABLE ELEC" is deployed to its full technically feasible extent by 2070. |  |

#### Industrial Processes (3 levers)

| ID | Lever | SISEPUEDE transformation | Current wording at L = 1 | Expert description |
|---|---|---|---|---|
| 12 | Reduce CLINKER | `TX:IPPU:DEC_CLINKER_STRATEGY_NZ` | Maximum ambition: "Reduce CLINKER" is deployed to its full technically feasible extent by 2070. |  |
| 13 | Reduce N2O | `TX:IPPU:DEC_N2O_STRATEGY_NZ` | Maximum ambition: "Reduce N2O" is deployed to its full technically feasible extent by 2070. |  |
| 14 | Reduce PFCS | `TX:IPPU:DEC_PFCS_STRATEGY_NZ` | Maximum ambition: "Reduce PFCS" is deployed to its full technically feasible extent by 2070. |  |

#### Water & Wastewater Treatment (3 levers)

| ID | Lever | SISEPUEDE transformation | Current wording at L = 1 | Expert description |
|---|---|---|---|---|
| 45 | Increase TREATMENT INDUSTRIAL | `TX:WALI:INC_TREATMENT_INDUSTRIAL_STRATEGY_NZ` | Maximum ambition: "Increase TREATMENT INDUSTRIAL" is deployed to its full technically feasible extent by 2070. |  |
| 46 | Increase TREATMENT RURAL | `TX:WALI:INC_TREATMENT_RURAL_STRATEGY_NZ` | Maximum ambition: "Increase TREATMENT RURAL" is deployed to its full technically feasible extent by 2070. |  |
| 47 | Increase TREATMENT URBAN | `TX:WALI:INC_TREATMENT_URBAN_STRATEGY_NZ` | Maximum ambition: "Increase TREATMENT URBAN" is deployed to its full technically feasible extent by 2070. |  |

#### Cross-Sector (2 levers)

| ID | Lever | SISEPUEDE transformation | Current wording at L = 1 | Expert description |
|---|---|---|---|---|
| 25 | Increase HEALTHIER DIETS | `TX:PFLO:INC_HEALTHIER_DIETS` | Maximum ambition: "Increase HEALTHIER DIETS" is deployed to its full technically feasible extent by 2070. |  |
| 26 | Increase IND CCS | `TX:PFLO:INC_IND_CCS_STRATEGY_NZ` | Maximum ambition: "Increase IND CCS" is deployed to its full technically feasible extent by 2070. |  |

#### Industrial Energy (2 levers)

| ID | Lever | SISEPUEDE transformation | Current wording at L = 1 | Expert description |
|---|---|---|---|---|
| 10 | Increase EFFICIENCY ENERGY | `TX:INEN:INC_EFFICIENCY_ENERGY_STRATEGY_NZ` | Maximum ambition: "Increase EFFICIENCY ENERGY" is deployed to its full technically feasible extent by 2070. |  |
| 11 | Shift FUEL HEAT | `TX:INEN:SHIFT_FUEL_HEAT_STRATEGY_NZ` | Maximum ambition: "Shift FUEL HEAT" is deployed to its full technically feasible extent by 2070. |  |

#### Livestock (2 levers)

| ID | Lever | SISEPUEDE transformation | Current wording at L = 1 | Expert description |
|---|---|---|---|---|
| 23 | Reduce ENTERIC FERMENTATION | `TX:LVST:DEC_ENTERIC_FERMENTATION_STRATEGY_NZ` | Maximum ambition: "Reduce ENTERIC FERMENTATION" is deployed to its full technically feasible extent by 2070. |  |
| 24 | Increase PRODUCTIVITY | `TX:LVST:INC_PRODUCTIVITY_STRATEGY_NZ` | Maximum ambition: "Increase PRODUCTIVITY" is deployed to its full technically feasible extent by 2070. |  |

#### Wastewater (2 levers)

| ID | Lever | SISEPUEDE transformation | Current wording at L = 1 | Expert description |
|---|---|---|---|---|
| 43 | Increase CAPTURE BIOGAS | `TX:TRWW:INC_CAPTURE_BIOGAS_STRATEGY_NZ` | Maximum ambition: "Increase CAPTURE BIOGAS" is deployed to its full technically feasible extent by 2070. |  |
| 44 | Increase COMPLIANCE SEPTIC | `TX:TRWW:INC_COMPLIANCE_SEPTIC_STRATEGY_NZ` | Maximum ambition: "Increase COMPLIANCE SEPTIC" is deployed to its full technically feasible extent by 2070. |  |

#### Forestry (1 levers)

| ID | Lever | SISEPUEDE transformation | Current wording at L = 1 | Expert description |
|---|---|---|---|---|
| 9 | Increase SEQUESTRATION | `TX:FRST:INCREASE_SEQUESTRATION_NZ` | Maximum ambition: "Increase SEQUESTRATION" is deployed to its full technically feasible extent by 2070. |  |

#### Fugitive Emissions (1 levers)

| ID | Lever | SISEPUEDE transformation | Current wording at L = 1 | Expert description |
|---|---|---|---|---|
| 8 | Reduce LEAKS | `TX:FGTV:DEC_LEAKS_STRATEGY_NZ` | Maximum ambition: "Reduce LEAKS" is deployed to its full technically feasible extent by 2070. |  |

#### Transport Demand (1 levers)

| ID | Lever | SISEPUEDE transformation | Current wording at L = 1 | Expert description |
|---|---|---|---|---|
| 31 | Reduce DEMAND | `TX:TRDE:DEC_DEMAND_STRATEGY_NZ` | Maximum ambition: "Reduce DEMAND" is deployed to its full technically feasible extent by 2070. |  |

<!-- END GENERATED CATALOGUE -->

---

## 6. References

1. RAND Corporation, *Robust Decision Making*, in **Tools for Decision Making under Deep
   Uncertainty** (TL-320). <https://www.rand.org/pubs/tools/TL320/tool/robust-decision-making.html>
2. Lempert, R. J., Groves, D. G., Popper, S. W., & Bankes, S. C. (2006). "A General, Analytic Method
   for Generating Robust Strategies and Narrative Scenarios." *Management Science*, 52(4), 514–528.
   <https://doi.org/10.1287/mnsc.1050.0472> — the source of the XLRM framework. (Note for the client:
   David Groves, who reviewed this tool, is a co-author.)
3. Lempert, R. J. (2019). "Robust Decision Making (RDM)", ch. 2 in Marchau, Walker, Bloemen & Popper
   (eds.), *Decision Making under Deep Uncertainty: From Theory to Practice*, Springer (open access).
   <https://link.springer.com/chapter/10.1007/978-3-030-05252-2_2>
4. weADAPT, *Robust Decision Making: XLRM framework* — a short practitioner explainer.
   <https://weadapt.org/knowledge-base/adaptation-decision-making/xlrm-framework/>
5. SISEPUEDE modelling framework — the model underlying Uganda's Country Development Pathway Model.

## 7. Reviewer notes

Space for the team. Please note who you are and the date.

- 
