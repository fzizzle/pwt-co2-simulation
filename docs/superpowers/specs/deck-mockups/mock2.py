import sys
CARS=[("Petrol","#ff9f0a"),("Full hybrid","#30d158"),("Plug-in hybrid","#bf5af2"),("Battery electric","#0a84ff")]
WLTC=[145.1,128.8,73.6,45.8]
GRID={"NEDC":[134.1,123.7,67.9,38.0],"WLTC Class 3":[145.1,128.8,73.6,45.8],
      "Spa eco":[217.5,218.8,113.0,56.5],"Spa sport":[385.2,395.2,293.0,132.2]}
def theme(dark):
    return dict(bg="#000" if dark else "#fff", fg="#f5f5f7" if dark else "#1d1d1f",
                mute="#86868b", grid="#2c2c2e" if dark else "#e8e8ed")
def single(dark):
    t=theme(dark); W,H=1600,900
    s=[f'<svg viewBox="0 0 {W} {H}" style="width:100%;display:block;background:{t["bg"]};border-radius:12px;font-family:Inter,-apple-system,sans-serif">']
    s.append(f'<text x="800" y="92" text-anchor="middle" fill="{t["mute"]}" font-size="26" font-weight="500">WLTC Class 3 · g CO2/km</text>')
    s.append(f'<text x="800" y="150" text-anchor="middle" fill="{t["fg"]}" font-size="46" font-weight="700" letter-spacing="-1">The electric car emits a third of the petrol car</text>')
    base,top=760,230; bw,gap=190,90; x0=800-(4*bw+3*gap)/2
    s.append(f'<line x1="{x0-40}" x2="{W-x0+40}" y1="{base}" y2="{base}" stroke="{t["grid"]}" stroke-width="2"/>')
    for i,((n,c),v) in enumerate(zip(CARS,WLTC)):
        h=(base-top)*v/max(WLTC); x=x0+i*(bw+gap)
        s.append(f'<path d="M{x},{base} V{base-h+16} q0,-16 16,-16 H{x+bw-16} q16,0 16,16 V{base} Z" fill="{c}"/>')
        s.append(f'<text x="{x+bw/2}" y="{base-h-22}" text-anchor="middle" fill="{t["fg"]}" font-size="44" font-weight="700" letter-spacing="-1">{v:.1f}</text>')
        s.append(f'<text x="{x+bw/2}" y="{base+50}" text-anchor="middle" fill="{t["mute"]}" font-size="26" font-weight="500">{n}</text>')
    s.append(f'<text x="80" y="860" fill="{t["mute"]}" font-size="18">EU grid 250 g/kWh · model output · first draft</text><text x="1520" y="860" text-anchor="end" fill="{t["mute"]}" font-size="18">5</text></svg>')
    return "".join(s)
def grouped(dark):
    t=theme(dark); W,H=1600,900
    s=[f'<svg viewBox="0 0 {W} {H}" style="width:100%;display:block;background:{t["bg"]};border-radius:12px;font-family:Inter,-apple-system,sans-serif">']
    s.append(f'<text x="800" y="92" text-anchor="middle" fill="{t["mute"]}" font-size="26" font-weight="500">Four cars on four cycles · g CO2/km</text>')
    s.append(f'<text x="800" y="150" text-anchor="middle" fill="{t["fg"]}" font-size="46" font-weight="700" letter-spacing="-1">Driving style moves CO2 more than the powertrain</text>')
    # legend
    lx=800-4*200/2
    for i,(n,c) in enumerate(CARS):
        s.append(f'<circle cx="{lx+i*200+10}" cy="205" r="9" fill="{c}"/><text x="{lx+i*200+28}" y="214" fill="{t["mute"]}" font-size="22">{n}</text>')
    base,top=770,260; mx=395.2; bw,inner,gap=58,10,110
    gw=4*bw+3*inner; x0=800-(4*gw+3*gap)/2
    s.append(f'<line x1="{x0-30}" x2="{W-x0+30}" y1="{base}" y2="{base}" stroke="{t["grid"]}" stroke-width="2"/>')
    for g,(cyc,vals) in enumerate(GRID.items()):
        gx=x0+g*(gw+gap)
        for i,((n,c),v) in enumerate(zip(CARS,vals)):
            h=(base-top)*v/mx; x=gx+i*(bw+inner)
            s.append(f'<path d="M{x},{base} V{base-h+8} q0,-8 8,-8 H{x+bw-8} q8,0 8,8 V{base} Z" fill="{c}"/>')
            s.append(f'<text x="{x+bw/2}" y="{base-h-12}" text-anchor="middle" fill="{t["fg"]}" font-size="19" font-weight="600">{v:.0f}</text>')
        s.append(f'<text x="{gx+gw/2}" y="{base+48}" text-anchor="middle" fill="{t["fg"]}" font-size="26" font-weight="600">{cyc}</text>')
    s.append(f'<text x="80" y="860" fill="{t["mute"]}" font-size="18">EU grid 250 g/kWh · model output · first draft</text><text x="1520" y="860" text-anchor="end" fill="{t["mute"]}" font-size="18">5</text></svg>')
    return "".join(s)
opts=[("a","White, one cycle, one message",
       "The chart fills the middle; one headline above, nothing else. Big value labels instead of an axis.", single(False)),
      ("b","Black, one cycle, one message","Same layout on a black stage. Colours glow more; reads more like a launch event.", single(True)),
      ("c","White, the whole 4 × 4 in one chart","All sixteen results as grouped bars, centred. Busier, but one slide carries the whole comparison.", grouped(False)),
      ("d","Black, the whole 4 × 4 in one chart","The grouped chart on black.", grouped(True))]
out=['<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">',
 '<h2>Chart in the middle, as the focus</h2>',
 '<p class="subtitle">Real model numbers (storage-loss baseline, EU grid). Headlines are placeholders to show the style, not the group\'s wording. Click the closest; say what to change.</p>',
 '<div class="options">']
for k,h,p,svg in opts:
    out.append(f'<div class="option" data-choice="{k}" onclick="toggleSelect(this)"><div class="letter">{k.upper()}</div><div class="content" style="width:100%"><h3>{h}</h3><p>{p}</p><div style="margin-top:10px;box-shadow:0 2px 16px rgba(0,0,0,.18);border-radius:12px">{svg}</div></div></div>')
out.append('</div>')
open(sys.argv[1],"w").write("\n".join(out))
