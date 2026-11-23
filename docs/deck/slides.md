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
title:
notes:

## A-1
> Study slot. figure: an image path from the repository root, e.g. docs/phase-3-sizing.png. Leave empty for a dashed frame.
label:
headline:
figure:
notes:

## A-2
label:
headline:
figure:
notes:

## A-3
label:
headline:
figure:
notes:

## B
title: CO? sensitivity
notes: Study B draft for owner review. We varied one factor at a time by ?10% across four powertrains and four fixed driving traces. We changed body mass, drag coefficient, rolling resistance, gear ratios and peak engine efficiency where applicable.
We used the assignment vehicles, the storage-loss scenario and EU electricity at 250 g CO?/kWh. Each tornado bar spans the two endpoint emissions. The baseline is shown separately.

## B-1
label: WLTC CLASS 3 ? PETROL AND FULL HYBRID
headline: Engine efficiency has the largest WLTC effect
figure: docs/study-b-combustion.png
notes: For a given engine work demand, higher conversion efficiency reduces fuel energy. This sweep scales peak efficiency and holds the curve shape fixed.
The full-hybrid comparison passes the model's engine-power check. The petrol WLTC baseline fails that check, so its ranking is conditional on the requested trace. Hollow markers flag individual endpoints and hatching flags provisional comparisons.

## B-2
label: NEDC AND WLTC CLASS 3 ? BATTERY ELECTRIC
headline: The BEV's leading factor changes by cycle
figure: docs/study-b-electric.png
notes: Rolling resistance leads on NEDC, closely followed by body mass. Drag leads on WLTC, where higher speeds increase aerodynamic force. A longer bar represents a larger CO? response to the same percentage change in the input.
The model's flags cover combustion-engine power. BEV motor, battery and thermal limits require a separate feasibility check.

## B-3
label: SPA-FRANCORCHAMPS ? PLUG-IN HYBRID
headline: Body mass dominates both PHEV laps
figure: docs/study-b-plugin.png
notes: Body mass has the largest span on both fixed Spa traces. The sport trace shows a larger mass response, consistent with greater acceleration work and partial energy recovery.
Petrol sport rankings are provisional where the engine cannot meet the requested power. The equal ?10% changes compare modeled sensitivity. Real design decisions also depend on achievable ranges, interactions and costs.

## C
> Study C opener at Stavelot.
title:
notes:

## C-1
> Study slot. figure: e.g. docs/study-c-lap-time.png, docs/study-c-co2.png.
label:
headline:
figure:
notes:

## C-2
label:
headline:
figure:
notes:

## C-3
label:
headline:
figure:
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
