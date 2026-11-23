import sys, json, math
import numpy as np, contourpy
exec(open(sys.argv[3]).read().split("def card(")[0])
src=open(sys.argv[5]).read()
exec(src.split("def fadeL(")[0].split("exec(open")[1].split("\n",1)[1])  # unit, idx, screen, curv, kerbs(old), onscr, speedline, poly
exec("def fadeL("+src.split("def fadeL(")[1].split("def boards(")[0])  # fadeL, minimap
LAP=T["franco_sport_generated"]; Z=np.array(LAP["z"])
# --- interpolated terrain from the lap's altitude (an impression, not survey data)
U0=np.array(unit(0)); sub=U0[::4]; zs=Z[::4]
H=U0[:,1].max()
gx=np.linspace(-0.6,1.6,260); gy=np.linspace(-0.6,H+0.6,int(260*(H+1.2)/2.2))
X,Y=np.meshgrid(gx,gy)
d2=(X[...,None]-sub[:,0])**2+(Y[...,None]-sub[:,1])**2+1e-6
w=1/d2**1.5; F=(w*zs).sum(-1)/w.sum(-1)
for _ in range(12):
    F=(F+np.roll(F,1,0)+np.roll(F,-1,0)+np.roll(F,1,1)+np.roll(F,-1,1))/5
gen=contourpy.contour_generator(X,Y,F)
LEVELS=np.arange(370,476,2)
CONT=[(lv,gen.lines(lv)) for lv in LEVELS]
def contours(t, s_focus, zoom, fx, fy, op, major_every=5):
    W=1600*zoom; ux,uy=U0[idx(s_focus)]
    out=f'<g fill="none" stroke="{t["fg"]}" stroke-linejoin="round">'
    for n,(lv,lines) in enumerate(CONT):
        major = n%major_every==0
        for L in lines:
            P=[(fx+(x-ux)*W, fy+(y-uy)*W) for x,y in L]
            if not any(-200<x<1800 and -200<y<1100 for x,y in P): continue
            out+=f'<polyline points="'+" ".join(f"{x:.0f},{y:.0f}" for x,y in P[::2])+f'" stroke-width="{1.6 if major else 1}" opacity="{op*(1.8 if major else 1):.2f}"/>'
    return out+'</g>'
def mono_kerbs(P, sw, kw, thresh, t, op):
    runs=[]; cur=[]
    for i in range(len(P)):
        k,a,c=curv(P,i)
        if abs(k)>thresh and onscr(P[i]):
            mx,my=(a[0]+c[0])/2-P[i][0],(a[1]+c[1])/2-P[i][1]; n=math.hypot(mx,my) or 1
            off=sw/2+kw/2+3
            cur.append((P[i][0]+mx/n*off,P[i][1]+my/n*off))
        else:
            if len(cur)>2: runs.append(cur)
            cur=[]
    if len(cur)>2: runs.append(cur)
    out=""
    for r in runs:
        pl=" ".join(f"{x:.1f},{y:.1f}" for x,y in r)
        out+=f'<polyline points="{pl}" fill="none" stroke="{t["fg"]}" opacity="{op}" stroke-width="{kw}" stroke-dasharray="{kw*1.2:.1f} {kw*1.2:.1f}"/>'
    return out
def opener(dark, s, zoom, num, title, corner, relief, kerb, gid):
    t=th(dark); sw=30
    P=screen(0,s,zoom,1100,450)
    b=""
    if relief: b+=contours(t,s,zoom,1100,450,relief)
    if kerb: b+=mono_kerbs(P,sw,9,0.0016,t,kerb)
    b+=speedline(P,sw)
    b+=fadeL(t,gid)
    b+=(f'<text x="110" y="380" fill="{t["mute"]}" font-size="28" font-weight="600">{num}</text>'
        f'<text x="110" y="480" fill="{t["fg"]}" font-size="96" font-weight="700" letter-spacing="-3.5">{title}</text>'
        f'<text x="110" y="540" fill="{t["mute"]}" font-size="28">{corner} · {s/1000:.1f} km</text>')
    b+=minimap(t,0,s,110,690,230)
    return svg(t,b,False)
def shadow(s): return f'<div style="box-shadow:0 2px 12px rgba(0,0,0,.18);border-radius:10px;overflow:hidden">{s}</div>'
SEC=[(220,"01","The simulation","La Source",3.2),(1010,"02","Four cars compared","Eau Rouge",2.8),(4740,"05 · Study C","Cornering speed","Stavelot",3.0),(6540,"06","Limits and next step","Bus Stop",3.4)]
COLS=[("Before",0,0),("Mono kerbs",0,0.6),("Light relief + kerbs",0.16,0.6),("Stronger relief + kerbs",0.28,0.6)]
def cell(lbl,s): return f'<div><p style="margin:0 0 6px;font-weight:600">{lbl}</p>{s}</div>'
def grid(i,dark,tag):
    s,num,title,corner,z=SEC[i]
    return '<div style="display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin:8px 0 16px">'+"".join(cell(l,shadow(opener(dark,s,z,num,title,corner,r,k,f"{tag}{i}{j}"))) for j,(l,r,k) in enumerate(COLS))+'</div>'
o=['<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">',
 '<h2>Subtler: monochrome kerbs and topographic relief</h2>',
 '<p class="subtitle">Colourful road kept. Kerbs now a faint dashed line in the text colour. Relief = contour lines every 2 m, every fifth line slightly heavier, interpolated from the lap\'s own altitude (373 to 470 m): an impression of the terrain, not survey data. North up.</p>']
for i,name in enumerate(["La Source","Eau Rouge","Stavelot","Bus Stop"]):
    o+=[f'<h3>{name}</h3>', grid(i,True,f"d{i}"), grid(i,False,f"l{i}")]
o.append('<h3>Full size: in-between relief + mono kerbs</h3><div class="split" style="margin-top:8px">'+shadow(opener(True,*SEC[1][:1],SEC[1][4],*SEC[1][1:4],0.22,0.6,"fz1"))+shadow(opener(False,SEC[2][0],SEC[2][4],*SEC[2][1:4],0.22,0.6,"fz2"))+'</div>')
open(sys.argv[4],"w").write(chr(10).join(o))
