> Start each slide with its existing ## id.
> Write text after the field name and colon. Continue notes on the following lines.
> Use model tags for numbers, for example {co2.petrol.wltc}.
> Empty fields show as placeholders.
> Rebuild with `.venv/bin/python -m pwt.deck`. It warns about any text that won't fit.
> Lines starting with > are notes to you; they never reach the slides. Full guide: docs/deck/README.md.

## title
> Title slide. title: up to ~28 characters per line, wraps onto 2 lines (shrinks if longer). subtitle and byline share one line under it.
title:
subtitle:
byline:
notes:

## sim
> Section opener at La Source. title: ~14 characters per line at full size; longer titles shrink, then wrap onto 2 lines.
title:
notes:

## sim-model
> The model as six boxes. stepN: Name | detail. Name ~13 characters; detail splits at commas onto 2 short lines.
label:
headline:
step1:
step2:
step3:
step4:
step5:
step6:
notes:

## sim-cars
> Real speed traces of the four cycles (drawn by the model). spec.<car>: one short line under each car, ~26 characters.
label:
headline:
spec.petrol:
spec.hybrid:
spec.phev:
spec.bev:
notes:

## sim-changed
> Four tiles. tileN: number | line. Number ~8 characters; the line wraps onto up to 3 lines.
label:
headline:
tile1:
tile2:
tile3:
tile4:
notes:

## cmp
> Section opener at Eau Rouge.
title:
notes:

## cmp-all
> Grouped bars, all 16 results (drawn by the model). headline: one line, ~52 characters; it shrinks a little if longer.
label:
headline:
notes:

## cmp-wltc
> Big bars, WLTC Class 3 (drawn by the model). Tags like {co2.petrol.wltc} put model numbers in your text.
label:
headline:
notes:

## A
> Study A opener at Les Combes.
> Draft by Claude for the study owner to rewrite. Charts: chart:phase-3-storage, chart:phase-3-hybrid, chart:phase-3-plugin (rebuild the data with python -m pwt.sweep).
title: Hybrid sizing
notes: Study A asks how big the battery and the motor of the two hybrids should be.
We swept the battery from 1 to 20 kWh and the motor from 20 to 80 kW, at 150 Wh/kg, on NEDC, WLTC Class 3 and the two generated Francorchamps laps. The strategies stay fixed: the band strategy for the full hybrid and the sheets' rule for the plug-in hybrid.
Three gaps were closed first: storage now loses energy, motor mass grows with power, and sizes above 20C are excluded. The 85 % storage efficiency and the 20C limit are assumptions.
This is a draft by Claude for the study owner to rewrite.

## A-steps
> Study A method as a dataflow chart. node.<name>: Technique | what it achieves (title ~15 characters, detail up to 2 lines of ~24). edge.<from>.<to>: the data on that arrow, ~12 characters.
label: Study A · how the study worked
headline: Data flow from the assignment hybrids to the three charts
node.cars: Hybrids | assignment specs
node.fix: Physical scaling | losses and motor mass make size cost CO2
node.grid: Factorial sweep | tries all 11 packs × 7 motors
node.sim: Backward sim | CO2 from the power each trace needs
node.runs: Sizing runs | phase-3-sizing.csv
node.cycles: Drive cycles | NEDC, WLTC, 2 laps
node.filter: C-rate filter | drops packs too small for the motor
node.argmin: Argmin | best motor at each battery size
node.sizes: Size curves | slides A-2 and A-3
node.sweep: η sensitivity | how much the 85 % assumption matters
node.storage: Strategy runs | phase-3-storage.csv
node.gap: Strategy gap | slide A-1
edge.cars.fix: 2 hybrids
edge.fix.grid: car models
edge.grid.sim: 154 cars
edge.cycles.sim: 4 traces
edge.sim.runs: 616 runs
edge.runs.filter: CO2, flags
edge.filter.argmin: buildable
edge.argmin.sizes: best motors
edge.cars.sweep: full hybrid
edge.sweep.storage: 40 runs
edge.storage.gap: CO2 gap
notes: Read left to right along the top, then down the right side. Parallelograms are inputs and outputs, boxes are processes, cylinders are saved files, and each arrow names the data it carries.
Model fixes: energy into or out of the battery keeps 85 % each way, an assumption close to the 70 % round trip Boretti reports. Motor mass follows the DOE's 1.4 kW/kg traction-drive target, anchored at the sheet's 100 kg at 35 kW; the pack weighs 150 Wh/kg.
Grid sweep: every combination of 11 battery sizes (1–20 kWh) and 7 motor sizes (20–80 kW), for both hybrids.
Backward simulation: each step, the speed trace gives the force and power the wheels need; the strategy splits it between engine and motor. Steps where the engine is short of its full-load curve are flagged.
20C filter and argmin: sizes with motor kW above 20 × battery kWh are dropped, then the lowest-CO2 motor is kept at each battery size.
Bottom row: the assignment full hybrid is rerun with storage efficiency from 80 to 100 %, with the band strategy and with the sheets' rule.
This is a draft by Claude for the study owner to rewrite.

