# Group presentation deck: design

**Status:** Design ready for Phred's approval (23 November 2026).

## Intent

The assignment sheet asks for "a ppt presentation with a short introduction made of the general simulation approach which will be completed by each student of the group by a personal study". This design covers the **first draft** of that deck. Phred writes every slide's words. Claude and other agents build the generator, the layouts, the track graphics and every chart and number from the model. The three students then turn the first draft into the final draft together.

## Format

| Item | Value | Source |
|---|---|---|
| Length | **15 minutes, 5 per speaker** | Phred's recollection. The course files say 20 minutes (`30 Examples of personal analysis.docx`). Plan to 15; any spare time goes on a live dashboard demo. Confirm with Nelis. |
| Slides | 3–4 introduction, 10–15 for the rest | `30 Examples of personal analysis.docx`. Phred's call: section-title slides don't count toward this limit. |
| Medium | PowerPoint (`.pptx`), 16:9 | Assignment sheet: "a ppt presentation" |
| Required content | general approach; vehicle comparison including highway ("must be done"); NEDC "for information"; weaknesses, improvements and "what is the next step?"; one personal study per student | Assignment sheet, rules file |

## Running order (23 slides; 28 since 27 November 2026)

On 27 November 2026 the Study A owner added a method slide and a glossary after the Study A opener (`A-steps`, `A-terms`), and a closing slide to every study (`A-end`, `B-end`, `C-end`). The numbers below are the original order. Check the 15-minute limit with the group: 28 slides is about 32 s each.

The mockup `docs/superpowers/specs/deck-mockups/png/` and `mock16.py` show this order slide by slide.

| # | Slide | Layout | Lap position |
|---|---|---|---|
| 1 | Title | whole lap above the title | — |
| 2 | **01 The simulation** | opener | La Source |
| 3 | The model in six steps | flow diagram: speed trace → forces → wheel power → engine/motor → energy → CO2 | |
| 4 | Cars and cycles | four cycle cards with the real speed traces, four cars below | |
| 5 | What we changed | four tiles, each a big number and one line | |
| 6 | **02 Four cars compared** | opener | Eau Rouge |
| 7 | All 16 results | grouped bars, four cars × four cycles | |
| 8 | The highway on its own | four big bars, WLTC Class 3 | |
| 9 | **03 Study A**, hybrid sizing | opener | Les Combes |
| 10–12 | Study A content | three slots | |
| 13 | **04 Study B**, sensitivity | opener | Pouhon |
| 14–16 | Study B content | three slots | |
| 17 | **05 Study C**, cornering speed | opener | Stavelot |
| 18–20 | Study C content | three slots | |
| 21 | **06 Limits and next step** | opener | Bus Stop |
| 22 | Limit → next step | three rows | |
| 23 | Questions?, then the demo if time allows | closing slide | finish line |

Content slides 3–5, 7–8, 10–12, 14–16, 18–20 and 22 are the 16 counted slides. A study slot holds a layout (centred chart, big number or two charts side by side). Phred chooses the layout and writes the words. The figure comes from that study's existing outputs.

## Approaches considered

- **A. Fully generated, no hand edits.** Every slide comes from code. Three people can't then polish the final draft by hand.
- **B. Written directly in PowerPoint.** Fastest start, but a rebuild wipes the text, and quoted numbers are typed by hand.
- **C. Content file + generator (chosen).** Phred writes every slide's words in `docs/deck/slides.md`. `python -m pwt.deck` combines it with the model's numbers and figures and writes the `.pptx`. For the final draft, the group edits a copy of the generated `.pptx` by hand.

## How it is built

