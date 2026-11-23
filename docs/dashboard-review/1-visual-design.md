# Dashboard visual review

The biggest difference is the first screen. The deck introduces the project with the shape of Spa. Overview introduces it with a paragraph, two expanders and a shallow blue elevation profile. At a 1280 × 800 browser viewport, the comparison heading and warning were visible, but neither the comparison chart nor the circuit outline was visible. Changing the background colour alone would leave that hierarchy intact.

I inspected the live Overview in a browser screenshot. The other page observations below come from the view and chart code. Paths and line numbers refer to the checkout during review.

## The deck reference

Use the slide inside mockups 24 and 31 as the reference. The HTML surrounding each slide has its own gallery styling. The production palette in `pwt/deck/art.py:18` is:

| Role | Dark | Light |
|---|---|---|
| Canvas | #000000 | #ffffff |
| Primary text | #f5f5f7 | #1d1d1f |
| Secondary text | #86868b | #86868b |
| Raised surface | #1c1c1e | #f5f5f7 |
| Rule | #2c2c2e | #e5e5ea |

- The four car colours are petrol **#d09539**, full hybrid **#4fb267**, plug-in hybrid **#b677d5**, and battery electric **#3984d0**. The mapping lives in `pwt/deck/data.py:17`.
- The title art is a smoothed north-up lap. Speed on the generated sport lap colours the road over 40–150 km/h. Its stops are #0a84ff, #30d158, #ffd60a and #ff453a at fractions 0, .45, .75 and 1. The bottom fades into the centred title. Relief is an impression interpolated from lap altitude. Contours are spaced at 2 m with every fifth heavier. The title masks them near the road. See `pwt/deck/art.py:74` and `pwt/deck/track.py:56`.
- A section opener zooms into a named corner on the right, fades left, and puts the heading and corner distance in the clear area. The small lap in the upper right carries a position dot and slide number. The dashboard already has navigation. Reserve this treatment for section entry points where a change of context helps.
- On the 1600 × 900 slide, the content left edge is 110 units in. The small label baseline is at 92, headline at 150 and footer at 862. Inter uses regular, medium, semibold and bold. Title size is 88 with −3 tracking. Openers use 96 with −3.5 tracking. Content uses a 24 label, 44 headline and 17 footer. These are slide design units. The renderer converts each unit of font size to 0.6 pt. See `pwt/deck/render.py:80`, `:385` and `:408`.
- The comparison slide gives its centre to the bars. Category labels and values do the work of axes. Values sit just above the bars. The multi-cycle legend sits above the plot. Bar corners have a 3–5 unit radius. Conditional model bars are hollow with an asterisk and a footnote. See `pwt/deck/render.py:177`. Its presentation rounding and model feasibility encoding belong to those slides.

## Findings by impact

**1. Overview needs a visual entry point and a faster route to the figures.** `dashboard/views/1_Overview.py:44` starts with a generic left-aligned title. The caption at line 50 places studies under the wrong menu group and omits Cornering speed. The series at line 64 is a workbook elevation profile. The comparison chart at line 128 follows both a warning and a full matrix. Use a shallow masthead with the title lap and real HTML heading. Put the selected measure, unit, workbook gap notice and grouped chart immediately below. Follow with the matrix and source table. Bundle the existing workbook elevation strip, map and cycle definitions below the comparison. Preserve the empty selection state. Link to the actual model and reports groups only where needed.

**2. Global styles currently assign different identities to the same cars.** `.streamlit/config.toml:4` gives the app a warm charcoal canvas and blue selection chips. `dashboard/theme.py:54` and `:64` give petrol blue and BEV orange. `style_axes` at line 95 uses the system font and grids on both axes. Carry the deck's named car mapping through filtering. Some charts also use positional colours for gear or force (`dashboard/charts.py:202` and `:220`). Give those quantities a separate palette and keep their legends. Preserve the existing labels, tables, hatching and dash patterns. The validation described in the current theme only covers its old colours. Recheck the new combinations in both themes. Strengthen muted small text on white for legibility. Resolve both live theme values before consulting the configured fallback at `dashboard/theme.py:75`.

**3. Use compact content headers on the other pages.** `dashboard/Overview.py:23` already groups the ten destinations well. Use those group names as quiet labels above page titles. `dashboard/layout.py:149` is the shared point for theme setup. Keep native sidebar, controls and keyboard focus. Give each page one primary reading area.