## A-terms
> Glossary. termN: Term | what it means. Term ~20 characters; the meaning wraps onto 2 lines at most.
label: Study A · key terms
headline: Terms used on the next three slides
term1: Band strategy | Aims to hold the battery at 50–70 % charge. Below 50 %, the engine runs at least at its most efficient load and charges the battery.
term2: Sheets' rule | The supplied workbooks' rule: the motor drives while the battery is above 30 % charge, and the engine covers the rest.
term3: Storage efficiency | The share of energy kept each time it goes into or out of the battery, through motor, inverter and battery. Assumed: 85 % each way.
term4: 20C limit | Motor power at most 20 times battery energy, so 80 kW needs at least 4 kWh. An assumption, just above the assignment hybrid's 16.7C.
term5: Best motor | At each battery size, the motor from 20 to 80 kW with the lowest CO2 within the 20C limit, even if its engine falls short.
term6: Engine short | On some steps the engine can't deliver the power the speed trace asks for. Drawn hollow: that CO2 is conditional.
notes: The band strategy also switches to the motor above 70 % charge, and the sheets' rule derates the motor to 90 % once demand exceeds its rating. Both read the engine's efficiency at the power it actually delivers.
This is a draft by Claude for the study owner to rewrite.

## A-1
> Study slot. figure: an image path from the repository root, e.g. docs/phase-3-sizing.png. Leave empty for a dashed frame.
label: Study A · full hybrid · band strategy minus sheets' rule, g CO2/km
headline: With 85 % storage, the band strategy costs CO2 on WLTC, yet only it keeps up
figure: chart:phase-3-storage
notes: The chart shows the band strategy's CO2 minus the sheets' rule's for the same assignment full hybrid, so above zero the band strategy emits more. It shows WLTC Class 3 and Francorchamps sport; NEDC and the eco lap are in docs/phase-3-sizing.md.
With free storage, the band strategy emits less on every cycle. At the assumed 85 % each way it emits more on WLTC Class 3: it charges the battery from the engine, and that energy pays a loss going in and another coming out.
Every point is hollow: the sheets'-rule car's engine is short of the trace on both cycles, at every efficiency, while the band-strategy car never is. Below 30 % charge the sheets' rule stops using the motor, and the 74 kW engine alone can't meet the peaks. So the comparison is conditional, and the band strategy's advantage on the sport lap is partly a car that can drive the lap against one that can't.
At 85 % the band strategy is the shared baseline: {co2.hybrid.wltc} on WLTC Class 3, against {co2.petrol.wltc} for petrol.
This is a draft by Claude for the study owner to rewrite.

## A-2
label: Study A · full hybrid · g CO2/km against battery size, best motor at each size
headline: Full hybrid: WLTC is flat up to 3 kWh; the sport lap wants maximum motor
figure: chart:phase-3-hybrid
notes: Each point is the lowest-CO2 motor that the 20C limit allows at that battery size. The full hybrid runs the band strategy. Each cycle has its own panel and scale; NEDC and the eco lap are in docs/phase-3-sizing.md.
On WLTC Class 3, every pack from 1 to 3 kWh is within about 1 g CO2/km, then CO2 rises with mass. The 1.5 kWh · 30 kW low is not a meaningful optimum; the assignment car's 1.5 kWh · 25 kW is almost as good.
On the sport lap, the lowest point uses the largest motor in the grid, on the smallest pack the 20C limit allows. It is a boundary of the assumptions, not a free optimum: more motor recovers more braking energy. Even there it beats petrol by only a few g CO2/km.
The petrol line on WLTC Class 3 is itself conditional: its engine is short of that trace.
The strategy is not re-tuned for each size, and the engine stays at 74 kW.
This is a draft by Claude for the study owner to rewrite.

