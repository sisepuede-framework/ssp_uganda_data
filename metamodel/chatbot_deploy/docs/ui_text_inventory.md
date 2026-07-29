# What the tool says — full text inventory

**Uganda Climate Pathways Explorer · generated 29 July 2026**

Every word the tool displays, and — for each button — the exact question it sends to the assistant on the user's behalf. Please comment directly on any wording you would change, using Word's comment tool.

Two things worth knowing while you read:

- The questions under each button are **what the assistant receives**, not what the user sees. They are written to route correctly (naming a pathway exactly, for instance) as well as to read naturally, so if you rewrite one, keep any pathway or sector name intact.
- This document is generated from the running code. If you change wording in it, the change has to be made in the app as well — mark it clearly and we will apply it.

---

## 1. Names and labels used everywhere

**Browser tab title:** Uganda Climate Pathways Explorer

**Tool name, shown in the header:** Uganda Climate Pathways Explorer

**The three tabs, left to right:**

| Tab label | What the input box says on that tab |
|---|---|
| Official pathways ◆ | Ask about one of the six official pathways... |
| Explore ≈ | Describe a combination to explore — an ambition level, a delay, a country condition... |
| How this works | no input on this tab |

**The control that folds the top section away:** “Hide ▴”, becoming “Show pathways ▾”, “Show questions ▾” or “Show reference ▾” depending on the tab.

**Under every answer:** a badge — “◆ Official pathway result” or “≈ Metamodel estimate” — and a collapsible panel headed **“How I got this answer”**, listing the steps that were actually run.

## 2. Tab 1 — Official pathways

**Section heading:** Uganda's six official pathways

**Section text:** Stored simulations from Uganda's Country Development Pathway Model (CDPM), built with SISEPUEDE. The fullest detail in the tool — nothing here is estimated.

**Badge on this section:** ◆ Official pathway result

### 2.1 The six pathway cards

Each card shows a name, a one-line description, its emissions trajectory as a small chart, and its 2070 net emissions with the change against BAU. **The descriptions are drafts and need your sign-off.** Figures come from the stored runs and are shown here for context, not for comment.

| Name shown | Description shown | 2070 figure | vs BAU |
|---|---|---|---|
| BAU | Business as Usual — minimal policy action. The baseline every other pathway is measured against. | 286.8 Mt CO₂e | baseline |
| NDC 2.0 | Uganda's NDC 2.0 ambition, as represented in the CDPM. | 97.9 Mt CO₂e | -65.9% |
| NDC 2.5 | The NDC 2.5 ambition — conditional and unconditional measures together. | 125.8 Mt CO₂e | -56.1% |
| NDC2 Unconditional | The unconditional portion of the NDC ambition — what Uganda commits to without external support. | 263.3 Mt CO₂e | -8.2% |
| NDC2 Uncond. (Alt) | An alternative formulation of the same unconditional set. | 251.5 Mt CO₂e | -12.3% |
| HBLE (NDC 3.0 basis) | High Benefits, Low Emission — the maximum-ambition frontier and the analytical basis for Uganda's NDC 3.0. | 8.2 Mt CO₂e | -97.1% |

**What clicking a card asks the assistant:**

