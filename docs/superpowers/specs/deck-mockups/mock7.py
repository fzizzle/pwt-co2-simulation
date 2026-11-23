import sys, json, math
exec(open(sys.argv[4]).read().split("def card(")[0])
exec(open(sys.argv[5]).read().split("def r1(")[0].split("exec(")[0] if False else "")
def rproj(lap, cx, cy, width, rot=90):
    lat=lap["lat"]; lon=lap["lon"]; sc=math.cos(math.radians(sum(lat)/len(lat)))
    pts=[(o*sc,-a) for a,o in zip(lat,lon)]
    if rot==90: pts=[(-y,x) for x,y in pts]
    xs=[p[0] for p in pts]; ys=[p[1] for p in pts]
    k=width/(max(xs)-min(xs)); mx=(max(xs)+min(xs))/2; my=(max(ys)+min(ys))/2
    return lambda x,y:(cx+(x-mx)*k, cy+(y-my)*k), pts
LAP=T["franco_sport_generated"]
def progress(t, cx, cy, width, upto, sw, label=None, fs=22):
    f,pts=rproj(LAP,cx,cy,width)
    P=[f(x,y) for x,y in pts]; S=LAP["s"]
    rest=" ".join(f"{x:.1f},{y:.1f}" for x,y in P)
    out=f'<polyline points="{rest}" fill="none" stroke="{t["line"]}" stroke-width="{sw}" stroke-linecap="round" stroke-linejoin="round"/>'
    last=P[0]
    for i in range(len(P)-1):
        if S[i]>upto: break
        (x1,y1),(x2,y2)=P[i],P[i+1]; last=P[i+1]
        out+=f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{col((LAP["v"][i]-VMIN)/(VMAX-VMIN))}" stroke-width="{sw}" stroke-linecap="round"/>'
    x,y=last
    out+=f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{sw*0.9:.1f}" fill="{t["fg"]}" stroke="{t["bg"]}" stroke-width="{sw*0.35:.1f}"/>'
    if label: out+=f'<text x="{x:.1f}" y="{y-sw*1.8:.1f}" text-anchor="middle" fill="{t["fg"]}" font-size="{fs}" font-weight="600">{label}</text>'
    return out
SECTIONS=[(0,"Start","PWT · Powertrains","Four cars. Four cycles."),
          (220,"La Source","01","The simulation"),
          (1010,"Eau Rouge","02","Four cars compared"),
          (2200,"Les Combes","03 · Study A","Hybrid sizing"),
          (3600,"Pouhon","04 · Study B","Sensitivity"),
          (4740,"Stavelot","05 · Study C","Cornering speed"),
          (6540,"Bus Stop","06","Limits and next step"),
          (7000,"Finish","","Questions?")]
def divider(dark, i):
    t=th(dark); s,corner,num,title=SECTIONS[i]
    b=progress(t,1030,450,980,s,18,corner,24)
    b+=hfade(t,f"d{i}{int(dark)}","0","0.6",mid=0.5)
    b+=(f'<text x="110" y="380" fill="{t["mute"]}" font-size="28" font-weight="600">{num}</text>'
        f'<text x="110" y="480" fill="{t["fg"]}" font-size="96" font-weight="700" letter-spacing="-3.5">{title}</text>'
        f'<text x="110" y="800" fill="{t["mute"]}" font-size="20">{s/1000:.1f} km of 7.0 · {corner}</text>')
    return svg(t,b,False)
def hfade(t,id,x1,x2,y1="0",y2="0",mid=0.5):
    c=t["bg"]
    return (f'<defs><linearGradient id="{id}" x1="{x1}" x2="{x2}" y1="{y1}" y2="{y2}"><stop offset="0" stop-color="{c}" stop-opacity="1"/><stop offset="{mid}" stop-color="{c}" stop-opacity="0.7"/><stop offset="1" stop-color="{c}" stop-opacity="0"/></linearGradient></defs>'
            f'<rect x="0" y="0" width="1600" height="900" fill="url(#{id})"/>')
GRID={"NEDC":[134.1,123.7,67.9,38.0],"WLTC Class 3":[145.1,128.8,73.6,45.8],"Spa eco":[217.5,218.8,113.0,56.5],"Spa sport":[385.2,395.2,293.0,132.2]}
CARS=[("Petrol","#ff9f0a"),("Full hybrid","#30d158"),("Plug-in hybrid","#bf5af2"),("Battery electric","#0a84ff")]
def content(dark):
    t=th(dark)
    b=progress(t,1440,95,220,1010,5)
    b+=f'<text x="1440" y="170" text-anchor="middle" fill="{t["mute"]}" font-size="15">Eau Rouge · 1.0 km</text>'
    b+=(f'<text x="110" y="92" fill="{t["mute"]}" font-size="26" font-weight="500">Four cars on four cycles · g CO2/km</text>'
        f'<text x="110" y="150" fill="{t["fg"]}" font-size="46" font-weight="700" letter-spacing="-1">Driving style moves CO2 as much as the powertrain</text>')
    base,top=760,290; mx=395.2; bw,inner,gap=58,10,110
    gw=4*bw+3*inner; x0=800-(4*gw+3*gap)/2
    lx=800-4*200/2
    for i,(n,c) in enumerate(CARS):
        b+=f'<circle cx="{lx+i*200+10}" cy="225" r="9" fill="{c}"/><text x="{lx+i*200+28}" y="234" fill="{t["mute"]}" font-size="22">{n}</text>'
    for g,(cyc,vals) in enumerate(GRID.items()):
        gx=x0+g*(gw+gap)
        for i,((n,c),v) in enumerate(zip(CARS,vals)):
            h=(base-top)*v/mx; x=gx+i*(bw+inner)
            b+=f'<path d="M{x},{base} V{base-h+8} q0,-8 8,-8 H{x+bw-8} q8,0 8,8 V{base} Z" fill="{c}"/>'
            b+=f'<text x="{x+bw/2}" y="{base-h-12}" text-anchor="middle" fill="{t["fg"]}" font-size="19" font-weight="600">{v:.0f}</text>'
        b+=f'<text x="{gx+gw/2}" y="{base+48}" text-anchor="middle" fill="{t["fg"]}" font-size="26" font-weight="600">{cyc}</text>'
    return svg(t,b,page="6")
def shadow(s): return f'<div style="box-shadow:0 2px 12px rgba(0,0,0,.18);border-radius:10px;overflow:hidden">{s}</div>'
strip=lambda dark:'<div style="display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin-top:10px">'+"".join(shadow(divider(dark,i)) for i in range(len(SECTIONS)))+'</div>'
o=['<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">',
 '<h2>One lap of Spa, one presentation</h2>',
 '<p class="subtitle">Each section opens at the next corner. The part of the lap already driven lights up in speed colours (the real generated sport lap); the rest stays grey. Content slides carry a small map in the corner showing where we are. Corner-to-section matching and all wording are placeholders.</p>',
 '<h3 style="margin-top:18px">The whole deck\'s section openers, in order (dark)</h3>', strip(True),
 '<h3 style="margin-top:22px">The same, light</h3>', strip(False),
 '<h3 style="margin-top:22px">A content slide with the progress map in the corner</h3>',
 '<div class="split" style="margin-top:10px">', shadow(content(False)), shadow(content(True)), '</div>',
 '<h3 style="margin-top:22px">One section opener, full size</h3>', shadow(divider(True,3)),
]
open(sys.argv[3],"w").write("\n".join(o))