## A-3
label: Study A · plug-in hybrid · g CO2/km against battery size, EU grid
headline: Plug-in on the sport lap: past 6 kWh, the pack only adds mass
figure: chart:phase-3-plugin
notes: The chart shows WLTC Class 3 and Francorchamps sport on the EU grid; NEDC, the eco lap and the French grid are in docs/phase-3-sizing.md.
On the sport lap, CO2 falls until the pack covers the lap, at 6 kWh, then rises with mass. Smaller packs are hollow: the engine can't follow the trace. The 6 kWh point also uses the largest motor in the grid.
On WLTC Class 3, CO2 falls all the way to the 20 kWh edge. R101 rewards electric range by construction, so this is a property of the weighting, not a best size. Every WLTC point is hollow, so these values are conditional.
The French grid (not shown) lowers the level but does not change the sizes.
This is a draft by Claude for the study owner to rewrite.

## A-end
> Closing slide. pointN: conclusion | real-world example (conclusion ~45 characters, example up to 2 lines). openN: open question | why it matters. limitN: one model limit, up to 2 short lines.
label: Study A · what we can say, and what we can't
headline: A full hybrid needs a small pack; a plug-in's best pack depends on the trip
point1: A full hybrid needs only a small pack | On WLTC Class 3, CO2 barely moves from 1 to 3 kWh. Toyota's full hybrids carry about 0.75–1.6 kWh.
point2: On hard laps, more motor kept helping | The sport lap's lowest sits at our 80 kW and 20C limits. F1 (2014–2025 rules) pairs 120 kW with 4 MJ per lap.
point3: Storage losses change which strategy wins | At 85 % each way, charging the battery from the engine costs CO2 on WLTC Class 3.
open1: Would a re-tuned band strategy win back WLTC? | Its band and charge target were set without storage losses.
open2: Should the engine shrink as the motor grows? | The engine stays at 74 kW in every size tested.
open3: What pack suits real plug-in trips? | On the sport lap, past 6 kWh the pack only adds mass; real trips vary in length and charging.
limit1: 85 % storage and 20C are assumptions; real hybrids run far above 20C.
limit2: Lows at 80 kW or 20 kWh sit on the grid edge; hollow points are conditional.
limit3: Real plug-ins average 2–4× their type-approval CO2 (ICCT, 2020).
notes: Each point pairs a model result with a real-world comparison, for scale only: they come from outside the model.
Toyota full-hybrid packs: about 0.75 kWh (Li-ion Prius) to 1.6 kWh (RAV4 hybrid). These cars pair about 53–88 kW of motor with them, far above our 20C limit, so that assumption may shape our small-pack answer. Check against the manufacturer's specifications.
F1 power units, 2014–2025 rules: the MGU-K is limited to 120 kW, and the energy store may deploy 4 MJ (about 1.1 kWh) per lap. A rule, not an optimum: shown for the power-to-energy scale. The 2026 rules changed both.
ICCT 2020: Plötz et al., "Real-world usage of plug-in hybrid electric vehicles", found real-world fuel use and CO2 about 2 to 4 times the type-approval values for private cars.
On the sport lap, the band strategy's advantage over the sheets' rule is conditional: the sheets'-rule car can't follow that trace.
This is a draft by Claude for the study owner to rewrite.

## B
title: CO₂ sensitivity
notes: Study B draft for owner review. We varied one factor at a time by ±10% across four powertrains and four fixed driving traces. We changed body mass, drag coefficient, rolling resistance, gear ratios and peak engine efficiency where applicable.
We used the assignment vehicles, the storage-loss scenario and EU electricity at 250 g CO₂/kWh. Each tornado bar spans the two endpoint emissions. The baseline is shown separately.

## B-1
label: WLTC CLASS 3 · PETROL AND FULL HYBRID
headline: Engine efficiency has the largest WLTC effect
figure: chart:study-b-combustion
notes: For a given engine work demand, higher conversion efficiency reduces fuel energy. This sweep scales peak efficiency and holds the curve shape fixed.
The full-hybrid comparison passes the model's engine-power check. The petrol WLTC baseline fails that check, so its ranking is conditional on the requested trace. Hollow markers flag individual endpoints and hatching flags provisional comparisons.

