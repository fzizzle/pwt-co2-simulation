# Sources for the model's constants

The harmonised model (`pwt/model/constants.py`) replaces the sheets' constants with these.

| Quantity | Sheets | Harmonised | Source |
|---|---|---|---|
| Petrol net calorific value | 39.6 MJ/kg (0.0909 g/Wh, "1 kg ≈ 11 kWh") | **44.3 MJ/kg** (0.0813 g/Wh) | IPCC 2006 Guidelines default, tabulated in [Commission Implementing Regulation (EU) 2018/2066, Annex VI, Table 1](https://www.legislation.gov.uk/eur/2018/2066/annex/VI/data.xht) |
| Petrol CO2 factor | 2392 g/l (3.32 g/g at 720 kg/m³) | **69.3 g CO2/MJ = 3.070 g CO2 per g fuel** | Same table |
| Petrol density | 720 kg/m³ | **750 kg/m³** | Assignment sheet (0.75 kg/l). EN 228 allows 720–775 kg/m³ at 15 °C ([supplier's copy of the EN 228 table](https://inverenergy.ie/wp-content/uploads/2019/11/Petrol.pdf); [CEN/TR 18238:2025](https://standards.iteh.ai/catalog/standards/cen/0676e1d2-e089-4198-840a-d5909fe0b938/cen-tr-18238-2025)); the WLTP E10 reference fuel is 743–756 kg/m³ ([Regulation (EU) 2017/1151](https://legislation.gov.uk/eur/2017/1151/attachment/40?view=plain)) |
| Grid electricity | 220 (Franco EV), 440 (NEDC EV), none (PHEV) | **250 g/kWh EU, 73 g/kWh France** | Assignment sheet, citing the EEA |
| Charger efficiency | 100 % (no loss) | **90 %**, an assumption | Measured one-way AC charging losses of 12–36 % ([Apostolaki-Iosifidou, Codani & Kempton, *Energy* 127 (2017) 730–742](https://ideas.repec.org/a/eee/energy/v127y2017icp730-742.html)); 5–7 % on an 11–22 kW wallbox up to 13–24 % on a 2.3 kW socket (ADAC, 2026, via [secondary report](https://zecar.com/reviews/ev-charging-losses-adac-study); original not checked) |

The IPCC values are defaults for motor gasoline as a fuel category, not for a specific EN 228 blend. With CO2 computed per kg of fuel, density only changes litres, not CO2.

On the petrol eco lap (`07`), with the sheet's own vehicle:

| | l/100 km | g CO2/km |
|---|---|---|
| Sheet constants | 10.273 | 245.7 |
| Heating value and CO2 factor | 9.184 (−10.6 %) | 203.0 (−17.4 %) |
| … and density 750 kg/m³ | 8.817 (−14.2 %) | 203.0 |

The −10.6 % is exactly 0.0813 / 0.0909: the lap never stops, so no idle fuel dilutes it. CO2 falls further than fuel because the sheets' 2392 g/l at 720 kg/m³ is 3.32 g CO2 per g of fuel, against 3.07.
