import sys, json, math
_src=open(sys.argv[6]).read(); exec(_src[:_src.find("\ndef deck(")])   # mock15: look helpers
DATA=json.load(open(sys.argv[7]))
CARS=[("petrol","Petrol","#d09539"),("hybrid","Full hybrid","#4fb267"),("phev","Plug-in hybrid","#b677d5"),("bev","Battery electric","#3984d0")]
# one fixed spot for the little lap on every slide: a box at the bottom right, whole outline inside it
MINI=(1452,44,62,100)   # top right: x, y, max width, max height
LABEL=['']; POS=[None]
def minimap(t, *a):
    s = POS[0] if POS[0] is not None else (a[1] if len(a) >= 2 else a[0])
    U=unit(0); xs=[p[0] for p in U]; ys=[p[1] for p in U]
    x0,y0,W,H=MINI; k=min(W/(max(xs)-min(xs)), H/(max(ys)-min(ys)))
    ox=x0+(W-(max(xs)-min(xs))*k)/2; oy=y0+(H-(max(ys)-min(ys))*k)/2
    P=[(ox+(x-min(xs))*k, oy+(y-min(ys))*k) for x,y in U]
    x,y=P[idx(s)]
    lab=""
    if LABEL[0]:
        # place the number beside the dot, never on the outline: try spots round the dot, pick the clearest
        tw=10.5*len(LABEL[0]); th_=14; gx=sum(q[0] for q in P)/len(P); gy=sum(q[1] for q in P)/len(P)
        best=None
        for ang in range(0,360,15):
            for r in (16,20,26,32):
                lx=x+r*math.cos(math.radians(ang)); ly=y+r*math.sin(math.radians(ang))
                box=(lx-tw/2-3, ly-th_/2-3, lx+tw/2+3, ly+th_/2+3)
                clear=min(max(box[0]-q[0], q[0]-box[2], box[1]-q[1], q[1]-box[3]) for q in P)  # >0: outside box
                away=math.hypot(lx-gx,ly-gy)
                score=(0 if clear>2 else 1, r, -away)
                if best is None or score<best[0]: best=(score,lx,ly)
        _,lx,ly=best
        lab=f'<text x="{lx:.1f}" y="{ly+6:.1f}" text-anchor="middle" fill="{t["fg"]}" font-size="18" font-weight="600">{LABEL[0]}</text>'
    return poly(P,t["mute"],2.5,'opacity="0.7"')+f'<circle cx="{x:.1f}" cy="{y:.1f}" r="6" fill="{t["fg"]}"/>'+lab
CYC=[("nedc","NEDC"),("wltc","WLTC Class 3"),("franco_eco_generated","Francorchamps eco"),("franco_sport_generated","Francorchamps sport")]
CO2=DATA["co2"]; SHORT=DATA["short"]
PH='font-style="italic"'
def yours(t,x,y,txt,size,anchor="start",w=700):
    return f'<text x="{x}" y="{y}" text-anchor="{anchor}" fill="{t["mute"]}" opacity="0.75" font-size="{size}" font-weight="600" {PH}>{txt}</text>'
def frame(t, label, headline_hint, page, s_pos, body):
    b=(f'<text x="110" y="92" fill="{t["mute"]}" font-size="24" font-weight="500">{label}</text>'
       + yours(t,110,150,headline_hint,44))
    b+=body
    # footer: units / provenance left, tiny lap with position, page right
    b+=f'<text x="110" y="862" fill="{t["mute"]}" font-size="17">model output · first draft</text>'
    b+=minimap(t,s_pos)
    return svg(t,b,False)
def legend(t,y):
    lx=800-4*210/2; out=""
    for i,(k,n,c) in enumerate(CARS):
        out+=f'<circle cx="{lx+i*210+10}" cy="{y}" r="9" fill="{c}"/><text x="{lx+i*210+28}" y="{y+8}" fill="{t["mute"]}" font-size="21">{n}</text>'
    return out
