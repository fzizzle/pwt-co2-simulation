import sys, json, math
exec(open(sys.argv[4]).read().split("def card(")[0])
LAP=T["franco_sport_generated"]
def base_pts(rot=90):
    lat=LAP["lat"]; lon=LAP["lon"]; sc=math.cos(math.radians(sum(lat)/len(lat)))
    pts=[(o*sc,-a) for a,o in zip(lat,lon)]
    if rot==90: pts=[(-y,x) for x,y in pts]
    xs=[p[0] for p in pts]; ys=[p[1] for p in pts]
    k=1/(max(xs)-min(xs)); mx=min(xs); my=min(ys)
    return [((x-mx)*k,(y-my)*k) for x,y in pts]   # unit width
ROT=int(sys.argv[5]) if len(sys.argv)>5 else 90
U=base_pts(ROT); S=LAP["s"]
def at(s):
    for i in range(len(S)-1):
        if S[i+1]>=s: return U[i]
    return U[-1]
def hfade(t,id,mid=0.6,x2="0.72"):
    c=t["bg"]
    return (f'<defs><linearGradient id="{id}" x1="0" x2="{x2}" y1="0" y2="0"><stop offset="0" stop-color="{c}" stop-opacity="1"/><stop offset="{mid}" stop-color="{c}" stop-opacity="0.8"/><stop offset="1" stop-color="{c}" stop-opacity="0"/></linearGradient></defs>'
            f'<rect x="0" y="0" width="1600" height="900" fill="url(#{id})"/>')
def zoomed(t, s_focus, zoom, fx, fy, sw):
    # unit coords -> screen: focus point lands at (fx,fy); full lap width = 1600*zoom px
    W=1600*zoom; ux,uy=at(s_focus)
    P=[(fx+(x-ux)*W, fy+(y-uy)*W) for x,y in U]
    out=f'<polyline points="'+" ".join(f"{x:.1f},{y:.1f}" for x,y in P)+f'" fill="none" stroke="{t["line"]}" stroke-width="{sw+14}" stroke-linecap="round" stroke-linejoin="round"/>'
    for i in range(len(P)-1):
        (x1,y1),(x2,y2)=P[i],P[i+1]
        if max(x1,x2)<-50 or min(x1,x2)>1650 or max(y1,y2)<-50 or min(y1,y2)>950: continue
        out+=f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{col((LAP["v"][i]-VMIN)/(VMAX-VMIN))}" stroke-width="{sw}" stroke-linecap="round"/>'
    return out
def mini(t, s, x0, y0, w):
    hmax=max(y for _,y in U)
    if hmax*w>150: w=150/hmax; y0=y0-20
    P=[(x0+x*w,y0+y*w) for x,y in U]
    out=f'<polyline points="'+" ".join(f"{x:.1f},{y:.1f}" for x,y in P)+f'" fill="none" stroke="{t["mute"]}" stroke-width="3" stroke-linejoin="round" opacity="0.6"/>'
    x,y=at(s); out+=f'<circle cx="{x0+x*w:.1f}" cy="{y0+y*w:.1f}" r="8" fill="{t["fg"]}"/>'
    return out
SECTIONS=[(0,"Start / finish","PWT · Powertrains","Four cars. Four cycles.",2.2),
          (220,"La Source","01","The simulation",3.2),
          (1010,"Eau Rouge","02","Four cars compared",2.8),
          (2200,"Les Combes","03 · Study A","Hybrid sizing",3.0),
          (3600,"Pouhon","04 · Study B","Sensitivity",2.8),
          (4740,"Stavelot","05 · Study C","Cornering speed",3.0),
          (6540,"Bus Stop","06","Limits and next step",3.4),
          (6990,"Start / finish","","Questions?",2.2)]
def opener(dark,i):
    t=th(dark); s,corner,num,title,z=SECTIONS[i]
    b=zoomed(t,s,z,1180,450,30)+hfade(t,f"z{i}{int(dark)}")
    b+=(f'<text x="110" y="380" fill="{t["mute"]}" font-size="28" font-weight="600">{num}</text>'
        f'<text x="110" y="480" fill="{t["fg"]}" font-size="96" font-weight="700" letter-spacing="-3.5">{title}</text>'
        f'<text x="110" y="540" fill="{t["mute"]}" font-size="28">{corner} · {s/1000:.1f} km</text>')
    b+=mini(t,s,110,700,230)
    return svg(t,b,False)
def shadow(s): return f'<div style="box-shadow:0 2px 12px rgba(0,0,0,.18);border-radius:10px;overflow:hidden">{s}</div>'
strip=lambda dark:'<div style="display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin-top:10px">'+"".join(shadow(opener(dark,i)) for i in range(len(SECTIONS)))+'</div>'
o=['<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">',
 '<h2>Each title slide zooms in on the next corner</h2>',
 '<p class="subtitle">Close-up of one corner per section, in lap order, coloured by the generated sport lap\'s speed and fading into the title. A small whole-lap map bottom-left shows where that corner is. Corner-to-section matching and wording are placeholders.</p>',
 '<h3 style="margin-top:18px">All section openers, in order (dark)</h3>', strip(True),
 '<h3 style="margin-top:22px">The same, light</h3>', strip(False),
 '<h3 style="margin-top:22px">Full size</h3>', '<div class="split" style="margin-top:10px">', shadow(opener(True,2)), shadow(opener(False,5)), '</div>']
open(sys.argv[3],"w").write("\n".join(o))