- **Content file:** `docs/deck/slides.md`. Each slide is a block giving its layout, label, headline, body fields and speaker notes, under a heading that names it. The generator only reads this file. Empty fields render as grey italic placeholders, as in the mockup.
- **Numbers as tags:** text may contain tags such as `{co2.petrol.wltc}`. The generator fills them from the model, formatted to one decimal with units from `pwt`. An unknown tag stops the build with an error. Numbers never get typed into the content file.
- **Entry point:** `python -m pwt.deck [--theme dark|light]` writes `docs/deck/build/group-deck-<theme>.pptx`, plus the figure images it places. It never writes outside `docs/deck/build/`, so a hand-edited final draft kept elsewhere is safe from rebuilds.
- **Dependencies:** python-pptx and matplotlib, in `requirements-deck.txt`, not in `requirements.txt`. `pwt/` must not import Streamlit.
- **Graphics:** the track openers, the title lap, the little lap and the relief are drawn as vector shapes or as high-resolution images (builder's call), so they match the mockups.
- **Model baseline:** assignment vehicles (`pwt.model.fleet`), the `"storage losses"` scenario (the `pwt.sweep.sweep` default), and the four cycles in `pwt.sweep.CYCLES`. CO2 includes electricity at 250 g/kWh. The plug-in hybrid on NEDC and WLTC is R101-weighted. No shared model values change.
- **Names:** cycles and powertrains use `pwt.sweep.CYCLES` and `pwt.catalog.POWERTRAIN_NAMES`.
- **Feasibility:** any car–cycle result where `short_steps > 0` is drawn as an outlined bar with an asterisk, and the footnote explains it. Today that covers petrol on WLTC and the plug-in hybrid on NEDC and WLTC.
- **Provenance:** every content slide's footer reads "model output · first draft". Speaker notes name the source of each figure (module or doc).
- **Tests (written first):**
  - The baseline reproduces to one decimal.
  - All 16 car–cycle results are present.
  - Tags resolve, and an unknown tag fails.
  - Outlined bars match `short_steps`.
  - The deck has 23 slides in the agreed order.
  - The little-lap label never overlaps the outline.
  - The opener road stays out of the title block and the top-right box.

## Look (agreed with Phred, 23 November 2026)

Apple-like: understated, clean and modern. The throwaway generators in `docs/superpowers/specs/deck-mockups/` are the reference for the look; they are spike code, not the build. `mock16.py` draws the whole deck and builds on `mock15.py`, `mock10.py` and `mock4.py`. The `png/` folder holds every mockup screen we reviewed.

- **One lap of Spa runs through the deck.** It uses the real circuit outline (`pwt.trackmap`), drawn **north up**. It's smoothed and coloured as a road by the generated sport lap's speed: blue (slow), green, yellow, red (fast), over 40–150 km/h.
- **First slide:** the whole lap above a centred title. The bottom of the circuit tucks behind the title and fades out under it.
- **Section openers:** a close-up of the next corner in lap order. It sits on the right and fades into the title on the left. Under the title is a line with the corner name and distance, such as "Les Combes · 2.2 km". The framing is chosen automatically, so the road stays out of the title block and the little-lap corner.
- **Relief:** light contour lines every 2 m, with every fifth line slightly heavier. They're masked so they fade out with distance from the circuit. They're **interpolated from the lap's own altitude** (373–470 m), so the deck labels them as an impression of the terrain. No kerbs, braking boards or tarmac.
- **Content slides:** the chart in the middle, as the focus. Above it are a small grey label and one bold headline. The footer is a single thin line. Value labels sit on the bars, and there's no axis. Bar corners are only slightly rounded (3–5 px at 1600 px wide).
- **Colour per car**, the same on every slide, muted for a mellow look:
  - petrol `#d09539`
  - full hybrid `#4fb267`
  - plug-in hybrid `#b677d5`
  - battery electric `#3984d0`

  The track keeps its full speed colours.
- **Little lap as the page number:** every slide except the title shows the same small whole-lap outline in the same place, **top right**, never cropped. A dot marks where the slide sits on the lap:
  - openers at their corner
  - content slides spread evenly along the stretch to the next section's corner
  - the last slide at the finish line

  The slide number sits beside the dot. It's placed automatically so it never touches the outline. There's no other page number.
- **Type:** Inter (fallback: system sans), bold headlines with tight letter-spacing, grey secondary text.
- **Theme:** dark and light are both built, via `--theme`. Which one to present is decided later, after seeing it projected.

## Ownership (AGENTS.md)

- Phred writes the words of every slide in the first draft. Claude writes no headlines, findings or conclusions. Placeholders stay visibly empty until Phred fills them.
- Each study's slides remain its owner's graded work. The final draft is where the owners of Studies B and C rewrite their slots.
- Charts and numbers come from code only.

## Goals, non-goals, anti-goals

- **Goal:** a first-draft deck that fits 15 minutes, covers every item the sheet requires, matches the agreed look, and rebuilds from code and one content file.
- **Non-goals:**
  - the words themselves (Phred's)
  - the final-draft edits
  - rehearsal
  - the dashboard demo itself
- **Anti-goals:**
  - text or conclusions written for Phred or for a study owner
  - numbers typed by hand
  - a deck that runs past 15 minutes
  - model results presented as the workbooks' own figures
  - an infeasible result ranked without its mark

## Left open

- **Which corner opens which section.** It's a placeholder order for now: start, La Source, Eau Rouge, Les Combes, Pouhon, Stavelot, Bus Stop, finish. It's one list in code, so it's easy to change.
- **Names:** the owners of Studies B and C, and which speaker gives which part. These go in the content file.

## Left to the builder

- How the content file is parsed: a light Markdown-with-fields format.
- How each graphic is drawn in PowerPoint (native shapes or images).
- How the test files are split.
