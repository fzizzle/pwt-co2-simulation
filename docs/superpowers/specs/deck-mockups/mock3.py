import sys, json
D=json.load(open(sys.argv[1]))
CAR={"petrol":("Petrol","#ff9f0a"),"hybrid":("Full hybrid","#30d158"),"phev":("Plug-in hybrid","#bf5af2"),"bev":("Battery electric","#0a84ff")}
def th(dark): return dict(bg="#000" if dark else "#fff", fg="#f5f5f7" if dark else "#1d1d1f", mute="#86868b", soft="#1c1c1e" if dark else "#f5f5f7", line="#2c2c2e" if dark else "#e5e5ea")
def svg(t, body, foot=True, page="2"):
    f = f'<text x="80" y="862" fill="{t["mute"]}" font-size="18">First draft · placeholder wording</text><text x="1520" y="862" text-anchor="end" fill="{t["mute"]}" font-size="18">{page}</text>' if foot else ""
    return f'<svg viewBox="0 0 1600 900" style="width:100%;display:block;background:{t["bg"]};border-radius:12px;font-family:Inter,-apple-system,sans-serif">{body}{f}</svg>'
def trace(key, x0, y0, w, h, color, sw=3, op=1):
    c=D[key]; xs=c["x"]; vs=c["v"]; X=xs[-1]; V=150
    step=max(1,len(xs)//400)
    pts=" ".join(f'{x0+w*x/X:.1f},{y0+h-h*v/V:.1f}' for x,v in list(zip(xs,vs))[::step])
    return f'<polyline points="{pts}" fill="none" stroke="{color}" stroke-width="{sw}" stroke-linejoin="round" opacity="{op}"/>'
def head(t, eyebrow, title):
    return (f'<text x="800" y="92" text-anchor="middle" fill="{t["mute"]}" font-size="26" font-weight="500">{eyebrow}</text>'
            f'<text x="800" y="150" text-anchor="middle" fill="{t["fg"]}" font-size="46" font-weight="700" letter-spacing="-1">{title}</text>')
GROUP="Group of three · PWT Powertrains · ESILV 2026"
# ---- title slides
def title1(dark):
    t=th(dark)
    b=(f'<text x="800" y="380" text-anchor="middle" fill="{t["fg"]}" font-size="96" font-weight="700" letter-spacing="-3">Four cars. Four cycles.</text>'
       f'<text x="800" y="490" text-anchor="middle" fill="{t["mute"]}" font-size="96" font-weight="700" letter-spacing="-3">One model.</text>'
       f'<text x="800" y="600" text-anchor="middle" fill="{t["mute"]}" font-size="28">CO2 of petrol, electric, hybrid and plug-in hybrid cars</text>'
       f'<text x="800" y="790" text-anchor="middle" fill="{t["mute"]}" font-size="20">{GROUP}</text>')
    return svg(t,b,False)
def title2(dark):
    t=th(dark)
    b=trace("franco_sport_generated",0,520,1600,330,"#0a84ff",4,0.9)+trace("franco_eco_generated",0,520,1600,330,"#30d158",3,0.6)
    b+=(f'<text x="120" y="300" fill="{t["fg"]}" font-size="84" font-weight="700" letter-spacing="-2.5">Simulating CO2</text>'
        f'<text x="120" y="395" fill="{t["fg"]}" font-size="84" font-weight="700" letter-spacing="-2.5">on a lap of Spa.</text>'
        f'<text x="120" y="460" fill="{t["mute"]}" font-size="26">And on NEDC and WLTC. {GROUP}</text>'
        f'<text x="1480" y="880" text-anchor="end" fill="{t["mute"]}" font-size="18">Speed over one generated lap, sport and eco</text>')
    return svg(t,b,False)
def title3(dark):
    t=th(dark)
    dots="".join(f'<circle cx="{650+i*100}" cy="560" r="14" fill="{c}"/>' for i,(n,c) in enumerate(CAR.values()))
    b=(f'<text x="800" y="420" text-anchor="middle" fill="{t["fg"]}" font-size="78" font-weight="700" letter-spacing="-2">Where does the CO2 come from?</text>'
       f'<text x="800" y="490" text-anchor="middle" fill="{t["mute"]}" font-size="28">A driving-cycle simulation of four powertrains</text>{dots}'
       f'<text x="800" y="790" text-anchor="middle" fill="{t["mute"]}" font-size="20">{GROUP}</text>')
    return svg(t,b,False)
def divider(dark, num, title, sub, color):
    t=th(dark)
    b=(f'<text x="120" y="330" fill="{color}" font-size="30" font-weight="600">{num}</text>'
       f'<text x="120" y="440" fill="{t["fg"]}" font-size="104" font-weight="700" letter-spacing="-3">{title}</text>'
       f'<text x="120" y="510" fill="{t["mute"]}" font-size="30">{sub}</text>'
       f'<rect x="120" y="580" width="120" height="6" rx="3" fill="{color}"/>'
       f'<text x="120" y="790" fill="{t["mute"]}" font-size="22">Owner: (name) · 2.5 min</text>')
    return svg(t,b,False)
# ---- normal slides
def chain(dark):
    t=th(dark)
    steps=[("Speed trace","v(t) or v(s)"),("Forces","rolling · aero · grade · inertia"),("Wheel power","F · v"),
           ("Engine / motor","÷ transmission η, capability check"),("Energy","÷ engine η(P) · LHV"),("CO2","g/km, fuel + grid")]
    b=head(t,"The simulation","Every step of the trace, the same six steps")
    w,h,g=215,230,38; x0=800-(6*w+5*g)/2; y=380
    for i,(a,s) in enumerate(steps):
        x=x0+i*(w+g); last=i==5
        b+=f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="22" fill="{"#1d1d1f" if last and not dark else ("#f5f5f7" if last else t["soft"])}"/>'
        fc = ("#fff" if not dark else "#000") if last else t["fg"]
        b+=f'<text x="{x+w/2}" y="{y+70}" text-anchor="middle" fill="{t["mute"]}" font-size="20" font-weight="600">{i+1}</text>'
        b+=f'<text x="{x+w/2}" y="{y+125}" text-anchor="middle" fill="{fc}" font-size="28" font-weight="700">{a}</text>'
        words=s.split(" "); l1=" ".join(words[:3]); l2=" ".join(words[3:])
        b+=f'<text x="{x+w/2}" y="{y+170}" text-anchor="middle" fill="{t["mute"]}" font-size="17">{l1}</text><text x="{x+w/2}" y="{y+194}" text-anchor="middle" fill="{t["mute"]}" font-size="17">{l2}</text>'
        if i<5: b+=f'<path d="M{x+w+8},{y+h/2} l{g-16},0 m-8,-8 l8,8 l-8,8" stroke="{t["mute"]}" stroke-width="2.5" fill="none"/>'
    b+=f'<text x="800" y="720" text-anchor="middle" fill="{t["mute"]}" font-size="22">Summed over the cycle, divided by distance: l/100 km, kWh/100 km, g CO2/km</text>'
    return svg(t,b,page="3")
def carscycles(dark):
    t=th(dark)
    b=head(t,"What we drive","Four cars on four cycles")
    cyc=[("nedc","NEDC","urban + extra-urban"),("wltc","WLTC Class 3","highway phase included"),("franco_eco_generated","Spa eco","90 km/h cap"),("franco_sport_generated","Spa sport","engine-limited")]
    w,g=330,40; x0=800-(4*w+3*g)/2
    for i,(k,n,s) in enumerate(cyc):
        x=x0+i*(w+g); y=220
        b+=f'<rect x="{x}" y="{y}" width="{w}" height="270" rx="22" fill="{t["soft"]}"/>'
        b+=trace(k,x+25,y+40,w-50,140,t["fg"],2.5)
        b+=f'<text x="{x+25}" y="{y+220}" fill="{t["fg"]}" font-size="28" font-weight="700">{n}</text>'
        b+=f'<text x="{x+25}" y="{y+252}" fill="{t["mute"]}" font-size="19">{D[k]["km"]:.1f} km · {s}</text>'
    cars=[("petrol","1280 kg · 74 kW"),("hybrid","+100 kg · 1.5 kWh · 25 kW"),("phev","+100 kg · 15 kWh · 45 kW"),("bev","1460 kg · 22 kWh")]
    for i,(k,s) in enumerate(cars):
        x=x0+i*(w+g); y=560; n,c=CAR[k]
        b+=f'<circle cx="{x+40}" cy="{y+40}" r="16" fill="{c}"/><text x="{x+70}" y="{y+50}" fill="{t["fg"]}" font-size="28" font-weight="700">{n}</text>'
        b+=f'<text x="{x+70}" y="{y+86}" fill="{t["mute"]}" font-size="19">{s}</text>'
    b+=f'<text x="800" y="750" text-anchor="middle" fill="{t["mute"]}" font-size="20">Assignment-sheet vehicles · speed traces drawn from the model, 0–150 km/h</text>'
    return svg(t,b,page="4")
def tiles(dark):
    t=th(dark)
    b=head(t,"What we changed","From spreadsheets to a model that can decide")
    items=[("19","workbooks reproduced exactly in Python"),("74 kW","engine limit checked on every step"),("85 %","storage efficiency each way for hybrids"),("250","g CO2/kWh grid counted for every car")]
    w,g=330,40; x0=800-(4*w+3*g)/2
    for i,(n,s) in enumerate(items):
        x=x0+i*(w+g); y=300
        b+=f'<rect x="{x}" y="{y}" width="{w}" height="380" rx="26" fill="{t["soft"]}"/>'
        b+=f'<text x="{x+w/2}" y="{y+180}" text-anchor="middle" fill="{t["fg"]}" font-size="88" font-weight="700" letter-spacing="-3">{n}</text>'
        words=s.split(" "); h=len(words)//2
        b+=f'<text x="{x+w/2}" y="{y+260}" text-anchor="middle" fill="{t["mute"]}" font-size="22">{" ".join(words[:h])}</text><text x="{x+w/2}" y="{y+292}" text-anchor="middle" fill="{t["mute"]}" font-size="22">{" ".join(words[h:])}</text>'
    return svg(t,b,page="5")
def nextstep(dark):
    t=th(dark)
    b=head(t,"Limits and next step","What the model still gets wrong")
    rows=[("Fixed traces","Every car drives the petrol car's lap","Let each car generate its own lap"),
          ("Fixed hybrid strategy","Band not tuned to storage losses","Optimise the strategy per size"),
          ("Course constants","One efficiency curve per engine","Use a measured BSFC map")]
    y0=280
    b+=f'<text x="230" y="{y0}" fill="{t["mute"]}" font-size="20" font-weight="600">LIMIT</text><text x="900" y="{y0}" fill="{t["mute"]}" font-size="20" font-weight="600">NEXT STEP</text>'
    for i,(a,s,n) in enumerate(rows):
        y=y0+50+i*150
        b+=f'<line x1="230" x2="1370" y1="{y}" y2="{y}" stroke="{t["line"]}" stroke-width="2"/>'
        b+=f'<text x="230" y="{y+60}" fill="{t["fg"]}" font-size="32" font-weight="700">{a}</text><text x="230" y="{y+98}" fill="{t["mute"]}" font-size="22">{s}</text>'
        b+=f'<path d="M760,{y+62} l60,0 m-10,-10 l10,10 l-10,10" stroke="{t["mute"]}" stroke-width="2.5" fill="none"/>'
        b+=f'<text x="900" y="{y+72}" fill="{t["fg"]}" font-size="30" font-weight="600">{n}</text>'
    return svg(t,b,page="16")
def card(k,h,p,s,sel=True):
    on = f'data-choice="{k}" onclick="toggleSelect(this)"' if sel else ""
    return f'<div class="option" {on}><div class="letter">{k.upper()}</div><div class="content" style="width:100%"><h3>{h}</h3><p>{p}</p><div style="margin-top:10px;box-shadow:0 2px 16px rgba(0,0,0,.18);border-radius:12px">{s}</div></div></div>'
o=['<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">',
   '<h2>Title slides</h2><p class="subtitle">Pick the opening you like (click). All wording is placeholder, not the group\'s.</p><div class="options">',
   card("t1","Big statement, centred","Two lines of very large type; second line greyed. Pure Keynote.",title1(False)),
   card("t2","Real Spa lap as the image","The generated eco and sport speed traces run across the slide; title above.",title2(True)),
   card("t3","A question, with the four car colours","Opens on the question the talk answers; four dots introduce the colour code.",title3(False)),
   '</div><h2 style="margin-top:28px">Section titles (one before each study)</h2><div class="options">',
   card("s1","Light","Big study name, coloured number and bar, owner and time.",divider(False,"02 · Study A","Hybrid sizing","How big should the battery and motor be?","#30d158")),
   card("s2","Dark","Same on black.",divider(True,"03 · Study B","Sensitivity","Which parameter moves CO2 the most?","#0a84ff")),
   '</div><h2 style="margin-top:28px">Normal slides</h2><p class="subtitle">The group sections, each with one centred visual. Click any you like.</p><div class="options" data-multiselect>',
   card("n1","The model in six steps","Section 2: the calculation chain as one centred flow.",chain(False)),
   card("n2","Cars and cycles","Section 2: real speed traces from the model, the four cars with the colour code.",carscycles(False)),
   card("n3","What we changed","Section 2: four big numbers, one line each. Shown dark.",tiles(True)),
   card("n4","Limits and next step","Section 7: limit → next step, three rows.",nextstep(False)),
   '</div>']
open(sys.argv[2],"w").write("\n".join(o))
