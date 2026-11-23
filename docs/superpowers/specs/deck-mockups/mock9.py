import sys, json, math
exec(open(sys.argv[3]).read().split("def card(")[0])
LAP=T["franco_sport_generated"]; S=LAP["s"]; V=LAP["v"]
def unit(rot):
    lat=LAP["lat"]; lon=LAP["lon"]; sc=math.cos(math.radians(sum(lat)/len(lat)))
    P=[(o*sc,-a) for a,o in zip(lat,lon)]
    if rot==90: P=[(-y,x) for x,y in P]
    xs=[p[0] for p in P]; ys=[p[1] for p in P]; k=1/(max(xs)-min(xs))
    return [((x-min(xs))*k,(y-min(ys))*k) for x,y in P]
def idx(s): return next(j for j in range(len(S)) if S[j]>=s)
def screen(rot, s_focus, zoom, fx, fy):
    U=unit(rot); W=1600*zoom; ux,uy=U[idx(s_focus)]
    return [(fx+(x-ux)*W, fy+(y-uy)*W) for x,y in U]
def curv(P,i,k=4):
    a=P[max(i-k,0)]; b=P[i]; c=P[min(i+k,len(P)-1)]
    h1=math.atan2(b[1]-a[1],b[0]-a[0]); h2=math.atan2(c[1]-b[1],c[0]-b[0])
    d=(h2-h1+math.pi)%(2*math.pi)-math.pi
    L=math.hypot(b[0]-a[0],b[1]-a[1])+math.hypot(c[0]-b[0],c[1]-b[1])
    return d/max(L,1e-6), a, c
def kerbs(P, sw, kw, thresh, onscreen):
    runs=[]; cur=[]
    for i in range(len(P)):
        k,a,c=curv(P,i)
        if abs(k)>thresh and onscreen(P[i]):
            mx,my=(a[0]+c[0])/2-P[i][0],(a[1]+c[1])/2-P[i][1]; n=math.hypot(mx,my) or 1
            off=sw/2+kw/2
            cur.append((P[i][0]+mx/n*off,P[i][1]+my/n*off))
        else:
            if len(cur)>2: runs.append(cur)
            cur=[]
    if len(cur)>2: runs.append(cur)
    out=""
    for r in runs:
        pl=" ".join(f"{x:.1f},{y:.1f}" for x,y in r)
        out+=f'<polyline points="{pl}" fill="none" stroke="#ffffff" stroke-width="{kw}" stroke-linejoin="round"/>'
        out+=f'<polyline points="{pl}" fill="none" stroke="#e5352b" stroke-width="{kw}" stroke-dasharray="{kw*1.1:.1f} {kw*1.1:.1f}" stroke-linejoin="round"/>'
    return out
def onscr(p): return -100<p[0]<1700 and -100<p[1]<1000
def speedline(P, sw):
    out=""
    for i in range(len(P)-1):
        (x1,y1),(x2,y2)=P[i],P[i+1]
        if not (onscr(P[i]) or onscr(P[i+1])): continue
        out+=f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{col((V[i]-VMIN)/(VMAX-VMIN))}" stroke-width="{sw}" stroke-linecap="round"/>'
    return out
def poly(P,stroke,sw,extra=""):
    Q=[p for p in P]
    return f'<polyline points="'+" ".join(f"{x:.1f},{y:.1f}" for x,y in Q)+f'" fill="none" stroke="{stroke}" stroke-width="{sw}" stroke-linecap="round" stroke-linejoin="round" {extra}/>'
def fadeL(t,id):
    c=t["bg"]
    return (f'<defs><linearGradient id="{id}" x1="0" x2="0.62" y1="0" y2="0"><stop offset="0" stop-color="{c}" stop-opacity="1"/><stop offset="0.55" stop-color="{c}" stop-opacity="0.8"/><stop offset="1" stop-color="{c}" stop-opacity="0"/></linearGradient></defs>'
            f'<rect x="0" y="0" width="1600" height="900" fill="url(#{id})"/>')
def minimap(t,rot,s,x0,y0,w):
    U=unit(rot); hm=max(y for _,y in U)
    if hm*w>150: w=150/hm
    P=[(x0+x*w,y0+y*w) for x,y in U]; x,y=P[idx(s)]
    return poly(P,t["mute"],3,'opacity="0.6"')+f'<circle cx="{x:.1f}" cy="{y:.1f}" r="8" fill="{t["fg"]}"/>'