| Card | Question sent |
|---|---|
| BAU | Show me the official Business as Usual (BAU) pathway result — Uganda's emissions, costs, and development benefits under minimal policy action. |
| NDC 2.0 | Show me the official NDC 2.0 pathway result — emissions, costs, and development benefits vs BAU. |
| NDC 2.5 | Show me the official NDC 2.5 pathway result — emissions, costs, and development benefits vs BAU. |
| NDC2 Unconditional | Show me the official NDC2 Unconditional pathway result — emissions, costs, and development benefits vs BAU. |
| NDC2 Unconditional (Alt) | Show me the official NDC2 Unconditional (Alt) pathway result — emissions, costs, and development benefits vs BAU. |
| Candidate NDC3 | Show me the official HBLE pathway result (Candidate NDC3, the analytical basis for Uganda's NDC 3.0) — emissions, costs, and development benefits vs BAU. |

### 2.2 “Or ask across all six”

**Row label:** Or ask across all six

| Button text | Question sent |
|---|---|
| Compare all six on emissions and cost | Compare all six official pathways on emissions and cost. |
| How does HBLE differ from Business as Usual? | How does the HBLE pathway differ from Business as Usual? |
| Which sectors separate NDC 2.5 from HBLE? | Which sectors separate the NDC 2.5 pathway from the HBLE pathway? |

### 2.3 The assistant's opening message on this tab

> **Six official pathways that used to live in a document. Now you can ask them questions — and then go beyond them.**
>
> Pick one above, ask about several at once, or move to Explore for combinations nobody has simulated.

## 3. Tab 2 — Explore

**Section heading:** Explore beyond the six

**Section text:** Combinations that were never officially simulated, estimated by a live metamodel trained on ~99,000 CDPM runs — broader strokes than an official run, always shown against BAU and HBLE.

**Badge on this section:** ≈ Metamodel estimate

### 3.1 Left column — ambition

**Heading:** Ambition — the sectoral transitions  ·  **Counter shown:** 54 L · 16 sectors

**Sub-line:** What Uganda decides: how far and how fast each sector transitions.

| Button text | Question sent |
|---|---|
| What happens if Uganda reaches only part of the HBLE ambition in transport and electricity? | What happens if Uganda reaches only part of the HBLE ambition in transport and electricity? |
| What are the effects of delaying the transition in one or more sectors? | What are the effects of delaying the transition in one or more sectors? |
| Which sectoral transitions contribute most to reductions and development benefits? | Which sectoral transitions contribute most to emissions reductions and development benefits? |

### 3.2 Right column — conditions

**Heading:** Conditions — the country assumptions  ·  **Counter shown:** 13 X

**Sub-line:** What the world decides: the futures Uganda has to deliver in.

| Button text | Question sent |
|---|---|
| How would faster GDP growth affect emissions and implementation costs? | How would faster GDP growth affect emissions and implementation costs? |
| What if fossil fuel prices stay high through 2070? | What if fossil fuel prices stay at the high end of their range through 2070? |
| How does higher population growth change the picture? | How does higher population growth change emissions and costs compared with the median future? |

### 3.3 The small sector chips (left column)

The first 6 sectors are shown, then a chip reading “10 more sectors” reveals the rest. Each chip shows the sector name and its number of levers.

| Chip | Question sent |
|---|---|
| Transportation 11 | What can Uganda change in the Transportation sector, and what would maximum ambition there do to emissions, costs and development benefits? |
| Solid Waste 7 | What can Uganda change in the Solid Waste sector, and what would maximum ambition there do to emissions, costs and development benefits? |
| Agriculture 4 | What can Uganda change in the Agriculture sector, and what would maximum ambition there do to emissions, costs and development benefits? |
| Buildings & Other Combustion 4 | What can Uganda change in the Buildings & Other Combustion sector, and what would maximum ambition there do to emissions, costs and development benefits? |
| Land Use 4 | What can Uganda change in the Land Use sector, and what would maximum ambition there do to emissions, costs and development benefits? |
| Livestock Manure Management 4 | What can Uganda change in the Livestock Manure Management sector, and what would maximum ambition there do to emissions, costs and development benefits? |

### 3.4 The small condition chips (right column)

The first 6 are shown, then “7 more” reveals the rest.

| Chip | Question sent |
|---|---|
| GDP Growth Trajectory | What happens to emissions, costs and development benefits if GDP Growth Trajectory sits at the high end of its uncertainty range instead of the median future? |
| Population Growth | What happens to emissions, costs and development benefits if Population Growth sits at the high end of its uncertainty range instead of the median future? |
| Fossil Fuel Prices | What happens to emissions, costs and development benefits if Fossil Fuel Prices sits at the high end of its uncertainty range instead of the median future? |
| Agricultural Export Volumes | What happens to emissions, costs and development benefits if Agricultural Export Volumes sits at the high end of its uncertainty range instead of the median future? |
| Industrial Output Elasticity (to GDP) | What happens to emissions, costs and development benefits if Industrial Output Elasticity (to GDP) sits at the high end of its uncertainty range instead of the median future? |
| Industrial Product-Use Elasticity (to GDP/cap) | What happens to emissions, costs and development benefits if Industrial Product-Use Elasticity (to GDP/cap) sits at the high end of its uncertainty range instead of the median future? |

### 3.5 The assistant's opening message on this tab

> **Ask for a combination nobody has simulated.**
>
> Set the ambition of any sectoral transition, change any country condition, or both at once — an answer takes about 10–30 seconds.

## 4. Tab 3 — How this works

This tab is a reference document: no conversation on it. Every lever, sector and condition carries an **Ask** button, which opens the question in Explore.

**Section list down the left:** The two answer types · Why it's built this way · Ambition — the levers · Conditions · What you get back

**Page title:** How this works

**Page introduction:** Where each answer comes from, and everything you can change. Ask about anything on this page — the question opens in Explore, with the rest of your conversation.

### The two kinds of answer

- **◆ Official pathway result** — One of the six stored CDPM simulations, read straight from the run. Nothing estimated.

- **≈ Metamodel estimate** — A combination never officially simulated, estimated by a metamodel trained on ~99,000 CDPM runs — broader strokes than an official run.

Each answer carries its badge, and “How I got this answer” beneath it lists the steps actually executed.


### Why it is built this way

Nobody can put probabilities on Uganda's 2070 economy, population or fuel prices. So rather than predict one future, the tool explores many — Robust Decision Making — splitting what you can change in two:

- **L — what Uganda decides** — The sectoral transitions: how far and how fast each part of the economy changes.

- **X — what the world decides** — The conditions Uganda cannot legislate: growth, population, prices, technology costs.


### Ambition — the levers

0 = no action → 1 = maximum feasible deployment by 2070, reached by a ramp over 20–30 years rather than a switch thrown today. Any number can move at once.

**Filter box placeholder:** Filter levers — try “forest”, “cooking”, “transport”


### Conditions — the uncertainties

0 = low end · 0.5 = median future (the default) · 1 = high end. Positions within the model's range — not percentage changes.


### What you get back

Emissions across 23 inventory categories, 3 cost types, 16 development-benefit types, and cost and benefit as a share of GDP — at 2025, 2035, 2040, 2050 and 2070, always against BAU with HBLE as the frontier.

Out of scope: other countries, metrics the model does not produce, years beyond 2025–2070, and interventions with no lever above.


### 4.1 Every lever, and what its Ask button asks

54 levers across 16 sectors. Each sector heading also has an “Ask about this sector” button.

#### Transportation (11 levers)

*“Ask about this sector” sends:* What can Uganda change in the Transportation sector, and what would maximum ambition there do to emissions, costs and development benefits?

| ID | Lever name shown | Question its Ask button sends |
|---|---|---|
| 32 | Increase EFFICIENCY ELECTRIC | What does the "Increase EFFICIENCY ELECTRIC" lever (Transportation) actually change, and what happens to emissions, costs and development benefits at maximum ambition? |
| 33 | Increase EFFICIENCY NON ELECTRIC | What does the "Increase EFFICIENCY NON ELECTRIC" lever (Transportation) actually change, and what happens to emissions, costs and development benefits at maximum ambition? |
| 34 | Increase OCCUPANCY LIGHT DUTY | What does the "Increase OCCUPANCY LIGHT DUTY" lever (Transportation) actually change, and what happens to emissions, costs and development benefits at maximum ambition? |
| 35 | Shift FUEL LIGHT DUTY | What does the "Shift FUEL LIGHT DUTY" lever (Transportation) actually change, and what happens to emissions, costs and development benefits at maximum ambition? |
| 36 | Shift FUEL MARITIME | What does the "Shift FUEL MARITIME" lever (Transportation) actually change, and what happens to emissions, costs and development benefits at maximum ambition? |
| 37 | Shift FUEL MEDIUM DUTY | What does the "Shift FUEL MEDIUM DUTY" lever (Transportation) actually change, and what happens to emissions, costs and development benefits at maximum ambition? |
| 38 | Shift FUEL POWERED BIKES | What does the "Shift FUEL POWERED BIKES" lever (Transportation) actually change, and what happens to emissions, costs and development benefits at maximum ambition? |
| 39 | Shift FUEL RAIL | What does the "Shift FUEL RAIL" lever (Transportation) actually change, and what happens to emissions, costs and development benefits at maximum ambition? |
| 40 | Shift MODE FREIGHT | What does the "Shift MODE FREIGHT" lever (Transportation) actually change, and what happens to emissions, costs and development benefits at maximum ambition? |
| 41 | Shift MODE PASSENGER | What does the "Shift MODE PASSENGER" lever (Transportation) actually change, and what happens to emissions, costs and development benefits at maximum ambition? |
| 42 | Shift MODE REGIONAL | What does the "Shift MODE REGIONAL" lever (Transportation) actually change, and what happens to emissions, costs and development benefits at maximum ambition? |

#### Solid Waste (7 levers)

*“Ask about this sector” sends:* What can Uganda change in the Solid Waste sector, and what would maximum ambition there do to emissions, costs and development benefits?

| ID | Lever name shown | Question its Ask button sends |
|---|---|---|
| 48 | Reduce CONSUMER FOOD WASTE | What does the "Reduce CONSUMER FOOD WASTE" lever (Solid Waste) actually change, and what happens to emissions, costs and development benefits at maximum ambition? |
| 49 | Increase ANAEROBIC AND COMPOST | What does the "Increase ANAEROBIC AND COMPOST" lever (Solid Waste) actually change, and what happens to emissions, costs and development benefits at maximum ambition? |
| 50 | Increase CAPTURE BIOGAS | What does the "Increase CAPTURE BIOGAS" lever (Solid Waste) actually change, and what happens to emissions, costs and development benefits at maximum ambition? |
| 51 | Increase ENERGY FROM BIOGAS | What does the "Increase ENERGY FROM BIOGAS" lever (Solid Waste) actually change, and what happens to emissions, costs and development benefits at maximum ambition? |
| 52 | Increase ENERGY FROM INCINERATION | What does the "Increase ENERGY FROM INCINERATION" lever (Solid Waste) actually change, and what happens to emissions, costs and development benefits at maximum ambition? |
| 53 | Increase LANDFILLING | What does the "Increase LANDFILLING" lever (Solid Waste) actually change, and what happens to emissions, costs and development benefits at maximum ambition? |
| 54 | Increase RECYCLING | What does the "Increase RECYCLING" lever (Solid Waste) actually change, and what happens to emissions, costs and development benefits at maximum ambition? |

#### Agriculture (4 levers)

*“Ask about this sector” sends:* What can Uganda change in the Agriculture sector, and what would maximum ambition there do to emissions, costs and development benefits?

| ID | Lever name shown | Question its Ask button sends |
|---|---|---|
| 1 | Reduce CH4 RICE | What does the "Reduce CH4 RICE" lever (Agriculture) actually change, and what happens to emissions, costs and development benefits at maximum ambition? |
| 2 | Reduce LOSSES SUPPLY CHAIN | What does the "Reduce LOSSES SUPPLY CHAIN" lever (Agriculture) actually change, and what happens to emissions, costs and development benefits at maximum ambition? |
| 3 | Increase CONSERVATION AGRICULTURE | What does the "Increase CONSERVATION AGRICULTURE" lever (Agriculture) actually change, and what happens to emissions, costs and development benefits at maximum ambition? |
| 4 | Increase PRODUCTIVITY | What does the "Increase PRODUCTIVITY" lever (Agriculture) actually change, and what happens to emissions, costs and development benefits at maximum ambition? |

#### Buildings & Other Combustion (4 levers)

*“Ask about this sector” sends:* What can Uganda change in the Buildings & Other Combustion sector, and what would maximum ambition there do to emissions, costs and development benefits?

| ID | Lever name shown | Question its Ask button sends |
|---|---|---|
| 27 | Reduce DEMAND HEAT | What does the "Reduce DEMAND HEAT" lever (Buildings & Other Combustion) actually change, and what happens to emissions, costs and development benefits at maximum ambition? |
| 28 | Increase EFFICIENCY APPLIANCE | What does the "Increase EFFICIENCY APPLIANCE" lever (Buildings & Other Combustion) actually change, and what happens to emissions, costs and development benefits at maximum ambition? |
| 29 | Increase EFFICIENCY HEAT | What does the "Increase EFFICIENCY HEAT" lever (Buildings & Other Combustion) actually change, and what happens to emissions, costs and development benefits at maximum ambition? |
| 30 | Shift FUEL HEAT | What does the "Shift FUEL HEAT" lever (Buildings & Other Combustion) actually change, and what happens to emissions, costs and development benefits at maximum ambition? |

#### Land Use (4 levers)

*“Ask about this sector” sends:* What can Uganda change in the Land Use sector, and what would maximum ambition there do to emissions, costs and development benefits?

| ID | Lever name shown | Question its Ask button sends |
|---|---|---|
| 15 | Reduce DEFORESTATION | What does the "Reduce DEFORESTATION" lever (Land Use) actually change, and what happens to emissions, costs and development benefits at maximum ambition? |
| 16 | Increase SILVOPASTURE | What does the "Increase SILVOPASTURE" lever (Land Use) actually change, and what happens to emissions, costs and development benefits at maximum ambition? |
| 17 | Set FORESTS SECONDARY MAX | What does the "Set FORESTS SECONDARY MAX" lever (Land Use) actually change, and what happens to emissions, costs and development benefits at maximum ambition? |
| 18 | Set WETLANDS MINIMUM | What does the "Set WETLANDS MINIMUM" lever (Land Use) actually change, and what happens to emissions, costs and development benefits at maximum ambition? |

#### Livestock Manure Management (4 levers)

*“Ask about this sector” sends:* What can Uganda change in the Livestock Manure Management sector, and what would maximum ambition there do to emissions, costs and development benefits?

| ID | Lever name shown | Question its Ask button sends |
|---|---|---|
| 19 | Increase CAPTURE BIOGAS | What does the "Increase CAPTURE BIOGAS" lever (Livestock Manure Management) actually change, and what happens to emissions, costs and development benefits at maximum ambition? |
| 20 | Increase MANAGEMENT CATTLE PIGS | What does the "Increase MANAGEMENT CATTLE PIGS" lever (Livestock Manure Management) actually change, and what happens to emissions, costs and development benefits at maximum ambition? |
| 21 | Increase MANAGEMENT OTHER | What does the "Increase MANAGEMENT OTHER" lever (Livestock Manure Management) actually change, and what happens to emissions, costs and development benefits at maximum ambition? |
| 22 | Increase MANAGEMENT POULTRY | What does the "Increase MANAGEMENT POULTRY" lever (Livestock Manure Management) actually change, and what happens to emissions, costs and development benefits at maximum ambition? |

#### Electricity (3 levers)

*“Ask about this sector” sends:* What can Uganda change in the Electricity sector, and what would maximum ambition there do to emissions, costs and development benefits?

| ID | Lever name shown | Question its Ask button sends |
|---|---|---|
| 5 | Reduce LOSSES | What does the "Reduce LOSSES" lever (Electricity) actually change, and what happens to emissions, costs and development benefits at maximum ambition? |
| 6 | Target CLEAN HYDROGEN | What does the "Target CLEAN HYDROGEN" lever (Electricity) actually change, and what happens to emissions, costs and development benefits at maximum ambition? |
| 7 | Target RENEWABLE ELEC | What does the "Target RENEWABLE ELEC" lever (Electricity) actually change, and what happens to emissions, costs and development benefits at maximum ambition? |

#### Industrial Processes (3 levers)

*“Ask about this sector” sends:* What can Uganda change in the Industrial Processes sector, and what would maximum ambition there do to emissions, costs and development benefits?

| ID | Lever name shown | Question its Ask button sends |
|---|---|---|
| 12 | Reduce CLINKER | What does the "Reduce CLINKER" lever (Industrial Processes) actually change, and what happens to emissions, costs and development benefits at maximum ambition? |
| 13 | Reduce N2O | What does the "Reduce N2O" lever (Industrial Processes) actually change, and what happens to emissions, costs and development benefits at maximum ambition? |
| 14 | Reduce PFCS | What does the "Reduce PFCS" lever (Industrial Processes) actually change, and what happens to emissions, costs and development benefits at maximum ambition? |

#### Water & Wastewater Treatment (3 levers)

*“Ask about this sector” sends:* What can Uganda change in the Water & Wastewater Treatment sector, and what would maximum ambition there do to emissions, costs and development benefits?

| ID | Lever name shown | Question its Ask button sends |
|---|---|---|
| 45 | Increase TREATMENT INDUSTRIAL | What does the "Increase TREATMENT INDUSTRIAL" lever (Water & Wastewater Treatment) actually change, and what happens to emissions, costs and development benefits at maximum ambition? |
| 46 | Increase TREATMENT RURAL | What does the "Increase TREATMENT RURAL" lever (Water & Wastewater Treatment) actually change, and what happens to emissions, costs and development benefits at maximum ambition? |
| 47 | Increase TREATMENT URBAN | What does the "Increase TREATMENT URBAN" lever (Water & Wastewater Treatment) actually change, and what happens to emissions, costs and development benefits at maximum ambition? |

#### Cross-Sector (2 levers)

*“Ask about this sector” sends:* What can Uganda change in the Cross-Sector sector, and what would maximum ambition there do to emissions, costs and development benefits?

| ID | Lever name shown | Question its Ask button sends |
|---|---|---|
| 25 | Increase HEALTHIER DIETS | What does the "Increase HEALTHIER DIETS" lever (Cross-Sector) actually change, and what happens to emissions, costs and development benefits at maximum ambition? |
| 26 | Increase IND CCS | What does the "Increase IND CCS" lever (Cross-Sector) actually change, and what happens to emissions, costs and development benefits at maximum ambition? |

#### Industrial Energy (2 levers)

*“Ask about this sector” sends:* What can Uganda change in the Industrial Energy sector, and what would maximum ambition there do to emissions, costs and development benefits?

| ID | Lever name shown | Question its Ask button sends |
|---|---|---|
| 10 | Increase EFFICIENCY ENERGY | What does the "Increase EFFICIENCY ENERGY" lever (Industrial Energy) actually change, and what happens to emissions, costs and development benefits at maximum ambition? |
| 11 | Shift FUEL HEAT | What does the "Shift FUEL HEAT" lever (Industrial Energy) actually change, and what happens to emissions, costs and development benefits at maximum ambition? |

#### Livestock (2 levers)

*“Ask about this sector” sends:* What can Uganda change in the Livestock sector, and what would maximum ambition there do to emissions, costs and development benefits?

| ID | Lever name shown | Question its Ask button sends |
|---|---|---|
| 23 | Reduce ENTERIC FERMENTATION | What does the "Reduce ENTERIC FERMENTATION" lever (Livestock) actually change, and what happens to emissions, costs and development benefits at maximum ambition? |
| 24 | Increase PRODUCTIVITY | What does the "Increase PRODUCTIVITY" lever (Livestock) actually change, and what happens to emissions, costs and development benefits at maximum ambition? |

#### Wastewater (2 levers)

*“Ask about this sector” sends:* What can Uganda change in the Wastewater sector, and what would maximum ambition there do to emissions, costs and development benefits?

| ID | Lever name shown | Question its Ask button sends |
|---|---|---|
| 43 | Increase CAPTURE BIOGAS | What does the "Increase CAPTURE BIOGAS" lever (Wastewater) actually change, and what happens to emissions, costs and development benefits at maximum ambition? |
| 44 | Increase COMPLIANCE SEPTIC | What does the "Increase COMPLIANCE SEPTIC" lever (Wastewater) actually change, and what happens to emissions, costs and development benefits at maximum ambition? |

#### Forestry (1 levers)

*“Ask about this sector” sends:* What can Uganda change in the Forestry sector, and what would maximum ambition there do to emissions, costs and development benefits?

| ID | Lever name shown | Question its Ask button sends |
|---|---|---|
| 9 | Increase SEQUESTRATION | What does the "Increase SEQUESTRATION" lever (Forestry) actually change, and what happens to emissions, costs and development benefits at maximum ambition? |

#### Fugitive Emissions (1 levers)

*“Ask about this sector” sends:* What can Uganda change in the Fugitive Emissions sector, and what would maximum ambition there do to emissions, costs and development benefits?

| ID | Lever name shown | Question its Ask button sends |
|---|---|---|
| 8 | Reduce LEAKS | What does the "Reduce LEAKS" lever (Fugitive Emissions) actually change, and what happens to emissions, costs and development benefits at maximum ambition? |

#### Transport Demand (1 levers)

*“Ask about this sector” sends:* What can Uganda change in the Transport Demand sector, and what would maximum ambition there do to emissions, costs and development benefits?

| ID | Lever name shown | Question its Ask button sends |
|---|---|---|
| 31 | Reduce DEMAND | What does the "Reduce DEMAND" lever (Transport Demand) actually change, and what happens to emissions, costs and development benefits at maximum ambition? |

### 4.2 Every condition, and what its Ask button asks

| ID | Name shown | Domain shown | Question its Ask button sends |
|---|---|---|---|
| 55 | Agricultural Export Volumes | Macroeconomic / Trade | What happens to emissions, costs and development benefits if Agricultural Export Volumes sits at the high end of its uncertainty range instead of the median future? |
| 56 | Fossil Fuel Prices | Energy Markets | What happens to emissions, costs and development benefits if Fossil Fuel Prices sits at the high end of its uncertainty range instead of the median future? |
| 57 | GDP Growth Trajectory | Macroeconomic | What happens to emissions, costs and development benefits if GDP Growth Trajectory sits at the high end of its uncertainty range instead of the median future? |
| 58 | Industrial Output Elasticity (to GDP) | Industry | What happens to emissions, costs and development benefits if Industrial Output Elasticity (to GDP) sits at the high end of its uncertainty range instead of the median future? |
| 59 | Industrial Product-Use Elasticity (to GDP/cap) | Industry | What happens to emissions, costs and development benefits if Industrial Product-Use Elasticity (to GDP/cap) sits at the high end of its uncertainty range instead of the median future? |
| 60 | Population Growth | Demographics | What happens to emissions, costs and development benefits if Population Growth sits at the high end of its uncertainty range instead of the median future? |
| 61 | Building Energy-Demand Elasticity (to GDP/cap) | Buildings | What happens to emissions, costs and development benefits if Building Energy-Demand Elasticity (to GDP/cap) sits at the high end of its uncertainty range instead of the median future? |
| 62 | Battery Storage Capital Cost | Energy Technology | What happens to emissions, costs and development benefits if Battery Storage Capital Cost sits at the high end of its uncertainty range instead of the median future? |
| 63 | Coal Power Plant Capital Cost | Energy Technology | What happens to emissions, costs and development benefits if Coal Power Plant Capital Cost sits at the high end of its uncertainty range instead of the median future? |
| 64 | Nuclear Power Plant Capital Cost | Energy Technology | What happens to emissions, costs and development benefits if Nuclear Power Plant Capital Cost sits at the high end of its uncertainty range instead of the median future? |
| 65 | Geothermal Power Plant Capital Cost | Energy Technology | What happens to emissions, costs and development benefits if Geothermal Power Plant Capital Cost sits at the high end of its uncertainty range instead of the median future? |
| 66 | Freight Transport Demand Elasticity | Transport Demand | What happens to emissions, costs and development benefits if Freight Transport Demand Elasticity sits at the high end of its uncertainty range instead of the median future? |
| 67 | Passenger Transport Demand Elasticity | Transport Demand | What happens to emissions, costs and development benefits if Passenger Transport Demand Elasticity sits at the high end of its uncertainty range instead of the median future? |

## 5. Labels inside the charts

**Panel titles:** “Business as Usual” (left) and “Selected pathway” (right); the cost chart is titled “Annual Cost & Benefit by Year (Selected pathway)”. **Axis labels:** “Mt CO₂e / yr” and “Billion USD / yr”. **Reference lines:** “Real BAU net” and “HBLE net (frontier)”.

**The 23 emission categories in the legend:** Agriculture and Managed Soil · Carbon Capture Industries · Commercial · Deforestation · Electricity and Heat Generation · Forest Land - Removals · Forest Land - Sequestration · Forest Land Methane · Fuel Production · Fugitive Emissions · IPPU · Industrial Combustion · Livestock · Other Combustion · Other Land Use Conversion · Other Not Estimated Conversion · Other Not Estimated Sequestration · Other Not Estimated Soils · Residential · Solid Waste · Transportation · Wastewater Treatment · Wetlands

**The cost and benefit types in the legend:** Air Quality · Human Health · Reduced Congestion · Road Safety · Consumer Savings · Technical Savings · Crop Value · Livestock Value · Industrial Value · Ecosystem Services · Environmental Pollution · Land Pollution · Water Pollution · Sector-Specific · Grasslands · Wetlands · Technical Cost · System Cost · Fuel Cost

