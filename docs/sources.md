# Sources for the model's constants

## Study B extension ranges

These motivate exploratory screening scenarios, not vehicle-specific achievable bounds or cost estimates. No shared model constants change.

- **Mass:** [US DOE, Lightweight Materials for Cars and Trucks](https://www.energy.gov/cmei/vehicles/lightweight-materials-cars-and-trucks) discusses a 10% vehicle-weight reduction and larger reductions for selected components. Study B uses body-only −5%/−10% as analyst-selected scenarios; translating vehicle weight into body mass is an assumption. A separate experiment reaches ±10% total mass by adjusting body mass while retaining driver and powertrain masses.
- **Drag and tyres:** [EPA-420-R-16-021, November 2016 technical support document](https://nepis.epa.gov/Exe/ZyPURL.cgi?Dockey=P100Q3L4.txt), sections on vehicle road-load technologies and sections 2.3.4.4–2.3.4.5, uses 10% and 20% aerodynamic and rolling-resistance reduction levels. We apply these as coefficient reductions with frontal area fixed. These are historical technology scenarios, not a claim that the same improvements are available for this assignment car.
- **Engine multiplier:** the assignment and `pwt/model/fleet.py` give a 20–40% range, with baseline 0.35. The exploratory +5%/+10% increments (0.3675/0.385) are assumptions within that range; no equal cost or real-engine attainability is claimed.
- **Curve shape:** the alternatives in `data/course-files/10 SPA Franco HYBRID engine ECO Driving.xlsx`, `15 SPA Franco HYBRID engine SPORT Driving.xlsx` and `35 NEDC HYBRID engine.xlsx`, parameter menus in columns B–D. The reader verifies all menus agree and exports their exact coefficients. Shape-only retains the baseline multiplier; the complete-menu experiment also changes that multiplier.
- **Gears:** ±5% is an unsourced exploration of the existing gearing model. There is no established universal physically feasible or economically attractive ratio range here. It is excluded from any claim about sourced technology potential.
- **Near-ties:** the 2% span-gap rule is a reporting assumption, not measurement uncertainty. Finite-difference elasticities remain interval-dependent for nonlinear responses.

## Existing shared model constants

The harmonised model (`pwt/model/constants.py`) replaces the sheets' constants with these.

| Quantity | Sheets | Harmonised | Source |
|---|---|---|---|
| Petrol net calorific value | 39.6 MJ/kg (0.0909 g/Wh, "1 kg ≈ 11 kWh") | **44.3 MJ/kg** (0.0813 g/Wh) | IPCC 2006 Guidelines default, tabulated in [Commission Implementing Regulation (EU) 2018/2066, Annex VI, Table 1](https://www.legislation.gov.uk/eur/2018/2066/annex/VI/data.xht) |
| Petrol CO2 factor | 2392 g/l (3.32 g/g at 720 kg/m³) | **69.3 g CO2/MJ = 3.070 g CO2 per g fuel** | Same table |
| Petrol density | 720 kg/m³ | **750 kg/m³** | Assignment sheet (0.75 kg/l). EN 228 allows 720–775 kg/m³ at 15 °C ([supplier's copy of the EN 228 table](https://inverenergy.ie/wp-content/uploads/2019/11/Petrol.pdf); [CEN/TR 18238:2025](https://standards.iteh.ai/catalog/standards/cen/0676e1d2-e089-4198-840a-d5909fe0b938/cen-tr-18238-2025)); the WLTP E10 reference fuel is 743–756 kg/m³ ([Regulation (EU) 2017/1151](https://legislation.gov.uk/eur/2017/1151/attachment/40?view=plain)) |
| Grid electricity | 220 (Franco EV), 440 (NEDC EV), none (PHEV) | **250 g/kWh EU, 73 g/kWh France** | Assignment sheet, citing the EEA |
| Charger efficiency | 100 % (no loss) | **90 %**, an assumption | Measured one-way AC charging losses of 12–36 % ([Apostolaki-Iosifidou, Codani & Kempton, *Energy* 127 (2017) 730–742](https://ideas.repec.org/a/eee/energy/v127y2017icp730-742.html)); 5–7 % on an 11–22 kW wallbox up to 13–24 % on a 2.3 kW socket (ADAC, 2026, via [secondary report](https://zecar.com/reviews/ev-charging-losses-adac-study); original not checked) |
| Hybrid storage, one way through motor, inverter and battery | 100 % (no loss) | **85 %**, an assumption | 0.85² ≈ the 70 % round-trip regenerative braking efficiency in [Boretti, SAE 2013-01-2872](https://saemobilus.sae.org/content/2013-01-2872) (abstract read; measured on electric vehicles, not hybrids) |
| Traction drive specific power | none: motor mass fixed | **1.4 kW/kg**, anchored at 100 kg for 35 kW | US DOE Vehicle Technologies Program target table ([Rogers, APEEM overview](https://www.energy.gov/sites/prod/files/2014/03/f8/4_rogers_ed.pdf)). A target, not a measured P2 module |
| Battery peak power | none | **20C limit on sweep results**, an assumption | Just above the assignment hybrid's 25 kW on 1.5 kWh (16.7C); not sourced |

The IPCC values are defaults for motor gasoline as a fuel category, not for a specific EN 228 blend. With CO2 computed per kg of fuel, density only changes litres, not CO2.

On the petrol eco lap (`07`), with the sheet's own vehicle:

| | l/100 km | g CO2/km |
|---|---|---|
| Sheet constants | 10.273 | 245.7 |
| Heating value and CO2 factor | 9.184 (−10.6 %) | 203.0 (−17.4 %) |
| … and density 750 kg/m³ | 8.817 (−14.2 %) | 203.0 |

The −10.6 % is exactly 0.0813 / 0.0909: the lap never stops, so no idle fuel dilutes it. CO2 falls further than fuel because the sheets' 2392 g/l at 720 kg/m³ is 3.32 g CO2 per g of fuel, against 3.07.
