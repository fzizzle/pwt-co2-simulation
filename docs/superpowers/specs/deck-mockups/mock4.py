import sys, json, math
T=json.load(open(sys.argv[1])); D=json.load(open(sys.argv[2]))
def th(dark): return dict(bg="#000" if dark else "#fff", fg="#f5f5f7" if dark else "#1d1d1f", mute="#86868b", soft="#1c1c1e" if dark else "#f5f5f7", line="#2c2c2e" if dark else "#e5e5ea")
def svg(t, body, foot=True, page="4"):
    f = f'<text x="80" y="862" fill="{t["mute"]}" font-size="18">First draft · placeholder wording · model output</text><text x="1520" y="862" text-anchor="end" fill="{t["mute"]}" font-size="18">{page}</text>' if foot else ""
    return f'<svg viewBox="0 0 1600 900" style="width:100%;display:block;background:{t["bg"]};border-radius:12px;font-family:Inter,-apple-system,sans-serif">{body}{f}</svg>'
# speed ramp: blue (slow) -> green -> yellow -> orange (fast)
STOPS=[(0,(10,132,255)),(0.45,(48,209,88)),(0.75,(255,214,10)),(1,(255,69,58))]
def col(f):
    f=max(0,min(1,f))
    for (a,ca),(b,cb) in zip(STOPS,STOPS[1:]):
        if f<=b:
            u=(f-a)/(b-a); return "#%02x%02x%02x"%tuple(round(x+(y-x)*u) for x,y in zip(ca,cb))
VMIN,VMAX=40,150
def proj(lap, cx, cy, size):
    lat=lap["lat"]; lon=lap["lon"]; sc=math.cos(math.radians(sum(lat)/len(lat)))
    xs=[o*sc for o in lon]; ys=lat
    w=max(xs)-min(xs); h=max(ys)-min(ys); k=size/max(w,h)
    mx=(max(xs)+min(xs))/2; my=(max(ys)+min(ys))/2
    return lambda la,lo:(cx+(lo*sc-mx)*k, cy-(la-my)*k)
def track(t, key, cx, cy, size, sw=14, labels=False, under=True):
    lap=T[key]; P=proj(T["franco_sport_generated"],cx,cy,size)
    pts=[P(a,o) for a,o in zip(lap["lat"],lap["lon"])]
    out=""
    if under:
        out+='<polyline points="'+" ".join(f"{x:.1f},{y:.1f}" for x,y in pts)+f'" fill="none" stroke="{t["line"]}" stroke-width="{sw+10}" stroke-linecap="round" stroke-linejoin="round"/>'
    for i in range(0,len(pts)-1):
        (x1,y1),(x2,y2)=pts[i],pts[i+1]; v=lap["v"][i]
        out+=f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{col((v-VMIN)/(VMAX-VMIN))}" stroke-width="{sw}" stroke-linecap="round"/>'
    if labels:
        for L in T["landmarks"]:
            x,y=P(L["lat"],L["lon"])
            left=L["name"] in ("Bus Stop","Blanchimont","Stavelot","Fagnes"); a="end" if left else "start"; dx=-16 if left else 16
            out+=f'<circle cx="{x:.1f}" cy="{y:.1f}" r="5" fill="{t["fg"]}"/><text x="{x+dx:.1f}" y="{y+6:.1f}" text-anchor="{a}" fill="{t["mute"]}" font-size="19" font-weight="500">{L["name"]}</text>'
    x,y=pts[0]
    out+=f'<rect x="{x-4:.1f}" y="{y-16:.1f}" width="8" height="32" rx="2" fill="{t["fg"]}"/>'
    return out
def legend(t,x,y,w):
    n=40; out=""
    for i in range(n): out+=f'<rect x="{x+w*i/n:.1f}" y="{y}" width="{w/n+0.5:.1f}" height="10" fill="{col(i/(n-1))}"/>'
    out+=f'<text x="{x}" y="{y+36}" fill="{t["mute"]}" font-size="18">{VMIN} km/h</text><text x="{x+w}" y="{y+36}" text-anchor="end" fill="{t["mute"]}" font-size="18">{VMAX} km/h</text>'
    return out
def head(t, eyebrow, title):
    return (f'<text x="800" y="92" text-anchor="middle" fill="{t["mute"]}" font-size="26" font-weight="500">{eyebrow}</text>'
            f'<text x="800" y="150" text-anchor="middle" fill="{t["fg"]}" font-size="46" font-weight="700" letter-spacing="-1">{title}</text>')
