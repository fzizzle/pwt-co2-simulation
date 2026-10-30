"""Physical constants with a source, for the harmonised model. See `docs/sources.md`.

The supplied sheets use 0.0909 g/Wh (the assignment sheet's "1 kg ≈ 11 kWh") and 2392 g CO2
per litre at 720 kg/m³. These replace them.
"""

#: Motor gasoline, IPCC 2006 Guidelines defaults as tabulated in Commission Implementing
#: Regulation (EU) 2018/2066, Annex VI, Table 1.
PETROL_NCV_MJ_PER_KG = 44.3
PETROL_CO2_G_PER_MJ = 69.3

#: g of fuel per Wh of fuel energy: 3.6 kJ per Wh over the net calorific value.
FUEL_G_PER_WH = 3.6 / PETROL_NCV_MJ_PER_KG
#: g CO2 per g of fuel burnt: 3.070.
CO2_G_PER_G_PETROL = PETROL_CO2_G_PER_MJ * PETROL_NCV_MJ_PER_KG / 1000

#: kg/m³. The assignment sheet's 0.75 kg/l; EN 228 allows 720-775 at 15 °C and the WLTP E10
#: reference fuel is 743-756 (Regulation (EU) 2017/1151).
PETROL_DENSITY = 750.0

#: g CO2 per kWh of electricity, from the assignment sheet (EEA).
GRID_G_PER_KWH = {"EU": 250.0, "FR": 73.0}

#: Battery energy per unit of grid energy. An assumption inside the measured range: one-way
#: AC charging losses of 12-36 % (Apostolaki-Iosifidou, Codani & Kempton, Energy 127, 2017)
#: and 5-7 % on an 11-22 kW wallbox to 13-24 % on a 2.3 kW socket (ADAC, 2026).
CHARGER_EFFICIENCY = 0.90

#: One way through motor, inverter and battery. An assumption: 0.85² is about the 70 %
#: round-trip regenerative braking efficiency Boretti reports (SAE 2013-01-2872).
STORAGE_EFFICIENCY = 0.85
