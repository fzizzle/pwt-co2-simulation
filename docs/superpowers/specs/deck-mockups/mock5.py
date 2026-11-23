import sys, json, math
sys.argv_ = sys.argv
exec(open(sys.argv[4]).read().split("def card(")[0])  # reuse helpers from mock4
GRID={"NEDC":[134.1,123.7,67.9,38.0],"WLTC Class 3":[145.1,128.8,73.6,45.8],"Spa eco":[217.5,218.8,113.0,56.5],"Spa sport":[385.2,395.2,293.0,132.2]}
CARS=[("Petrol","#ff9f0a"),("Full hybrid","#30d158"),("Plug-in hybrid","#bf5af2"),("Battery electric","#0a84ff")]
def bg(t, cx, cy, size, op, sw, mono=None):
    lap=T["franco_sport_generated"]; P=proj(lap,cx,cy,size)
    pts=[P(a,o) for a,o in zip(lap["lat"],lap["lon"])]
    if mono:
        return f'<g opacity="{op}"><polyline points="'+" ".join(f"{x:.1f},{y:.1f}" for x,y in pts)+f'" fill="none" stroke="{mono}" stroke-width="{sw}" stroke-linecap="round" stroke-linejoin="round"/></g>'
    out=f'<g opacity="{op}">'
    for i in range(len(pts)-1):
        (x1,y1),(x2,y2)=pts[i],pts[i+1]
        out+=f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{col((lap["v"][i]-VMIN)/(VMAX-VMIN))}" stroke-width="{sw}" stroke-linecap="round"/>'
    return out+'</g>'
def fade(t, id, x1, x2):
    c=t["bg"]
    return (f'<defs><linearGradient id="{id}" x1="{x1}" x2="{x2}" y1="0" y2="0"><stop offset="0" stop-color="{c}" stop-opacity="1"/><stop offset="0.55" stop-color="{c}" stop-opacity="0.85"/><stop offset="1" stop-color="{c}" stop-opacity="0"/></linearGradient></defs>'
            f'<rect x="0" y="0" width="1600" height="900" fill="url(#{id})"/>')
def b1():
    t=th(True)
    b=bg(t,1150,470,1150,0.95,26)+fade(t,"f1","0","1")
    b+=(f'<text x="110" y="560" fill="{t["fg"]}" font-size="110" font-weight="700" letter-spacing="-4">Spa, in CO2.</text>'
        f'<text x="110" y="625" fill="{t["mute"]}" font-size="28">Four powertrains on four driving cycles</text>'
        f'<text x="110" y="800" fill="{t["mute"]}" font-size="20">{GROUP}</text>')
    return svg(t,b,False)
def b2():
    t=th(False)
    b=bg(t,800,450,1000,0.10,40,mono="#1d1d1f")
    b+=bg(t,800,450,1000,1,4)
    b+=(f'<text x="800" y="440" text-anchor="middle" fill="{t["fg"]}" font-size="92" font-weight="700" letter-spacing="-3">Four cars. Four cycles.</text>'
        f'<text x="800" y="515" text-anchor="middle" fill="{t["mute"]}" font-size="30">Simulating the CO2 of four powertrains</text>'
        f'<text x="800" y="830" text-anchor="middle" fill="{t["mute"]}" font-size="20">{GROUP}</text>')
    return svg(t,b,False)
def b3():
    t=th(True)
    b=bg(t,800,520,1100,0.18,22)
    b+=head(t,"Four cars on four cycles · g CO2/km","Driving style moves CO2 as much as the powertrain")
    base,top=760,280; mx=395.2; bw,inner,gap=58,10,110
    gw=4*bw+3*inner; x0=800-(4*gw+3*gap)/2
    lx=800-4*200/2
    for i,(n,c) in enumerate(CARS):
        b+=f'<circle cx="{lx+i*200+10}" cy="205" r="9" fill="{c}"/><text x="{lx+i*200+28}" y="214" fill="{t["mute"]}" font-size="22">{n}</text>'
    for g,(cyc,vals) in enumerate(GRID.items()):
        gx=x0+g*(gw+gap)
        for i,((n,c),v) in enumerate(zip(CARS,vals)):
            h=(base-top)*v/mx; x=gx+i*(bw+inner)
            b+=f'<path d="M{x},{base} V{base-h+8} q0,-8 8,-8 H{x+bw-8} q8,0 8,8 V{base} Z" fill="{c}"/>'
            b+=f'<text x="{x+bw/2}" y="{base-h-12}" text-anchor="middle" fill="{t["fg"]}" font-size="19" font-weight="600">{v:.0f}</text>'
        b+=f'<text x="{gx+gw/2}" y="{base+48}" text-anchor="middle" fill="{t["fg"]}" font-size="26" font-weight="600">{cyc}</text>'
    return svg(t,b,page="6")
