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
> Study B opener at Pouhon.
title:
notes:

## B-1
> Study slot. figure: e.g. docs/study-b-combustion.png, docs/study-b-electric.png, docs/study-b-plugin.png.
label:
headline:
figure: chart:study-b-combustion
notes:

## B-2
label:
headline:
figure: chart:study-b-electric
notes:

## B-3
label:
headline:
figure: chart:study-b-plugin
notes:

## C
> Study C opener at Stavelot.
title:
notes:

## C-1
> Study slot. figure: e.g. docs/study-c-lap-time.png, docs/study-c-co2.png.
label:
headline:
figure: chart:study-c-lap-time
notes:

## C-2
label:
headline:
figure: chart:study-c-co2
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