GROUP="Group of three · PWT Powertrains · ESILV 2026"
def m_title():
    t=th(True)
    b=track(t,"franco_sport_generated",1060,450,620,12)
    b+=(f'<text x="110" y="330" fill="{t["fg"]}" font-size="80" font-weight="700" letter-spacing="-2.5">Four cars.</text>'
        f'<text x="110" y="420" fill="{t["fg"]}" font-size="80" font-weight="700" letter-spacing="-2.5">One lap of Spa.</text>'
        f'<text x="110" y="480" fill="{t["mute"]}" font-size="26">And NEDC and WLTC. The CO2 of four powertrains.</text>'
        f'<text x="110" y="790" fill="{t["mute"]}" font-size="20">{GROUP}</text>')
    b+=legend(t,1250,790,230)
    return svg(t,b,False)
def m_title_light():
    t=th(False)
    b=track(t,"franco_sport_generated",800,420,560,12,under=True)
    b+=(f'<text x="800" y="790" text-anchor="middle" fill="{t["fg"]}" font-size="54" font-weight="700" letter-spacing="-1.5">Simulating CO2 on Spa-Francorchamps</text>'
        f'<text x="800" y="840" text-anchor="middle" fill="{t["mute"]}" font-size="22">{GROUP}</text>')
    return svg(t,b,False)
def m_centre():
    t=th(False)
    b=head(t,"Francorchamps sport, generated lap","Where the sport lap is fast, and where it brakes")
    b+=track(t,"franco_sport_generated",800,500,560,14,labels=True)
    b+=legend(t,1250,700,240)
    b+=f'<text x="1250" y="680" fill="{t["mute"]}" font-size="18" font-weight="600">SPEED</text>'
    return svg(t,b)
def m_split(dark):
    t=th(dark)
    b=head(t,"Same lap, two drivers","Sport driving more than doubles the speed range")
    b+=track(t,"franco_sport_generated",460,500,470,11,labels=False)
    # speed traces on right
    x0,y0,w,h=850,260,640,420
    b+=f'<line x1="{x0}" x2="{x0+w}" y1="{y0+h}" y2="{y0+h}" stroke="{t["line"]}" stroke-width="2"/>'
    for key,color,name in (("franco_sport_generated","#ff453a","Sport"),("franco_eco_generated","#30d158","Eco")):
        xs=D[key]["x"]; vs=D[key]["v"]; X=xs[-1]
        pts=" ".join(f"{x0+w*x/X:.1f},{y0+h-h*v/160:.1f}" for x,v in list(zip(xs,vs))[::3])
        b+=f'<polyline points="{pts}" fill="none" stroke="{color}" stroke-width="3.5" stroke-linejoin="round"/>'
    b+=f'<text x="{x0}" y="{y0-20}" fill="{t["mute"]}" font-size="18" font-weight="600">SPEED OVER THE LAP</text>'
    b+=f'<circle cx="{x0+w-150}" cy="{y0-26}" r="7" fill="#ff453a"/><text x="{x0+w-136}" y="{y0-19}" fill="{t["mute"]}" font-size="18">Sport</text>'
    b+=f'<circle cx="{x0+w-60}" cy="{y0-26}" r="7" fill="#30d158"/><text x="{x0+w-46}" y="{y0-19}" fill="{t["mute"]}" font-size="18">Eco</text>'
    b+=f'<text x="{x0}" y="{y0+h+34}" fill="{t["mute"]}" font-size="18">0 km</text><text x="{x0+w}" y="{y0+h+34}" text-anchor="end" fill="{t["mute"]}" font-size="18">7 km</text>'
    b+=legend(t,240,790,240)
    return svg(t,b)
def card(k,h,p,s):
    return f'<div class="option" data-choice="{k}" onclick="toggleSelect(this)"><div class="letter">{k.upper()}</div><div class="content" style="width:100%"><h3>{h}</h3><p>{p}</p><div style="margin-top:10px;box-shadow:0 2px 16px rgba(0,0,0,.18);border-radius:12px">{s}</div></div></div>'
o=['<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">',
 '<h2>With the Spa track map</h2><p class="subtitle">The real circuit outline, coloured by the speed of the generated sport lap (model output). Wording is placeholder. Click the ones you like.</p><div class="options" data-multiselect>',
 card("m1","Title, dark: track beside the title","The circuit glows on black on the right; title on the left; speed scale bottom right.",m_title()),
 card("m2","Title, light: track as the centrepiece","The circuit fills the slide; title underneath.",m_title_light()),
 card("m3","Normal slide: the lap on the map","Centred map, corner names, speed scale. For introducing the Spa cycles (section 2) or Study C.",m_centre()),
 card("m4","Normal slide: map beside the speed trace","Map left, eco and sport speed over the lap right. Shown dark.",m_split(True)),
 '</div>']
open(sys.argv[3],"w").write("\n".join(o))
