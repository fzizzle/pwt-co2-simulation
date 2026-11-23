import sys, json, math
exec(open(sys.argv[4]).read().split("def card(")[0])
def rproj(lap, cx, cy, width, rot):
    lat=lap["lat"]; lon=lap["lon"]; sc=math.cos(math.radians(sum(lat)/len(lat)))
    pts=[(o*sc,-a) for a,o in zip(lat,lon)]  # screen coords, y down
    if rot==90: pts=[(-y,x) for x,y in pts]      # clockwise
    elif rot==-90: pts=[(y,-x) for x,y in pts]   # counter-clockwise
    xs=[p[0] for p in pts]; ys=[p[1] for p in pts]
    k=width/(max(xs)-min(xs)); mx=(max(xs)+min(xs))/2; my=(max(ys)+min(ys))/2
    return [(cx+(x-mx)*k, cy+(y-my)*k) for x,y in pts], k*(max(ys)-min(ys))
def rtrack(cx,cy,width,rot,sw,op=1,mono=None):
    lap=T["franco_sport_generated"]; pts,_=rproj(lap,cx,cy,width,rot)
    if mono: return f'<polyline opacity="{op}" points="'+" ".join(f"{x:.1f},{y:.1f}" for x,y in pts)+f'" fill="none" stroke="{mono}" stroke-width="{sw}" stroke-linecap="round" stroke-linejoin="round"/>'
    out=f'<g opacity="{op}">'
    for i in range(len(pts)-1):
        (x1,y1),(x2,y2)=pts[i],pts[i+1]
        out+=f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{col((lap["v"][i]-VMIN)/(VMAX-VMIN))}" stroke-width="{sw}" stroke-linecap="round"/>'
    return out+'</g>'
def hfade(t,id,x1,x2,y1="0",y2="0",mid=0.5):
    c=t["bg"]
    return (f'<defs><linearGradient id="{id}" x1="{x1}" x2="{x2}" y1="{y1}" y2="{y2}"><stop offset="0" stop-color="{c}" stop-opacity="1"/><stop offset="{mid}" stop-color="{c}" stop-opacity="0.75"/><stop offset="1" stop-color="{c}" stop-opacity="0"/></linearGradient></defs>'
            f'<rect x="0" y="0" width="1600" height="900" fill="url(#{id})"/>')
def r1(dark,rot,id):
    t=th(dark)
    b=rtrack(1020,450,1000,rot,20)+hfade(t,id,"0","0.85",mid=0.45)
    b+=(f'<text x="110" y="470" fill="{t["fg"]}" font-size="110" font-weight="700" letter-spacing="-4">Spa, in CO2.</text>'
        f'<text x="110" y="535" fill="{t["mute"]}" font-size="28">Four powertrains on four driving cycles</text>'
        f'<text x="110" y="800" fill="{t["mute"]}" font-size="20">{GROUP}</text>')
    return svg(t,b,False)
def r3(dark,rot,id):
    t=th(dark)
    b=rtrack(800,360,1250,rot,18)+hfade(t,id,"0","0","1","0.25",mid=0.35)
    b+=(f'<text x="800" y="700" text-anchor="middle" fill="{t["fg"]}" font-size="96" font-weight="700" letter-spacing="-3">Four cars. Four cycles.</text>'
        f'<text x="800" y="765" text-anchor="middle" fill="{t["mute"]}" font-size="28">Simulating the CO2 of four powertrains · {GROUP}</text>')
    return svg(t,b,False)
def r4(dark,rot,id):
    t=th(dark)
    b=rtrack(1000,470,1050,rot,22)+hfade(t,id,"0","0.85",mid=0.45)
    b+=(f'<text x="110" y="360" fill="#ff9f0a" font-size="30" font-weight="600">04 · Study C</text>'
        f'<text x="110" y="470" fill="{t["fg"]}" font-size="104" font-weight="700" letter-spacing="-4">Cornering speed</text>'
        f'<text x="110" y="535" fill="{t["mute"]}" font-size="30">Do grippier tyres or a spoiler save CO2?</text>'
        f'<text x="110" y="790" fill="{t["mute"]}" font-size="22">Owner: (name) · 2.5 min</text>')
    return svg(t,b,False)
def r5(dark,rot,id):
    t=th(dark)
    b=rtrack(1060,470,900,rot,14)+hfade(t,id,"0.05","0.8",mid=0.4)
    b+=(f'<text x="110" y="270" fill="{t["mute"]}" font-size="26" font-weight="500">Petrol car, one sport lap</text>'
        f'<text x="100" y="500" fill="{t["fg"]}" font-size="220" font-weight="700" letter-spacing="-10">385</text>'
        f'<text x="110" y="565" fill="{t["fg"]}" font-size="36" font-weight="600">g CO2/km</text>'
        f'<text x="110" y="620" fill="{t["mute"]}" font-size="26">against 217.5 on the eco lap of the same track</text>')
    b+=legend(t,110,720,230)
    return svg(t,b,page="7")
def card(k,h,p,s):
    return f'<div class="option" data-choice="{k}" onclick="toggleSelect(this)"><div class="letter">{k.upper()}</div><div class="content" style="width:100%"><h3>{h}</h3><p>{p}</p><div style="margin-top:10px;box-shadow:0 2px 16px rgba(0,0,0,.18);border-radius:12px;overflow:hidden">{s}</div></div></div>'
o=['<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">',
 '<h2>Track rotated 90°, whole circuit visible, with the fade</h2><p class="subtitle">Real Spa outline, coloured by the generated sport lap\'s speed. Wording is placeholder. Click any you like.</p><div class="options" data-multiselect>',
 card("r1","Title, dark, turned clockwise","The fade from the first one; the whole circuit now lies on its side to the right.",r1(True,90,"a1")),
 card("r2","Title, dark, turned anticlockwise","Same, rotated the other way, so La Source sits on the left.",r1(True,-90,"a2")),
 card("r3","Title, light, turned clockwise","The same layout on white.",r1(False,90,"a3")),
 card("r4","Title, dark: track across the top, title below","The rotated circuit spans the width and fades downward into the title.",r3(True,90,"a4")),
 card("r5","Section title, dark","The fade layout used for a study divider.",r4(True,-90,"a5")),
 card("r6","One big number, light","A single result beside the rotated track.",r5(False,90,"a6")),
 '</div>']
open(sys.argv[3],"w").write("\n".join(o))