| View and location | Current arrangement | Proposed treatment |
|---|---|---|
| Category view, `dashboard/views/2_Category_View.py:88` | Reported table precedes the single-measure comparison and trace overlays. | Put the selected category and metric next to the comparison. Keep the reported table, source and gaps beside or directly below it. Use lighter section headings for trace and input detail. |
| Trace explorer, `dashboard/views/3_Trace_Explorer.py:76` | Speed and elevation, circuit, paired gear and force charts, then arbitrary columns. | Give speed and elevation the full content width. Use compact aligned panels for gear and forces. Keep step transitions, scales and units visible. |
| Compare, `dashboard/views/4_Compare.py:62` | Reported figures, input differences and traces compete as consecutive sections. | Keep the run pair and source names visible over a two-column comparison. Use line dashes for two runs of the same car. Keep the existing alignment warning with the overlay. |
| Data, `dashboard/views/5_Data.py:40` and `:144` | Dataset selection, source caption, grid and CSV download. | Use the compact workbook header. Group source, row count and download with the grid. Give the table all available width. |
| Model, `dashboard/views/6_Model.py:85` and `:127` | Scenario table followed by selectors, metrics and traces. | Lead with a “Model output” label and the scenario table. Align metric baselines. Preserve the distinction between scenarios, measured cycles and generated laps. |
| Track map, `dashboard/views/8_Track_Map.py:35` | Controls and four tiles introduce the playable track, followed by a distance plot. | Make the interactive circuit the main figure. Give the map a responsive container and test the full lap, scale and playback controls at narrow widths. Keep the selected variable's own colour scale. |
| Hybrid sizing, `dashboard/views/7_Sizing.py:53` and `:77` | Four summary metrics, long numbered owner headings, plots and heatmaps. | Use a compact Study A opener. Retain the owner's wording and assumptions. Align the paired heatmap panels and keep their individual axes, scale keys and limits visible. |
| CO₂ sensitivity, `dashboard/views/9_CO2_Sensitivity.py:63` and `:112` | Three filters, four tabs, metric row and split chart/key. | Keep the saved-results and owner-review labels under the title. Stack the key below the tornado chart on small screens. Preserve hatching, marker shapes and provisional notes. |
| Cornering speed, `dashboard/views/10_Cornering_Speed.py:54` and `:85` | Two headline metrics and two stacked response curves. | Align the plots' horizontal domains and margins for the selected variant. Retain their separate units, hollow markers and provisional caption. Keep the report and downloads in their existing tab. |

## Implementation sketches

Start with dark as the existing app default. Blue is a proposed interaction accent. Use native theme styling for focus and selection.

```toml
[theme]
base = "dark"
backgroundColor = "#000000"
secondaryBackgroundColor = "#1c1c1e"
textColor = "#f5f5f7"
primaryColor = "#3984d0"
font = "sans-serif"
```

Use Inter where available, with system sans as fallback. Apply CSS to dashboard-owned classes. The following are proposed screen dimensions.

```css
.pwt {
  --ink: #f5f5f7; --secondary: #86868b; --rule: #2c2c2e;
  --space-1: 8px; --space-2: 16px; --space-3: 24px; --section: 40px;
  font-family: Inter, system-ui, sans-serif;
}
.pwt-hero { text-align: center; padding: 12px 16px 24px; }
.pwt-hero h1 { font-size: clamp(30px, 4vw, 52px); line-height: 1.06;
  letter-spacing: -.035em; margin: 0; }
.pwt-source { font-size: 14px; line-height: 1.5; color: var(--secondary); }
```

Use `art.title_art("dark", path)` and its light counterpart during asset preparation. The existing build produces text-free title backgrounds. Package a downsampled copy for the dashboard. The local build output is not a tracked deployment asset. Keep matplotlib and PowerPoint dependencies in the deck environment. Do not render contours during a Streamlit rerun. The faded region is built into the PNG. Centre a live H1 over its lower part. Fit the whole lap at each breakpoint and let the title wrap below it on phones. Aim for a 220–280 px desktop masthead. Describe the art as the generated sport lap, with relief interpolated from lap altitude, in its accessible description and a short visible caption. Keep workbook figures sourced from the existing loaders. On workbook pages, retain the short “electricity not counted” note. The existing expanded explanation at `dashboard/layout.py:103` also gives calculated electricity and derived R101 values. Move that explanatory detail to a model context in a separately reviewed content change.

Use a Plotly template through `style_axes`. Keep its subplot title handling, automargins and `theme=None` call sites. Set individual car traces by key. Keep chart-specific quantity colours and feasibility markers explicit.

```python
from plotly import graph_objects as go
from pwt.deck.data import CAR_COLOURS

axis = dict(automargin=True, showgrid=False, zeroline=False)
template = go.layout.Template(layout=dict(
    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Inter, system-ui, sans-serif", size=14, color=pal.text_primary),
    xaxis=axis, yaxis=dict(axis, showgrid=True, gridcolor=pal.grid),
    legend=dict(orientation="h"), margin=dict(l=12, r=12, t=28, b=12),
))
fig.update_layout(template=template)
# Inside the existing per-powertrain bar builder:
# marker_color=CAR_COLOURS[powertrain]
```

Only hide numeric ticks and gridlines on labelled summary bars where every value, unit and sign remains legible. Keep scales on time series, overlays, scatter plots and heatmaps. Test long cycle names, negative totals, missing cells and the reported PHEV zero. Keep workbook gap text distinct from model shortfall symbols. Retain existing saved study data, draft labels and owner interpretation. All Streamlit helpers belong in dashboard/.

## Recommendation

1. **First, rebuild the Overview header and reorder the first comparison (half a day).** Export the two title assets, correct the menu caption, and place the labelled workbook chart under the masthead. Check default, filtered and empty views at desktop and phone widths.
2. **Second, align shared theme and chart styles (half to one day).** Apply the deck surfaces, type scale and named car colours. Check readable contrast, focus, labels and subplot units. Compare displayed workbook figures and CSVs before and after.
3. **Third, carry the compact headers and chart hierarchy through the remaining pages (one day).** Start with Model and Track map. Finish the three reports with their owners' labels intact. Check narrow layouts, the entire circuit, chart legends, conditional results and downloads.