def grouped(t):
    base,top=750,300; mx=max(CO2[k][c] for k,_,_ in CARS for c,_ in CYC); bw,inner,gap=60,10,100
    gw=4*bw+3*inner; x0=800-(4*gw+3*gap)/2; out=legend(t,225)
    for g,(ck,cn) in enumerate(CYC):
        gx=x0+g*(gw+gap)
        for i,(k,n,c) in enumerate(CARS):
            v=CO2[k][ck]; h=(base-top)*v/mx; x=gx+i*(bw+inner); hollow=SHORT[k][ck]>0
            fill=f'fill="{c}"' if not hollow else f'fill="none" stroke="{c}" stroke-width="3"'
            out+=f'<path d="M{x},{base} V{base-h+3} q0,-3 3,-3 H{x+bw-3} q3,0 3,3 V{base} Z" {fill}/>'
            out+=f'<text x="{x+bw/2}" y="{base-h-12}" text-anchor="middle" fill="{t["fg"]}" font-size="19" font-weight="600">{v:.0f}{"*" if hollow else ""}</text>'
        out+=f'<text x="{gx+gw/2}" y="{base+46}" text-anchor="middle" fill="{t["fg"]}" font-size="24" font-weight="600">{cn}</text>'
    out+=f'<text x="800" y="830" text-anchor="middle" fill="{t["mute"]}" font-size="17">g CO2/km, EU grid 250 g/kWh · * outlined: engine short of the trace on some steps</text>'
    return out
def single(t,ck):
    base,top=740,280; vals=[CO2[k][ck] for k,_,_ in CARS]; mx=max(vals); bw,gap=200,90; x0=800-(4*bw+3*gap)/2; out=""
    for i,((k,n,c),v) in enumerate(zip(CARS,vals)):
        h=(base-top)*v/mx; x=x0+i*(bw+gap); hollow=SHORT[k][ck]>0
        fill=f'fill="{c}"' if not hollow else f'fill="none" stroke="{c}" stroke-width="4"'
        out+=f'<path d="M{x},{base} V{base-h+5} q0,-5 5,-5 H{x+bw-5} q5,0 5,5 V{base} Z" {fill}/>'
        out+=f'<text x="{x+bw/2}" y="{base-h-22}" text-anchor="middle" fill="{t["fg"]}" font-size="44" font-weight="700" letter-spacing="-1">{v:.1f}{"*" if hollow else ""}</text>'
        out+=f'<text x="{x+bw/2}" y="{base+46}" text-anchor="middle" fill="{t["mute"]}" font-size="24" font-weight="500">{n}</text>'
    out+=f'<text x="800" y="830" text-anchor="middle" fill="{t["mute"]}" font-size="17">g CO2/km, EU grid 250 g/kWh{" · * outlined: engine short of the trace on some steps" if any(SHORT[k][ck] for k,_,_ in CARS) else ""}</text>'
    return out
def chain(t):
    steps=[("Speed trace","v(t) or v(s)"),("Forces","rolling, aero, grade, inertia"),("Wheel power","F · v"),
           ("Engine / motor","÷ transmission η, capability"),("Energy","engine η(P), heating value"),("CO2","fuel + grid, g/km")]
    w,h,g=210,250,40; x0=800-(6*w+5*g)/2; y=330; out=""
    for i,(a,s) in enumerate(steps):
        x=x0+i*(w+g); last=i==5
        out+=f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="22" fill="{t["fg"] if last else t["soft"]}"/>'
        fc=t["bg"] if last else t["fg"]
        out+=f'<text x="{x+w/2}" y="{y+70}" text-anchor="middle" fill="{t["mute"]}" font-size="20" font-weight="600">{i+1}</text>'
        out+=f'<text x="{x+w/2}" y="{y+130}" text-anchor="middle" fill="{fc}" font-size="27" font-weight="700">{a}</text>'
        ws=s.split(", ") if ", " in s else [s]
        for j,l in enumerate(ws if len(ws)<3 else [", ".join(ws[:2]),", ".join(ws[2:])]):
            out+=f'<text x="{x+w/2}" y="{y+175+j*24}" text-anchor="middle" fill="{t["mute"]}" font-size="17">{l}</text>'
        if i<5: out+=f'<path d="M{x+w+8},{y+h/2} l{g-16},0 m-8,-8 l8,8 l-8,8" stroke="{t["mute"]}" stroke-width="2.5" fill="none"/>'
    return out
