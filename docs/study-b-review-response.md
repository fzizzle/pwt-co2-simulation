# Study B review response

The owner requested both the merge fixes and every research extension on 3 November 2026.
The approved fixed-trace experiment is retained; additional experiments are labelled exploratory.

| Feedback | Resolution |
|---|---|
| Typed-in result numbers | Report prose and PowerPoint use one `result_facts` function built from the current tables. Tests change variants while keeping baselines fixed and check that quoted numbers and leaders change. |
| Infeasible petrol sport comparisons | Explicit provisional section, endpoint shortfall table, hollow markers, hatched comparisons, and rankings that require the baseline and both endpoints to pass. |
| Draft/final decision | Technical work remains an owner-review draft. No claim of final owner approval or merge. |
| Binary footprint | Keep a single replaceable set of review snapshots; extensions are CSV tables rather than a new set of binary outputs for each experiment. One additional figure makes petrol-lap failures visible. |
| Team setup instructions | Windows and macOS/Linux commands appear side by side. |
| Duplicate baseline check | Removed from the report entry point; sweep production and ranking validate at their public boundaries. |
| Duplicate branch | `study-b-sensitivity` is canonical; the old PR/branch is superseded during handover. |
| Per-car laps | Regenerate petrol/hybrid laps per variant and compare rankings after shortfall checks. Retain lap times. The shared generator is engine-limited and cannot validate BEV motor/battery limits; no BEV feasible-lap claim is made. |
| Near-ties | Explicit 2% rule anchored to the largest span in each tie group; no transitive chaining. |
| Elasticities | Signed central and one-sided normalized finite differences in CSV/report. Unlike an exact local derivative, these remain interval-dependent for nonlinear responses. |
| Realistic ranges | Technology-inspired road-load ranges cite DOE/EPA. Body-mass mapping and engine increments are explicit assumptions. Gear range is exploratory because no universal sourced feasible range was established. No vehicle-specific attainability or economic ranking is claimed. |
| Intermediate points | ±5% for every factor; ±2.5%/±7.5% extra gear points; sampled minima and flags reported without claiming continuous optima. |
| Total versus body mass | Reach ±10% total mass by adjusting only body mass; driver, powertrain masses and energy capacities stay fixed. Compare both spans and rankings. |
| Engine curves | Read all three supplied menus and verify agreement; test shape-only and complete-menu alternatives separately. Categorical alternatives are not ranked as if they were ±10% perturbations. |
| French-grid PHEV | Separate spans and rankings from `co2_fr`. A discovered BEV helper bug was also fixed: French electricity must replace the existing electric CO2, not be added to it. EU baselines and model physics remain unchanged. |
| Interactions | 3×3 grids for mass × drag/gears for all cars, plus mass × efficiency for hybrids, on WLTC and sport. Report joint-minus-additive residuals and require all four terms to pass for the passing subset. |

Interpretation still requires owner review. The extensions do not supply a vehicle-cost model,
hybrid-optimal lap generator, BEV capability model, tyre-grip trade-off model or continuous
optimization. These limits are documented rather than hidden behind claims of feasibility.

Validation: 257 tests passed and the existing LibreOffice-dependent test was skipped.
All 16 approved EU baselines still match. All generated CSVs, marked figures and five slides
were regenerated; figure rendering and slide bounds were checked. There are 950 exploratory
simulation rows in addition to the 168 original runs; coefficient menus are exported separately.
