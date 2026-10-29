# The supplied model, as equations

Every column of `07 SPA Franco PETROL car ECO Driving.xlsx`, written as the equation it computes, then what the other workbooks do differently. Subscript $i$ is the current row (step), $i-1$ the one above. Cell references are to file `07`.

## Parameters

| Symbol | Cell | Value in `07` |
|---|---|---|
| $D$ wheel diameter | C4 | 0.6345 m |
| $i_1 \dots i_5$ overall gear ratios | C6:C10 | 12.526, 7.588, 5.052, 3.428, 2.525 |
| $m_v$ vehicle, $m_d$ driver, $m = m_v + m_d$ | C13:C15 | 1300 + 80 = 1380 kg |
| $g$ | C16 | 9.81 m/s² |
| $S C_x$ | C19:C21 | 2.69 × 0.31 = 0.834 m² |
| $\rho$ air | C22 | 1.2 kg/m³ |
| $f_r$ rolling coefficient | C24 | 0.015 |
| $\eta_\text{max}$, $A_1, A_2, A_3$ efficiency curve | C26:C29 | 0.35; −0.3867, 0.6285, 0.7516 ("modern") |
| $P_\text{max}$ | C31 | 85 000 W |
| $\eta_t$ drivetrain | C34 | 95 % |
| $\rho_f$ fuel | C37 | 720 kg/m³ |
| $m_{\text{eff},k}$ effective mass in gear $k$ | C39:C43 | see below |

## Per step

The Francorchamps lap is 32 points along the track, each with a distance $s$, an altitude $z$ and an imposed speed $V$ (km/h). Time is derived from them.

| Col | Quantity | Equation |
|---|---|---|
| F | step length | $\Delta s_i = s_i - s_{i-1}$ |
| K | speed | $v_i = V_i / 3.6$ |
| E | step time | $\Delta t_i = \Delta s_i \,/\, \tfrac12(v_i + v_{i-1})$ — constant acceleration over the step |
| G | time | $t_i = t_{i-1} + \Delta t_i$ |
| L | gear | $k_i = 0$ if $V_i = 0$; else 1, 2, 3, 4, 5 for $V_i \le 35, 57, 82, 115, >115$ km/h |
| M | acceleration | $a_i = (v_i - v_{i-1}) / \Delta t_i$ |
| N | wheel speed | $\omega_{w,i} = v_i / (D/2)$ |
| O | engine speed | $\omega_{e,i} = i_{k_i}\,\omega_{w,i}$; at $k_i = 0$, idle: $800 \cdot 2\pi/60$ |
| P | engine rpm | $N_i = 60\,\omega_{e,i} / 2\pi$ |
| Q | slope | $\theta_i = \arctan\big((z_i - z_{i-1}) / \Delta s_i\big)$ |
| R | resistive force | $F_{\text{res},i} = m g f_r + m g \sin\theta_i + \tfrac12 \rho\, S C_x\, v_i^2$ |
| S | inertia force | $F_{\text{acc},i} = m_{\text{eff},k_i}\, a_i$ (0 at $k_i = 0$) |
| T | total force | $F_i = F_{\text{res},i} + F_{\text{acc},i}$ |
| U | wheel power | $P_{w,i} = \max(F_i, 0) \cdot \tfrac12(v_i + v_{i-1})$ — labelled "Engine power" |
| V | engine power | $P_{e,i} = P_{w,i} / \eta_t$ |
| W | engine torque | $C_{e,i} = P_{e,i} / \omega_{e,i}$ |
| X | engine energy | $E_i = P_{e,i}\,\Delta t_i / 3600$ Wh (0 when $F_i < 0$) |
| Y | engine efficiency | $\eta_{e,i} = \eta_\text{max}\,(A_1 x_i^2 + A_2 x_i + A_3)$, $x_i = P_{e,i} / P_\text{max}$ |
| Z | fuel mass | $m_{f,i} = 0.0909\, E_i / \eta_{e,i}$ g |
| AA | fuel volume | $V_{f,i} = m_{f,i} / \rho_f$ l; at $k_i = 0$, idle: $0.8\,\Delta t_i / 3600$ l |
| AB | CO2 | $\text{CO2}_i = 2392\, V_{f,i}$ g |

### Totals

$$\text{l/100 km} = \frac{\sum V_{f,i}}{\sum \Delta s_i / 10^5} \qquad \text{g CO2/km} = \frac{\sum \text{CO2}_i}{\sum \Delta s_i / 10^3}$$

### The constants

- **0.0909 g/Wh** is $1/11$: the assignment sheet's "1 kg gasoline ≈ 40 MJ or 11 kWh". It implies a heating value of 39.6 MJ/kg.
- **2392 g CO2 per litre** is the sheet's EEA figure. With $\rho_f = 720$ it means 3.32 g CO2 per g of fuel; with the sheet's own 0.75 kg/l it would be 3.19.
- **Idle, 0.8 l/h**, applies only at standstill. Moving with $F_i \le 0$ burns nothing: the model assumes overrun fuel cut-off, and braking energy is lost.

