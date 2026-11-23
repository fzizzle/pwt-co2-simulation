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
| The workbooks | Overview | All twelve runs, one table and one chart |
| | Category view | Every run in one category: all the petrols, all the NEDC runs, all the sport runs |
| | Trace Explorer | Per-step data for one run |
| | Compare | Two runs, with their differing inputs listed first |
| | Data | The raw datasets as plain tables |
| The model | Model | What `pwt.model` computes, including the five-scenario comparison |
| | Track map | A generated Francorchamps lap, animated |
| The reports | Hybrid sizing | Study A's results |
| | CO₂ sensitivity | Study B's results, report and downloads |
| | Cornering speed | Study C's results, report and downloads |

Workbook pages show the supplied figures exactly as reported: no unit conversion, recomputation, corrections or conclusions. The report pages read each study's saved results instead of rerunning sweeps. Every table has a CSV download.

A category is a slice of the 4 × 3 grid along one field: powertrain (4 categories of 3) or cycle (3 categories of 4). Driving style maps one-to-one onto cycle for now, so "all the sport" is the Francorchamps sport category.

The Data page has five datasets: `Runs` (12 × 74), `Totals` and `Parameters` in long form, `Traces` (676 steps), and `Workbook cells`, one workbook's labelled block exactly as the sheet holds it, with how the reader classified each row. Look there first when a figure elsewhere seems wrong.