def boards(P, s_corner, sw, t):
    # 150/100/50 m braking boards on the outside before the corner
    out=""
    for d,lab in ((150,"3"),(100,"2"),(50,"1")):
        i=idx(max(s_corner-d,0)); k,a,c=curv(P,i,6)
        hx,hy=c[0]-a[0],c[1]-a[1]; n=math.hypot(hx,hy) or 1; nx,ny=-hy/n,hx/n
        # pick the side away from the upcoming corner's centre
        j=idx(s_corner); _,a2,c2=curv(P,j); mx,my=(a2[0]+c2[0])/2-P[j][0],(a2[1]+c2[1])/2-P[j][1]
        side=-1 if nx*mx+ny*my>0 else 1
        x,y=P[i][0]+side*nx*(sw/2+40),P[i][1]+side*ny*(sw/2+40)
        if onscr((x,y)):
            out+=f'<rect x="{x-17:.1f}" y="{y-22:.1f}" width="34" height="44" rx="5" fill="#fff" stroke="{t["line"]}" stroke-width="2"/><text x="{x:.1f}" y="{y+10:.1f}" text-anchor="middle" fill="#1d1d1f" font-size="28" font-weight="700">{lab}</text>'
    return out
def opener(dark, rot, s, zoom, num, title, corner, style, gid):
    t=th(dark); sw=34
    P=screen(rot,s,zoom,1180,450)
    th_=0.0016
    if style=="kerb":
        b=kerbs(P,sw,14,th_,onscr)+speedline(P,sw)
    elif style=="tarmac":
        tar="#3a3a3c" if dark else "#d9d9de"
        b=poly(P,"#ffffff" if not dark else "#8e8e93",sw+30)+poly(P,tar,sw+22)+kerbs(P,sw+30,14,th_,onscr)+speedline(P,8)
    else:  # tarmac + boards + apex
        tar="#3a3a3c" if dark else "#d9d9de"
        b=poly(P,"#ffffff" if not dark else "#8e8e93",sw+30)+poly(P,tar,sw+22)+kerbs(P,sw+30,14,th_,onscr)+speedline(P,8)+boards(P,s,sw+30,t)
    b+=fadeL(t,gid)
    b+=(f'<text x="110" y="380" fill="{t["mute"]}" font-size="28" font-weight="600">{num}</text>'
        f'<text x="110" y="480" fill="{t["fg"]}" font-size="96" font-weight="700" letter-spacing="-3.5">{title}</text>'
        f'<text x="110" y="540" fill="{t["mute"]}" font-size="28">{corner} · {s/1000:.1f} km</text>')
    b+=minimap(t,rot,s,110,690,230)
    return svg(t,b,False)
def shadow(s): return f'<div style="box-shadow:0 2px 12px rgba(0,0,0,.18);border-radius:10px;overflow:hidden">{s}</div>'
SEC=[(220,"01","The simulation","La Source",3.2),(1010,"02","Four cars compared","Eau Rouge",2.8),(4740,"05 · Study C","Cornering speed","Stavelot",3.0),(6540,"06","Limits and next step","Bus Stop",3.4)]
def row(dark,rot,style,tag):
    return '<div class="split" style="margin-top:10px">'+"".join(shadow(opener(dark,rot,*[SEC[i][0],SEC[i][4],SEC[i][1],SEC[i][2],SEC[i][3]],style,f"{tag}{i}")) for i in (0,3))+'</div>'
o=['<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">',
 '<h2>Making the corners read as corners</h2><p class="subtitle">Red-and-white kerbs drawn automatically on the inside of every bend tighter than a set radius (from the real outline). North up. Shown on La Source (hairpin) and Bus Stop (chicane). Click the treatment you like.</p>',
 '<div class="options">',
 f'<div class="option" data-choice="k1" onclick="toggleSelect(this)"><div class="letter">1</div><div class="content" style="width:100%"><h3>Kerbs on the speed ribbon</h3><p>The coloured track as before, plus kerbs on the apexes.</p>{row(True,0,"kerb","a")}{row(False,0,"kerb","b")}</div></div>',
 f'<div class="option" data-choice="k2" onclick="toggleSelect(this)"><div class="letter">2</div><div class="content" style="width:100%"><h3>Tarmac with kerbs, speed as the racing line</h3><p>A grey road with white edges and kerbs; the speed colours become a thin line along it.</p>{row(True,0,"tarmac","c")}{row(False,0,"tarmac","d")}</div></div>',
 f'<div class="option" data-choice="k3" onclick="toggleSelect(this)"><div class="letter">3</div><div class="content" style="width:100%"><h3>Tarmac, kerbs and braking boards</h3><p>Adds the 3-2-1 boards (150, 100, 50 m) before the corner on the outside.</p>{row(True,0,"boards","e")}{row(False,0,"boards","f")}</div></div>',
 '</div>']
open(sys.argv[4],"w").write("\n".join(o))