## The rotating-mass factor, by hand

$$m_{\text{eff},k} = m_d + m_v\,(1.04 + 0.0025\, i_k^2)$$

Gear 1: $i_1^2 = 12.526^2 = 156.90$, so $0.0025 \times 156.90 = 0.3923$ and the factor is $1.4323$. Then $m_{\text{eff},1} = 80 + 1300 \times 1.4323 = 1941.9$ kg, which matches the cached C39 (1941.927 kg). In 5th it falls to 1452.7 kg: the engine and gearbox spin 5× slower relative to the wheels.

## A step by hand: row 10 of `07`

From 1130 m to 1180 m, 22.2 → 25.0 m/s, climbing from 415 to 417.24 m:

- $\Delta t = 50 / 23.61 = 2.118$ s, $a = 2.778 / 2.118 = 1.312$ m/s², gear 4 ($V = 90 \le 115$).
- $\theta = \arctan(2.243/50) = 0.0448$ rad.
- $F_\text{res} = 203.1 + 606.7 + 312.7 = 1122.5$ N; $F_\text{acc} = 1470.2 \times 1.312 = 1928.5$ N; $F = 3051.0$ N.
- $P_w = 3051.0 \times 23.61 = 72.0$ kW, $P_e = 75.8$ kW, $\omega_e = 270.1$ rad/s (2580 rpm), $C_e = 281$ Nm.
- $E = 75\,828 \times 2.118 / 3600 = 44.6$ Wh, $x = 0.892$, $\eta_e = 0.352$, fuel $= 11.53$ g $= 16.0$ ml, CO2 $= 38.3$ g.

**This step asks the 74 kW, 146 Nm engine for 75.8 kW and 281 Nm.** The sheet does not check capability (the assignment says to). On the sport lap the petrol car is asked for up to 127 kW and 480 Nm, beyond its power on 7 of 32 steps and its torque on 14. So the supplied sport speed profile is not limited by the engine, although the sport case requires it to be.

## What the other workbooks do differently

| | Petrol (Franco `07`/`13`) | Petrol NEDC `33` | Hybrid / PHEV | Electric |
|---|---|---|---|---|
| Trace | 32 points by distance | 1 row per time point; $\Delta s = v_i\,\Delta t$ | as their cycle | as their cycle |
| Shift speeds (km/h) | 35/57/82/115 | 18/38/50/70 | 35/57/82/115 | single ratio 6.218 |
| $m_{\text{eff}}$ | $m_d + m_v k$ | $m\,k$ (driver included in $k$) | $m_\text{EM} + m_\text{batt} + m_d + m_v k$ | $m_d + m_\text{batt} + m_v k$ |
| Negative power | discarded | discarded | recovered: $P_e = \eta_t P_w$ | recovered; Francorchamps caps at −120 kW |
| Engine at standstill | idles, 0.8 l/h | idles | Franco: idles; NEDC: off | — |

### Hybrid columns (X–AA)

| Col | Quantity | Equation |
|---|---|---|
| X | demand energy | $B_i = P_{e,i}\,\Delta t_i / 3600$ Wh, signed |
| Y | motor share | traction: $\phi_i = 0$ if $\text{SOC}_{i-1} \le \text{SOC}_\text{min}$, else $1$ if $P_\text{EM} \ge P_{e,i}$, else $0.9\,P_\text{EM}/P_{e,i}$; braking: $\min(1, P_\text{EM}/\lvert P_{e,i}\rvert)$ while $\text{SOC}_{i-1} \le 1$ |
| Z | engine energy | traction: $(1 - \phi_i) B_i$; braking: $\phi_i B_i$ (negative — the netting the brief warns about) |
| AA | state of charge | $\text{SOC}_i = \text{SOC}_{i-1} - \phi_i B_i / E_\text{batt}$ |

$\text{SOC}_\text{min}$ is 0.3 in the full hybrid, 0.23 in the plug-in. No motor or battery efficiency is applied: the battery delivers and absorbs the drivetrain-side energy exactly. The full hybrid adds a **fictive end-of-cycle line** that buys back $E_\text{batt}(\text{SOC}_0 - \text{SOC}_N)$ with fuel at $\eta_\text{max}$, the engine's best efficiency.

Battery mass is $2E_\text{batt}/e$, with $e$ = 80 Wh/kg (`10`, `15`), 150 (`09`, `14`) or 160 (`34`, `35`).

### Electric columns

Motor efficiency depends on speed only: $\eta_m = aN^2 + bN + c$ % ($a = -6\times10^{-7}$, $b = 0.0059$, $c = 80$; peak 94.5 % at 4917 rpm). Battery power is $P_e/\eta_m$ in traction, $P_e\,\eta_m$ in regeneration. CO2 is $220$ g/kWh (Francorchamps) or $440$ g/kWh (NEDC) times the battery energy.
