# Deck mockups

These are the throwaway mockups from designing the group deck on 23 November 2026. They are spike code, kept as the visual reference for [the design](../2026-11-23-group-deck-design.md). They are not the build: `pwt.deck` replaces them.

- `png/`: every screen reviewed, in order, from `01-visual-style.png` to `31-main-slides-v7.png`. The agreed look is `24-first-slide-v5.png` (first slide) and `31-main-slides-v7.png` (the whole deck).
- `pages/`: the same screens as standalone HTML pages, which open in a browser.
- `mock*.py`, `ref.py`, `minitest.py`: the generators. Each later mock execs earlier ones, so keep them together.
- `track.json`, `cycles.json`, `co2.json`: the model data the mockups used:
  - the generated laps placed on the circuit by `pwt.trackmap`
  - the four cycles' speed traces
  - the baseline CO2 and `short_steps` from `pwt.sweep.sweep`

Rebuild the whole-deck mockup from the repository root:

```sh
D=docs/superpowers/specs/deck-mockups
.venv/bin/python -I $D/mock16.py $D/track.json $D/cycles.json $D/mock4.py out.html $D/mock10.py $D/mock15.py $D/co2.json
```

The output is a content fragment for the brainstorming viewer. Wrap it like the files in `pages/` to open it on its own.