def carscycles(t):
    out=""; w,g=330,40; x0=800-(4*w+3*g)/2
    for i,(k,n) in enumerate(CYC):
        x=x0+i*(w+g); y=230
        out+=f'<rect x="{x}" y="{y}" width="{w}" height="270" rx="22" fill="{t["soft"]}"/>'
        c=D[k]; xs=c["x"]; vs=c["v"]; X=xs[-1]; step=max(1,len(xs)//300)
        pts=" ".join(f'{x+25+(w-50)*a/X:.1f},{y+180-140*v/150:.1f}' for a,v in list(zip(xs,vs))[::step])
        out+=f'<polyline points="{pts}" fill="none" stroke="{t["fg"]}" stroke-width="2.5" stroke-linejoin="round"/>'
        out+=f'<text x="{x+25}" y="{y+225}" fill="{t["fg"]}" font-size="26" font-weight="700">{n}</text>'
        out+=f'<text x="{x+25}" y="{y+255}" fill="{t["mute"]}" font-size="18">{D[k]["km"]:.1f} km</text>'
    for i,(k,n,c) in enumerate(CARS):
        x=x0+i*(w+g); y=570
        out+=f'<circle cx="{x+40}" cy="{y+40}" r="16" fill="{c}"/><text x="{x+70}" y="{y+50}" fill="{t["fg"]}" font-size="26" font-weight="700">{n}</text>'
        out+=yours(t,x+70,y+84,"key specs",18)
    return out
def tiles(t,n=4):
    w,g=330,40; x0=800-(n*w+(n-1)*g)/2; out=""
    for i in range(n):
        x=x0+i*(w+g); y=280
        out+=f'<rect x="{x}" y="{y}" width="{w}" height="400" rx="26" fill="{t["soft"]}"/>'
        out+=yours(t,x+w/2,y+190,"number",64,"middle")+yours(t,x+w/2,y+270,"one line",22,"middle")
    return out
def rows(t):
    out=f'<text x="230" y="270" fill="{t["mute"]}" font-size="19" font-weight="600">LIMIT</text><text x="900" y="270" fill="{t["mute"]}" font-size="19" font-weight="600">NEXT STEP</text>'
    for i in range(3):
        y=320+i*150
        out+=f'<line x1="230" x2="1370" y1="{y}" y2="{y}" stroke="{t["line"]}" stroke-width="2"/>'
        out+=yours(t,230,y+62,"limit",32)+yours(t,230,y+100,"why it matters",21)
        out+=f'<path d="M760,{y+62} l60,0 m-10,-10 l10,10 l-10,10" stroke="{t["mute"]}" stroke-width="2.5" fill="none"/>'
        out+=yours(t,900,y+72,"next step",30)
    return out
def study_slot(t,owner_hint):
    out=f'<rect x="250" y="240" width="1100" height="520" rx="26" fill="none" stroke="{t["line"]}" stroke-width="3" stroke-dasharray="14 12"/>'
    out+=yours(t,800,490,"chart or figure from the study",30,"middle")+yours(t,800,535,owner_hint,22,"middle")
    return out
def questions(t,op,gid):
    P=screen(0,6990,2.4,1100,450)
    b=contours(t,6990,2.4,1100,450,op)+speedline(P,30)+fadeL(t,gid)
    b+=(f'<text x="110" y="480" fill="{t["fg"]}" font-size="110" font-weight="700" letter-spacing="-4">Questions?</text>'
        + yours(t,110,545,"then, if time allows: the live demo",28))
    return svg(t,b+minimap(t,6990),False)
SECS={"sim":(220,"01","The simulation","La Source",3.2),"cmp":(1010,"02","Four cars compared","Eau Rouge",2.8),
      "A":(2200,"03 · Study A","Hybrid sizing","Les Combes",3.0),"B":(3600,"04 · Study B","Sensitivity","Pouhon",2.6),
      "C":(4740,"05 · Study C","Cornering speed","Stavelot",3.0),"lim":(6540,"06","Limits and next step","Bus Stop",3.4)}
def op_(dark,key,op,gid):
    s,n,ti,c,z=SECS[key]; return opener(dark,s,z,n,ti,c,op,gid)
KEEP=(1400,20,1600,180)   # top-right box the road must stay out of
def placement(s_, zoom):
    # keep the road out of the little-lap box (top right) and the title block (left), keep the corner on screen
    TITLE=(60,300,900,580); best=None
    for fy in range(300,701,25):
        for fx in range(950,1301,25):
            P=screen(0,s_,zoom,fx,fy)
            k=sum(1 for x,y in P if KEEP[0]-30<x<KEEP[2] and KEEP[1]-30<y<KEEP[3]+30)
            ti=sum(1 for x,y in P if TITLE[0]<x<TITLE[2] and TITLE[1]<y<TITLE[3])
            score=k*5+ti*3+abs(fx-1100)/50+abs(fy-450)/50
            if best is None or score<best[0]: best=(score,fx,fy)
    return best[1],best[2]
def opener(dark, s, zoom, num, title, corner, relief, gid):
    t=th(dark); fx,fy=placement(s,zoom); P=screen(0,s,zoom,fx,fy)
    b=contours(t,s,zoom,fx,fy,relief)+speedline(P,30)+fadeL(t,gid)
    b+=(f'<text x="110" y="380" fill="{t["mute"]}" font-size="28" font-weight="600">{num}</text>'
        f'<text x="110" y="480" fill="{t["fg"]}" font-size="96" font-weight="700" letter-spacing="-3.5">{title}</text>'
        f'<text x="110" y="540" fill="{t["mute"]}" font-size="28">{corner} · {s/1000:.1f} km</text>')
    return svg(t,b+minimap(t,s),False)
def questions(t,op,gid):
    fx,fy=placement(6990,2.4); P=screen(0,6990,2.4,fx,fy)
    b=contours(t,6990,2.4,fx,fy,op)+speedline(P,30)+fadeL(t,gid)
    b+=(f'<text x="110" y="480" fill="{t["fg"]}" font-size="110" font-weight="700" letter-spacing="-4">Questions?</text>'
        + yours(t,110,545,"then, if time allows: the live demo",28))
    return svg(t,b+minimap(t,6990),False)
ORDER=["sim","cmp","A","B","C","lim"]
def run(dark,op,tag):
    t=th(dark); sl=[]; P=lambda: str(len(sl)+1)
    plan=[None,("sim",0),("sim",1),("sim",2),("sim",3),("cmp",0),("cmp",1),("cmp",2)]
    for k in ("A","B","C"): plan+=[(k,0),(k,1),(k,2),(k,3)]
    plan+=[("lim",0),("lim",1),("end",0)]
    size={k:sum(1 for q in plan if q and q[0]==k) for k in ORDER}
    def where(n):
        q=plan[n]
        if q is None: return None
        k,j=q
        if k=="end": return 6990
        a=SECS[k][0]; nxt=ORDER.index(k)+1; b=SECS[ORDER[nxt]][0] if nxt<len(ORDER) else 6990
        return a+(b-a)*j/size[k]
    _app=sl.append
    class L(list):
        pass
    def add(item):
        _app(item)
    def before():
        n=len(sl); POS[0]=where(n); LABEL[0]=str(n+1) if n>0 else ''
    import builtins
    before(); sl.append(("Title",t_centre(dark,op*1.1,tag+"t")))
    before(); sl.append(("Opener",op_(dark,"sim",op,tag+"o1")))
    before(); sl.append(("The model",frame(t,"The simulation","Your headline",P(),220,chain(t))))
    before(); sl.append(("Cars and cycles",frame(t,"The simulation","Your headline",P(),220,carscycles(t))))
    before(); sl.append(("What we changed",frame(t,"The simulation","Your headline",P(),220,tiles(t))))
    before(); sl.append(("Opener",op_(dark,"cmp",op,tag+"o2")))
    before(); sl.append(("All 16 results",frame(t,"Four cars on four cycles · g CO2/km","Your headline",P(),1010,grouped(t))))
    before(); sl.append(("Highway focus",frame(t,"WLTC Class 3 · g CO2/km","Your headline",P(),1010,single(t,"wltc"))))
    for key,hint in (("A","Study A owner's slides"),("B","Study B owner's slides"),("C","Study C owner's slides")):
        before(); sl.append(("Opener",op_(dark,key,op,tag+"o"+key)))
        for j in range(3):
            before(); sl.append((f"Study {key} · {j+1}/3",frame(t,SECS[key][2],"Owner's headline",P(),SECS[key][0],study_slot(t,hint))))
    before(); sl.append(("Opener",op_(dark,"lim",op,tag+"o6")))
    before(); sl.append(("Limits → next step",frame(t,"Limits and next step","Your headline",P(),6540,rows(t))))
    before(); sl.append(("Questions",questions(t,op,tag+"q")))
    return sl
def grid(sl):
    return '<div style="display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin:8px 0 20px">'+"".join(
        f'<div><p style="margin:0 0 5px;font-size:13px"><b>{i+1}</b> · {n}</p>{shadow(s)}</div>' for i,(n,s) in enumerate(sl))+'</div>'
dk=run(True,0.14,"d"); lt=run(False,0.20,"l")
o=['<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">',
 '<h2>The whole deck, in order</h2>',
 f'<p class="subtitle">{len(dk)} slides. Grey italic text marks where your words go; nothing is written for you. Charts and track use real model numbers (storage-loss baseline, assignment vehicles, EU grid). Study slots are empty frames for their owners. Each content slide carries a tiny lap in the footer showing where we are.</p>',
 '<h3>Dark</h3>', grid(dk), '<h3>Light</h3>', grid(lt),
 '<h3>Full size (dark)</h3>']
for i in (16,6,22):
    o.append(f'<div style="margin:10px 0 18px">{shadow(dk[i][1])}</div>')
open(sys.argv[4],"w").write(chr(10).join(o))
