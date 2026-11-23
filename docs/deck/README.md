# The group deck

The first-draft presentation is built from one text file, [`slides.md`](slides.md). Everything else comes from the model: the track, relief, charts and numbers. The design is in [the spec](../superpowers/specs/2026-11-23-group-deck-design.md).

## Build it

```sh
.venv/bin/pip install -r requirements-deck.txt     # once
.venv/bin/python -m pwt.deck                        # both themes
.venv/bin/python -m pwt.deck --theme dark           # one theme
```

The decks land in `docs/deck/build/` as `group-deck-dark.pptx` and `group-deck-light.pptx`. That folder is not committed, and a rebuild overwrites it. If you edit a `.pptx` by hand, for the final draft, save it somewhere else first.

The build lists any text that is too long to fit, for example `warning: cmp-all.headline is too long to fit; shorten it.`.

## Write in `slides.md`

Each slide starts with `## <id>` followed by its fields. Write after the colon:

```
## cmp-wltc
label: WLTC Class 3 · g CO2/km
headline: On the highway, petrol emits {co2.petrol.wltc}
notes: First line of the speaker notes.
Second line of the notes.
```

- **Empty fields** show as grey italic placeholders, so you can see what's still missing.
- **Notes** can run over several lines. A line that starts with a word and a colon (such as `Source: …`) starts a new field instead, so avoid that inside notes.
- **Lines starting with `>`** are hints to you and never reach the slides.
- **A typo in a slide id or field name** stops the build and names the typo.

### Numbers from the model

Never type a model number. Use a tag, which the build fills in to one decimal with its unit:

| Tag | Gives |
|---|---|
| `{co2.<car>.<cycle>}` | g CO2/km, EU grid |
| `{fuel.<car>.<cycle>}` | l/100 km |
| `{elec.<car>.<cycle>}` | kWh/100 km |

- `<car>` is one of `petrol`, `hybrid`, `phev` or `bev`.
- `<cycle>` is one of `nedc`, `wltc`, `eco` or `sport`. The longer `franco_eco_generated` and `franco_sport_generated` work too.

An unknown tag stops the build.

### How much fits

The build shrinks text that is a little too long, wraps titles onto two lines, and warns when something still doesn't fit. As a guide, at full size:

| Field | About |
|---|---|
| Title slide `title` | 28 characters per line, 2 lines |
| Opener `title` | 14 characters per line at full size; shrinks, then wraps onto 2 lines |
| Content `headline` | 52 characters, one line |
| `label` | 99 characters |
| `tileN` | `number \| line`: number about 8 characters; the line wraps onto 3 lines |
| `rowN` | `limit \| why it matters \| next step`: about 28, 44 and 28 characters |
| `stepN` | `Name \| detail`: name about 13 characters; the detail splits at commas onto 2 lines |
| `spec.<car>` | 26 characters |

### Study slides

Each study has an opener and three slots (`A-1` to `A-3`, `B-1`, …). A slot's `figure:` takes an image path from the repository root. The image is fitted into the middle of the slide.

| Study | Figures already in the repo |
|---|---|
| A, hybrid sizing | `docs/phase-3-sizing.png` |
| B, sensitivity | `docs/study-b-combustion.png`, `docs/study-b-electric.png`, `docs/study-b-plugin.png`, `docs/study-b-provisional.png` |
| C, cornering speed | `docs/study-c-lap-time.png`, `docs/study-c-co2.png` |

These figures were made for the study reports. They have white backgrounds and their own titles, so they will look out of place on the dark theme. Restyling them to match the deck is the owners' call.

## Fonts

The deck is set in **Inter**, and the build looks it up through fontconfig. Inter is installed on the presenting machine (`~/.local/share/fonts/Inter`). The deck's theme font is Inter too, so any text box you add later is Inter. On a machine without Inter, PowerPoint substitutes another font. To show the deck elsewhere, export a PDF.

## The fixed parts

The track pictures, the little lap in the top right (its number is the slide number), the charts, the corner names and distances, the chart footnotes and "model output · first draft" all come from code. Change them in `pwt/deck/`, not in `slides.md`.
