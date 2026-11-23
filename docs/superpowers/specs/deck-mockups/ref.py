import sys, json, math
exec(open(sys.argv[3]).read().split("def card(")[0])
LAP=T["franco_sport_generated"]
def pts(rot):
    lat=LAP["lat"]; lon=LAP["lon"]; sc=math.cos(math.radians(sum(lat)/len(lat)))
    P=[(o*sc,-a) for a,o in zip(lat,lon)]
    if rot==90: P=[(-y,x) for x,y in P]
    return P
def ref(rot, title):
    t=th(False); P=pts(rot)
    xs=[p[0] for p in P]; ys=[p[1] for p in P]
    k=min(1200/(max(xs)-min(xs)),640/(max(ys)-min(ys)))
    cx=(max(xs)+min(xs))/2; cy=(max(ys)+min(ys))/2
    Q=[(800+(x-cx)*k, 500+(y-cy)*k) for x,y in P]
    b=f'<text x="800" y="90" text-anchor="middle" fill="{t["fg"]}" font-size="40" font-weight="700">{title}</text>'
    for i in range(len(Q)-1):
        (x1,y1),(x2,y2)=Q[i],Q[i+1]
        b+=f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{col((LAP["v"][i]-VMIN)/(VMAX-VMIN))}" stroke-width="12" stroke-linecap="round"/>'
    # direction arrows every ~1 km
    S=LAP["s"]
    for target in (500,1600,2600,4000,5400,6300):
        i=next(j for j in range(len(S)) if S[j]>=target); (x1,y1),(x2,y2)=Q[i],Q[i+3]
        a=math.degrees(math.atan2(y2-y1,x2-x1))
        b+=f'<path d="M-14,-11 L10,0 L-14,11 Z" fill="{t["fg"]}" transform="translate({x1:.1f},{y1:.1f}) rotate({a:.1f})"/>'
    for L in T["landmarks"]:
        i=next(j for j in range(len(S)) if S[j]>=L["s"]); x,y=Q[i]
        b+=f'<circle cx="{x:.1f}" cy="{y:.1f}" r="6" fill="{t["fg"]}"/><text x="{x+14:.1f}" y="{y-10:.1f}" fill="{t["fg"]}" font-size="20" font-weight="600">{L["name"]}</text>'
    x,y=Q[0]; b+=f'<text x="{x:.1f}" y="{y+40:.1f}" text-anchor="middle" fill="{t["mute"]}" font-size="20">start / finish</text>'
    if rot==0: b+=f'<text x="1480" y="150" text-anchor="middle" fill="{t["mute"]}" font-size="22" font-weight="600">N ↑</text>'
    else: b+=f'<text x="1480" y="150" text-anchor="middle" fill="{t["mute"]}" font-size="22" font-weight="600">N →</text>'
    return svg(t,b,False)
open(sys.argv[4],"w").write('<div class="split">'+f'<div style="box-shadow:0 2px 12px rgba(0,0,0,.18);border-radius:10px;overflow:hidden">{ref(0,"True orientation, north up")}</div>'+f'<div style="box-shadow:0 2px 12px rgba(0,0,0,.18);border-radius:10px;overflow:hidden">{ref(90,"Rotated 90° clockwise")}</div></div>')
