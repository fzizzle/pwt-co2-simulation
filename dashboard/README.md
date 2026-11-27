# Dashboard

A Streamlit app for exploring the workbooks and the model. It is an **internal viewer, not a project deliverable**.

**Hosted:** <https://pwt-co2-simulation-iihscdva9b3woycsyuk7dp.streamlit.app> (invite-only, because the repo is private: ask for your email to be added under *Settings → Sharing*). It sleeps when idle and takes about 30 s to wake, so open it once before a session where you need it.

> [!important]
> **Reboot the app after any change to `pwt/`.** Community Cloud re-runs the page scripts on push but only re-imports modules inside `dashboard/`. The `pwt/` package stays in memory from boot, so a page calling a new function fails with `ImportError` until you reboot (Manage app → ⋮ → Reboot app). Changes inside `dashboard/` hot-reload on their own.

Run it locally:

```sh
.venv/bin/streamlit run dashboard/Overview.py
```

`python -m pwt.build` writes `data/processed/*.parquet` to speed up startup. It is optional and gitignored.

## Pages

`Overview.py` holds only the menu. The pages are in `views/`, and display names, units and number formats come from `labels.py`.

| Group | Page | Shows |
|---|---|---|
| | Home | What the app holds, three links, and the WLTC Class 3 model preview |
| Workbooks | Overview | All twelve runs: the chart first, then the matrix |
| | Category view | Every run in one category: all the petrols, all the NEDC runs, all the sport runs |
| | Trace explorer | Per-step data for one run |
| | Compare | Two runs: their reported figures side by side, traces, then the inputs that differ |
| | Data | The raw datasets as plain tables |
| Model | Model | What `pwt.model` computes: the scenario chart first, the tables in an expander |
| | Track map | A generated Francorchamps lap, animated |
| Studies | Hybrid sizing | Study A's results |
| | CO₂ sensitivity | Study B's results, report and downloads |
| | Cornering speed | Study C's results, report and downloads |

Workbook pages show the supplied figures exactly as reported: no unit conversion, recomputation, corrections or conclusions. Compare shows the two runs' figures side by side and does no arithmetic on them, and a workbook lap's distances stay in metres. Study B and C read their saved results. Hybrid sizing still runs its sweep when the page loads, which is an open decision for Study A's owner. Every table has a CSV download.

## Look and feel

- **Dark for every viewer.** `.streamlit/config.toml` has no `[theme.light]`, so Streamlit never follows a light system setting. A viewer who picks Light in the settings menu gets the charts and chips in `theme.LIGHT`, but Streamlit's stock light controls (red radios, sliders and toggles), because no light theme is configured.
- **Colour means powertrain.** The four deck colours (`theme.CAR_COLOURS`) belong to the cars. Controls use the neutral silver accent `theme.ACCENT` (`#d1d1d6`) with black ink. A trace that belongs to no car, such as the elevation strip, is drawn in neutral ink.
- **One chart helper.** Draw every Plotly figure with `layout.show_chart()`. It hides the Plotly toolbar, which covered legends and corner labels. Pass `toolbar=True` only where zooming helps; `tests/test_chart_chrome.py` fails on a direct `.plotly_chart(` call.
- **Page CSS lives in `layout.inject_css()`.** Its selectors come from the live Streamlit 1.66 DOM: the active segmented control is `button[data-variant="segmented_control"][aria-checked="true"]`, and a multiselect chip is `[data-tag]` in `stMultiSelectTagsContainer`. Check them again after a Streamlit upgrade.
- **Track map without tiles.** `track_charts.lap_map()` draws the lap over the deck's altitude contours (`pwt.deck.track.relief`) on an equal-aspect plane. `basemap="tiles"` brings back the CARTO street map.
- **The local server does not reload `dashboard/` modules.** Restart `streamlit run` before checking a change in the browser.

A category is a slice of the 4 × 3 grid along one field: powertrain (4 categories of 3) or cycle (3 categories of 4). Driving style maps one-to-one onto cycle for now, so "all the sport" is the Francorchamps sport category.

The Data page has five datasets: `Runs` (12 × 74), `Totals` and `Parameters` in long form, `Traces` (676 steps), and `Workbook cells`, one workbook's labelled block exactly as the sheet holds it, with how the reader classified each row. Look there first when a figure elsewhere seems wrong.