## B-2
label: NEDC AND WLTC CLASS 3 · BATTERY ELECTRIC
headline: The BEV's leading factor changes by cycle
figure: chart:study-b-electric
notes: Rolling resistance leads on NEDC, closely followed by body mass. Drag leads on WLTC, where higher speeds increase aerodynamic force. A longer bar represents a larger CO₂ response to the same percentage change in the input.
The model's flags cover combustion-engine power. BEV motor, battery and thermal limits require a separate feasibility check.

## B-3
label: SPA-FRANCORCHAMPS · PLUG-IN HYBRID
headline: Body mass dominates both PHEV laps
figure: chart:study-b-plugin
notes: Body mass has the largest span on both fixed Spa traces. The sport trace shows a larger mass response, consistent with greater acceleration work and partial energy recovery.
Petrol sport rankings are provisional where the engine cannot meet the requested power. The equal ±10% changes compare modeled sensitivity. Real design decisions also depend on achievable ranges, interactions and costs.

## B-end
> Closing slide. pointN: conclusion | real-world example (conclusion ~45 characters, example up to 2 lines). openN: open question | why it matters. limitN: one model limit, up to 2 short lines.
> Left empty for the Study B owner: conclusions, open questions and limits are theirs to write.
label:
headline:
point1:
point2:
point3:
open1:
open2:
open3:
limit1:
limit2:
limit3:
notes:

## C
> Study C opener at Stavelot.
title: Corner speed
notes: Study C asks how tyre grip and a rear spoiler change corner speed, and what that does to lap time and CO2 on the generated Francorchamps sport lap.
Every car drives the lap the petrol car generates, in the storage-losses scenario.
This is a draft by Claude for the study owner to rewrite.

## C-1
> Study slot. figure: e.g. docs/study-c-lap-time.png, docs/study-c-co2.png.
label: Study C · Francorchamps sport, generated · lap time (s)
headline: More grip shortens the lap; a spoiler slows it
figure: chart:study-c-lap-time
notes: Left, the tyre grip factor from 0.9 to 1.3 on the 12 corners with a set speed. Right, a spoiler from 0 to 0.4 m² of downforce area, with its added drag and mass.
Corner speed grows with the square root of grip, so the car brakes less into each corner and has less speed to rebuild out of it.
The template corners are all slow. Downforce grows with the square of speed, so it adds almost nothing there, while the spoiler's drag and mass cost time on every straight.
The radii here are inferred from the template speeds at a grip of 0.7, the default method.

## C-2
label: Study C · Francorchamps sport, generated · EU CO2 (g CO2/km)
headline: More grip cuts fuel-car CO2; the BEV barely moves
figure: chart:study-c-co2
notes: At baseline the petrol car emits {co2.petrol.sport} on this lap.
Petrol, full hybrid and plug-in hybrid fall with grip and rise with spoiler size.
The battery electric car recovers much of its braking energy, so braking less gains it little, but it still pays for the spoiler's drag.
The order of the four cars does not change.

## C-3
label: Study C · spoiler minus tyres at the same lap time · g CO2/km
headline: At equal lap time, the spoiler always emits more
figure: chart:study-c-comparison
notes: For each spoiler size, the tyre grip factor that gives the same lap time is found, and the two cars' CO2 is compared.
The difference is positive for every car and for all three radius methods: inferred, fitted to the circuit outline, and the driver's line.
Matching on lap time is a provisional rule. Matching on the average corner speed or on one reference corner could change the result.
The spoiler's lift-to-drag ratio and its mass are unsourced assumptions. A more efficient wing, a much larger one or a faster track could change this.

## C-end
> Closing slide. pointN: conclusion | real-world example (conclusion ~45 characters, example up to 2 lines). openN: open question | why it matters. limitN: one model limit, up to 2 short lines.
> Left empty for the Study C owner: conclusions, open questions and limits are theirs to write.
label:
headline:
point1:
point2:
point3:
open1:
open2:
open3:
limit1:
limit2:
limit3:
notes:

## lim
> Section opener at Bus Stop.
title:
notes:

## lim-rows
> Three rows. rowN: limit | why it matters | next step. limit and next step ~28 characters, why ~44.
label:
headline:
row1:
row2:
row3:
notes:

## questions
> Closing slide at the finish line. title ~14 characters per line; subtitle one line.
title:
subtitle:
notes:
