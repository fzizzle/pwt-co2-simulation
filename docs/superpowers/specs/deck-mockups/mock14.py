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

def whole(t, cx, cy, height, op, sw, gid=None, fade=True):
    H=U0[:,1].max(); W=height/H*1.0  # px per unit
    mx=(U0[:,0].max()+U0[:,0].min())/2; my=H/2
    P=[(cx+(x-mx)*W, cy+(y-my)*W) for x,y in U0]
    mid=f"m{gid}"
    trk=" ".join(f"{x:.0f},{y:.0f}" for x,y in P[::3])
    out=(f'<defs><filter id="bl{mid}" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="45"/></filter>'
         f'<mask id="{mid}" maskUnits="userSpaceOnUse" x="0" y="0" width="1600" height="900"><rect width="1600" height="900" fill="black"/>'
         f'<polyline points="{trk}" fill="none" stroke="white" stroke-width="170" stroke-linejoin="round" filter="url(#bl{mid})"/></mask></defs>')
    out+='<g fill="none" stroke="%s" stroke-linejoin="round" mask="url(#%s)">' % (t["fg"],mid)
    for n,(lv,lines) in enumerate(CONT):
        major=n%5==0
        for L in lines:
            Q=[(cx+(x-mx)*W, cy+(y-my)*W) for x,y in L]
            if not any(-200<x<1800 and -200<y<1100 for x,y in Q): continue
            out+='<polyline points="'+" ".join(f"{x:.0f},{y:.0f}" for x,y in Q[::2])+f'" stroke-width="{1.6 if major else 1}" opacity="{op*(1.8 if major else 1):.2f}"/>'
    out+='</g>'+speedline(P,sw)
    x,y=P[0]; out+=f'<rect x="{x-14:.1f}" y="{y-3:.1f}" width="28" height="6" rx="2" fill="{t["fg"]}"/>'
    return out
GROUP="Group of three · PWT Powertrains · ESILV 2026"
def t_zoom(dark,op,gid):
    t=th(dark); P=screen(0,0,2.4,1100,450)
    b=contours(t,0,2.4,1100,450,op)+speedline(P,30)+fadeL(t,gid)
    b+=(f'<text x="110" y="420" fill="{t["fg"]}" font-size="100" font-weight="700" letter-spacing="-4">Four cars.</text>'
        f'<text x="110" y="525" fill="{t["fg"]}" font-size="100" font-weight="700" letter-spacing="-4">Four cycles.</text>'
        f'<text x="110" y="590" fill="{t["mute"]}" font-size="28">Simulating the CO2 of four powertrains</text>'
        f'<text x="110" y="800" fill="{t["mute"]}" font-size="20">{GROUP}</text>')
    return svg(t,b,False)
def t_side(dark,op,gid):
    t=th(dark)
    b=whole(t,1120,450,760,op,16,gid+'w')+fadeL(t,gid)
    b+=(f'<text x="110" y="420" fill="{t["fg"]}" font-size="100" font-weight="700" letter-spacing="-4">Four cars.</text>'
        f'<text x="110" y="525" fill="{t["fg"]}" font-size="100" font-weight="700" letter-spacing="-4">Four cycles.</text>'
        f'<text x="110" y="590" fill="{t["mute"]}" font-size="28">Simulating the CO2 of four powertrains</text>'
        f'<text x="110" y="800" fill="{t["mute"]}" font-size="20">{GROUP}</text>')
    return svg(t,b,False)
def t_centre(dark,op,gid):
    t=th(dark); c=t["bg"]
    b=whole(t,800,330,520,op,12,gid+'w')
    b+=(f'<defs><linearGradient id="{gid}" x1="0" x2="0" y1="1" y2="0"><stop offset="0" stop-color="{c}" stop-opacity="1"/><stop offset="0.2" stop-color="{c}" stop-opacity="0.8"/><stop offset="0.36" stop-color="{c}" stop-opacity="0"/></linearGradient></defs><rect width="1600" height="900" fill="url(#{gid})"/>')
    b+=(f'<text x="800" y="740" text-anchor="middle" fill="{t["fg"]}" font-size="88" font-weight="700" letter-spacing="-3">Four cars. Four cycles.</text>'
        f'<text x="800" y="800" text-anchor="middle" fill="{t["mute"]}" font-size="26">Simulating the CO2 of four powertrains · {GROUP}</text>')
    return svg(t,b,False)
ALL=[(220,"01","The simulation","La Source",3.2),(1010,"02","Four cars compared","Eau Rouge",2.8),
     (2200,"03 · Study A","Hybrid sizing","Les Combes",3.0),(3600,"04 · Study B","Sensitivity","Pouhon",2.6),(4740,"05 · Study C","Cornering speed","Stavelot",3.0),
     (6540,"06","Limits and next step","Bus Stop",3.4),(6990,"","Questions?","Start / finish",2.4)]
def opener(dark, s, zoom, num, title, corner, relief, gid):
    t=th(dark); P=screen(0,s,zoom,1100,450)
    b=contours(t,s,zoom,1100,450,relief)+speedline(P,30)+fadeL(t,gid)
    b+=(f'<text x="110" y="380" fill="{t["mute"]}" font-size="28" font-weight="600">{num}</text>'
        f'<text x="110" y="480" fill="{t["fg"]}" font-size="96" font-weight="700" letter-spacing="-3.5">{title}</text>'
        f'<text x="110" y="540" fill="{t["mute"]}" font-size="28">{corner} · {s/1000:.1f} km</text>')
    return svg(t,b+minimap(t,0,s,110,690,230),False)
DK,LT=0.14,0.20
def deck(dark,op,tag):
    sl=[t_centre(dark,op*1.1,tag+"t")]+[opener(dark,s,z,n,ti,c,op,f"{tag}{i}") for i,(s,n,ti,c,z) in enumerate(ALL)]
    return '<div style="display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin:8px 0 18px">'+"".join(shadow(x) for x in sl)+'</div>'
o=['<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">',
 '<h2>First slide: whole lap above, zoomed out, less hidden</h2>',
 '<p class="subtitle">Relief lighter everywhere. Wording is placeholder.</p>',
 '<div class="split">'+shadow(t_centre(True,DK*1.1,"x1"))+shadow(t_centre(False,LT*1.1,"x2"))+'</div>',
 '<h3 style="margin-top:22px">The whole run of title slides with the lighter relief (dark)</h3>', deck(True,DK,"d"),
 '<h3>Light</h3>', deck(False,LT,"l")]
open(sys.argv[4],"w").write(chr(10).join(o))