def b4():
    t=th(True)
    # zoom into the top of the circuit (La Source / Eau Rouge), cropped off the edges
    b=bg(t,700,1350,3600,1,60)
    b+=f'<rect x="0" y="0" width="1600" height="900" fill="#000" opacity="0.45"/>'
    b+=(f'<text x="110" y="330" fill="#ff9f0a" font-size="30" font-weight="600">04 · Study C</text>'
        f'<text x="110" y="440" fill="{t["fg"]}" font-size="110" font-weight="700" letter-spacing="-4">Cornering speed</text>'
        f'<text x="110" y="510" fill="{t["fg"]}" font-size="30" opacity="0.75">Do grippier tyres or a spoiler save CO2?</text>'
        f'<text x="110" y="790" fill="{t["fg"]}" font-size="22" opacity="0.6">Owner: (name) · 2.5 min</text>')
    return svg(t,b,False)
def b5():
    t=th(False)
    b=bg(t,1180,450,900,0.9,16)+fade(t,"f5","0.05","0.75")
    b+=(f'<text x="110" y="250" fill="{t["mute"]}" font-size="26" font-weight="500">Petrol car, one sport lap</text>'
        f'<text x="100" y="480" fill="{t["fg"]}" font-size="220" font-weight="700" letter-spacing="-10">385</text>'
        f'<text x="110" y="545" fill="{t["fg"]}" font-size="36" font-weight="600">g CO2/km</text>'
        f'<text x="110" y="600" fill="{t["mute"]}" font-size="26">against 217.5 on the eco lap of the same track</text>')
    b+=legend(t,110,700,230)
    return svg(t,b,page="7")
def b6():
    t=th(True)
    b=bg(t,800,450,820,0.35,10)
    b+=(f'<text x="800" y="440" text-anchor="middle" fill="{t["fg"]}" font-size="100" font-weight="700" letter-spacing="-3">Questions?</text>'
        f'<text x="800" y="510" text-anchor="middle" fill="{t["mute"]}" font-size="28">Then, if time allows: the model live</text>')
    return svg(t,b,False)
def card(k,h,p,s):
    return f'<div class="option" data-choice="{k}" onclick="toggleSelect(this)"><div class="letter">{k.upper()}</div><div class="content" style="width:100%"><h3>{h}</h3><p>{p}</p><div style="margin-top:10px;box-shadow:0 2px 16px rgba(0,0,0,.18);border-radius:12px;overflow:hidden">{s}</div></div></div>'
o=['<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">',
 '<h2>The track as a background</h2><p class="subtitle">Real Spa outline, coloured by the generated sport lap\'s speed. Numbers are model output; wording is placeholder. Click any you like.</p><div class="options" data-multiselect>',
 card("b1","Title: oversized track bleeding off the right","The circuit is cropped by the slide edge and fades into black behind the title.",b1()),
 card("b2","Title: big pale track behind centred type","A wide grey ribbon of the circuit with a thin coloured line on top; title over the middle.",b2()),
 card("b3","Chart over a faint track","The 4 × 4 comparison, the circuit glowing faintly behind it.",b3()),
 card("b4","Section title: zoomed into one part of the circuit","Huge, cropped close-up of the track as texture behind the study title. Shown for Study C.",b4()),
 card("b5","One big number beside the track","A single result in very large type; the track on the right fades in behind it.",b5()),
 card("b6","Closing slide","Questions, then the live demo, over a faint lap.",b6()),
 '</div>']
open(sys.argv[3],"w").write("\n".join(o))
