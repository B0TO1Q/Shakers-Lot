import math, asyncio, sys
from playwright.async_api import async_playwright

# ---- zones copied from the live lot map (front of building + east side) ----
ZONES = [
 dict(id="Z11",n=6, x=1356,y=752,w=164,h=76, lbl="at", at=(1438,767), name="SIDEWALK", cells=[
   [1356+k*164/6,776,164/6,50,0] for k in range(6)]),
 dict(id="Z10",n=3, x=1268,y=858,w=82, h=46, lbl="below", name="FRONT PAD"),
 dict(id="Z9", n=2, x=1283,y=994,w=76, h=46, lbl="below", name="FORD SIGN", cells=[
   [1284,995,22,44,0],[1308,995,22,44,0]]),
 dict(id="Z1", n=15,x=1362,y=962,w=380,h=54, lbl="top", name="ZONE 1"),
 dict(id="Z12",n=2, x=1806,y=1006,w=104,h=86, lbl="left", name="LINCOLN SIGN", cells=[
   [1830,1008,54,26,0],[1830,1064,54,26,0]]),
 dict(id="Z7", n=16,dir="v",x=1846,y=612,w=64,h=388, lbl="top", name="Z7"),
 dict(id="Z2", n=7, x=1596,y=822,w=180,h=50, lbl="left", name="Z2"),
 dict(id="Z3", n=7, x=1596,y=772,w=180,h=50, lbl="left", name="Z3"),
 dict(id="Z4", n=7, x=1596,y=652,w=180,h=50, lbl="left", name="Z4"),
 dict(id="Z5", n=7, x=1596,y=602,w=180,h=50, lbl="left", name="Z5"),
 dict(id="Z6", n=8, x=1586,y=486,w=218,h=50, lbl="below", name="Z6"),
]
CAT={"Z11":"FORD","Z10":"LINCOLN","Z1":"TRUCKS","Z2":"EXPLORER · BRONCO","Z3":"JEEP","Z4":"LINCOLN · BMW","Z5":"SMALL FORDS","Z7":"OTHER MAKES"}
def geom(z,k):
    if "cells" in z:
        c=z["cells"][k]; return dict(x=c[0],y=c[1],w=c[2],h=c[3],rot=c[4],num=c[5] if len(c)>5 else k+1)
    if z.get("dir")=="v":
        h=z["h"]/z["n"]; return dict(x=z["x"],y=z["y"]+k*h,w=z["w"],h=h,rot=0,num=k+1)
    w=z["w"]/z["n"]; return dict(x=z["x"]+k*w,y=z["y"],w=w,h=z["h"],rot=0,num=k+1)

VB=(955,440,980,700)   # overview area (map units)
# Zoomed write-in pages: (letter, title, region x y w h, orientation, label overrides)
SECTIONS=[
 ("A","Front line","Sidewalk · Front Pad · Ford Sign · Zone 1",(1255,745,500,320),"land",{}),
 ("B","East lot rows","Z6 · Z5 · Z4 · Z3 · Z2",(1515,448,300,440),"port",{}),
 ("C","East line & Lincoln sign","Z7 other makes · Lincoln Sign",(1770,585,165,530),"port",{"Z12":"below"}),
]
SEC_ZONES={"A":["Z9","Z10","Z11","Z1"],"B":["Z6","Z5","Z4","Z3","Z2"],"C":["Z7","Z12"]}
MAP_AREA={"land":(10.3,6.25),"port":(7.8,8.75)}
def page_scale(vb,orient):
    W,H=MAP_AREA[orient]; return min(W/vb[2],H/vb[3])
OV_SCALE=min(10.3/VB[2],6.25/VB[3])


INK="#111111"; GRAY="#b0b0b0"; MID="#555555"
def fit_box(vb,orient):
    W,H=MAP_AREA[orient]; x,y,w,h=vb; ar=W/H
    if w/h<ar: nw=h*ar; return (x-(nw-w)/2,y,nw,h)
    nh=w/ar; return (x,y-(nh-h)/2,w,nh)

def svg_map(vb=VB, t=1.0, labels=None, big=False, only=None, arrow="tl", extra="", nums=True):
    """Line-only plan: black outlines for inventory spots, light gray for everything else. t scales text."""
    labels=labels or {}
    o=[]; A=o.append; x0,y0,W,H=vb; fs=lambda v:f"{v*t:.2f}"
    G=f'fill="none" stroke="{GRAY}" stroke-width="1.3"'
    A(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{x0} {y0} {W} {H}" preserveAspectRatio="xMidYMid meet">')
    A(f'<clipPath id="c"><rect x="{x0}" y="{y0}" width="{W}" height="{H}"/></clipPath><g clip-path="url(#c)">')
    A(f'<style>.zs{{font-size:{fs(8.5)}px}} .zl{{font-size:{fs(12)}px}} .n{{font-size:{fs(6.5)}px}} .lm{{font-size:{fs(7)}px}} .sp{{stroke-width:{1.5 if big else 1.1}}}</style>')
    # context, all light gray lines
    A(f'<line x1="1530" y1="476" x2="1906" y2="476" stroke="{GRAY}" stroke-width="3"/>')
    A('<text x="1720" y="466" class="lm">RETAINING WALL · WOODS</text>')
    A(f'<path d="M1906 476 L1922 600 V1100" {G} stroke-dasharray="6 5"/>')
    A(f'<line x1="0" y1="1100" x2="1946" y2="1100" stroke="{GRAY}" stroke-width="1.5"/>')
    A(f'<line x1="0" y1="1130" x2="1946" y2="1130" stroke="{GRAY}" stroke-width="1.5" stroke-dasharray="22 18"/>')
    A('<text x="1440" y="1121" class="lm" style="letter-spacing:.2em">ROUTE 63 · STRAITS TURNPIKE</text>')
    A(f'<path d="M1350 742 H1526 V832 H1356 L1356 920 Q1356 926 1350 926 H1268 Q1262 926 1262 920 V832 H1350 Z" {G}/>')
    A(f'<rect x="1793" y="1004" width="130" height="90" rx="14" {G}/>')
    A(f'<rect x="1281" y="990" width="80" height="54" rx="9" {G}/>')
    A(f'<ellipse cx="1346" cy="1017" rx="5.5" ry="12" fill="none" stroke="{MID}" stroke-width="1"/>')
    A(f'<rect x="1836" y="1040" width="42" height="14" rx="1.5" fill="none" stroke="{MID}" stroke-width="1"/><text x="1857" y="1050" class="lm" style="font-size:{fs(5.5)}px;fill:{MID}">LINCOLN</text>')
    A(f'<rect x="1528" y="496" width="50" height="30" rx="3" {G}/><text x="1553" y="514" class="lm" style="font-size:{fs(6)}px">DUMPSTER</text>')
    # customer stalls at the main entrance: ADA 2 west + 1 east, hatched walk (2 stalls) to the doors, no stall at the east end
    for i in range(10): A(f'<line x1="{964+i*29.6:.1f}" y1="856" x2="{964+i*29.6:.1f}" y2="912" stroke="{GRAY}" stroke-width="1"/>')
    for i in (4,5):
      x=964+i*29.6; A(f'<clipPath id="h{i}"><rect x="{x+2:.1f}" y="858" width="25.6" height="52"/></clipPath><g clip-path="url(#h{i})">'
        +"".join(f'<line x1="{x+2+k*7:.1f}" y1="910" x2="{x+2+k*7+20:.1f}" y2="858" stroke="{GRAY}" stroke-width="1"/>' for k in range(-3,5))+'</g>')
    for i in (2,3,6): A(f'<text x="{964+i*29.6+14.8:.1f}" y="888" class="lm" style="font-size:{fs(6)}px">ADA</text>')
    A(f'<text x="{964+5*29.6:.1f}" y="850" class="lm" style="font-size:{fs(5.5)}px">MAIN ENTRANCE</text>')
    A('<text x="1110" y="930" class="lm">CUSTOMER PARKING</text>')
    for i in range(7): A(f'<line x1="{1356+i*164/6:.1f}" y1="838" x2="{1356+i*164/6:.1f}" y2="884" stroke="{GRAY}" stroke-width="1"/>')
    for i in range(11): A(f'<line x1="{1010+i*27}" y1="962" x2="{1010+i*27}" y2="1016" stroke="{GRAY}" stroke-width="1"/>')
    # inventory spots
    # what parks here: big light-gray words right across each row (stock numbers write over them)
    for z in ZONES:
        if (only and z["id"] not in only) or z["id"] not in CAT: continue
        gs=[geom(z,k) for k in range(z["n"])]
        x0_=min(g["x"] for g in gs); y0_=min(g["y"] for g in gs); x1_=max(g["x"]+g["w"] for g in gs); y1_=max(g["y"]+g["h"] for g in gs)
        vert=(y1_-y0_)>(x1_-x0_)*1.6; Ln=(y1_-y0_) if vert else (x1_-x0_); Th=(x1_-x0_) if vert else (y1_-y0_); cx=(x0_+x1_)/2; cy=(y0_+y1_)/2
        fit=lambda ls:min(Th*(0.4 if len(ls)>1 else 0.6),(Ln-8)/(max(len(l) for l in ls)*0.66))
        one=[CAT[z["id"]]]; two=CAT[z["id"]].split(" · "); ls=two if len(two)>1 and fit(two)>fit(one) else one; f=fit(ls)
        tr=f' transform="rotate(-90 {cx:.1f} {cy:.1f})"' if vert else ""
        A(f'<text class="zbig" text-anchor="middle" style="font-size:{f:.1f}px"{tr}>'+"".join(f'<tspan x="{cx:.1f}" y="{cy+f*0.36+(i-(len(ls)-1)/2)*f*1.02:.1f}">{l}</tspan>' for i,l in enumerate(ls))+'</text>')
    for z in ZONES:
        if only and z["id"] not in only: continue
        for k in range(z["n"]):
            g=geom(z,k)
            A(f'<rect x="{g["x"]+1.2:.1f}" y="{g["y"]+1.2:.1f}" width="{g["w"]-2.4:.1f}" height="{g["h"]-2.4:.1f}" rx="1.5" class="sp"/>'
              +(f'<text x="{g["x"]+3:.1f}" y="{g["y"]+2+6.5*t:.1f}" class="n">{g["num"]}</text>' if nums else ""))
        nm=z["name"]; Gp=12; pos=labels.get(z["id"],z["lbl"]); c=None; d=0
        def lab(x,y,anchor="middle"):
            A(f'<text x="{x}" y="{y}" class="zl" text-anchor="{anchor}">{nm}</text>')
            if c: A(f'<text x="{x}" y="{y+d}" class="zs" text-anchor="{anchor}">{c}</text>')
        if pos=="top":     lab(z["x"]+z["w"]/2, z["y"]-Gp+2-d)
        elif pos=="below": lab(z["x"]+z["w"]/2, z["y"]+z["h"]+Gp+8*t)
        elif pos=="left":  lab(z["x"]-(22 if z["id"]=="Z12" else Gp), z["y"]+z["h"]/2+4*t-d/2, "end")
        elif pos=="at":    lab(z["at"][0], z["at"][1]-d/2)
    ax=x0+16*t+10 if arrow in("tl","bl") else x0+W-16*t-10
    ay=y0+24*t+8 if arrow in("tl","tr") else y0+H-26*t-10
    A(f'<g transform="translate({ax:.1f} {ay:.1f})"><path d="M0 {-16*t:.1f} L{6*t:.1f} {6*t:.1f} L0 {2*t:.1f} L{-6*t:.1f} {6*t:.1f} Z" fill="none" stroke="{INK}" stroke-width="1.2" stroke-linejoin="round"/>'
      f'<text x="0" y="{19*t:.1f}" class="zl" style="font-size:{fs(9)}px">N</text></g>')
    A(extra)
    A('</g></svg>')
    return "".join(o)

PLOW_STEPS=[
 ("Open the entrances","West exit by the Side Pad and the east entrance by the Lincoln Sign. Stop short of the road, angle the V and roll the snow onto the grass beside the curb cut."),
 ("Customer stalls &amp; pad aprons","Push straight out into the front aisle before anyone parks."),
 ("West side aisle","Start below the dumpster and push south into the front aisle."),
 ("Front aisle, west half","From the service door east, then turn through the empty customer stalls onto the front grass. Pile B. Keep it low."),
 ("Front aisle, east half","From the Front Pad east past Zone 1, then turn up the east aisle (in front of Z7) to the back corner. Pile A."),
 ("Z3 / Z4 aisle","West to east, then up the east aisle to Pile A."),
 ("Z5 / Z6 aisle","West to east into Pile A."),
 ("Hand finish","Shovel or blow the main doors, side entrance, service door, Sidewalk pad and around the signs. A V plow can't back-drag."),
]
def plow_overlay(t):
    R="#111111"; o=[]; A=o.append
    A(f'<defs><pattern id="ph" width="7" height="7" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><line x1="0" y1="0" x2="0" y2="7" stroke="{R}" stroke-width="1" opacity=".35"/></pattern>'
      f'<marker id="ah" viewBox="0 0 10 10" refX="7" refY="5" markerWidth="3.2" markerHeight="3.2" orient="auto"><path d="M0 0 L10 5 L0 10 Z" fill="{R}"/></marker></defs>')
    rt=lambda d,w=2.6:A(f'<path d="{d}" fill="none" stroke="{R}" stroke-width="{w}" stroke-linecap="round" stroke-linejoin="round" marker-end="url(#ah)"/>')
    def num(n,x,y): A(f'<circle cx="{x}" cy="{y}" r="{9*t}" fill="#fff" stroke="{R}" stroke-width="1.6"/><text x="{x}" y="{y+3.6*t}" style="font:800 {10*t}px Archivo,Arial;fill:{R}" text-anchor="middle">{n}</text>')
    def pile(x,y,w,h,lab): A(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="8" fill="url(#ph)" stroke="{R}" stroke-width="1.2" stroke-dasharray="5 4"/><text x="{x+w/2}" y="{y+h/2+4*t}" class="zl" style="font-size:{10*t}px">{lab}</text>')
    A('<path d="M858 432 H1515 V742 H1350 V826 H858 Z" fill="none" stroke="#b0b0b0" stroke-width="1.5"/>')
    A(f'<text x="1186" y="640" class="lm" style="font-size:{11*t}px;letter-spacing:.3em">BUILDING</text>')
    A(f'<text x="1156" y="818" class="lm" style="font-size:{6*t}px">MAIN DOORS</text><text x="897" y="818" class="lm" style="font-size:{6*t}px">SERVICE DOOR</text>')
    pile(1812,488,90,104,"PILE A"); pile(958,1024,200,68,"PILE B")
    rt("M912 996 V1050 Q912 1066 928 1066 H954",1.8); rt("M1772 1012 V1046 Q1772 1062 1756 1062 H1740",1.8)
    num(1,896,1000); num(1,1756,1004)
    for x in (1000,1090,1180,1240,1390,1470): rt(f"M{x} {868 if x<1300 else 846} V{926 if x<1300 else 928}",1.8)
    num(2,1046,862)
    rt("M1530 548 V926"); num(3,1530,530)
    rt("M944 937 H1140 Q1160 937 1160 958 V1026"); num(4,944,918)
    rt("M1190 940 H1790 Q1811 940 1811 918 V604"); num(5,1206,958)
    rt("M1530 737 H1798"); num(6,1512,737)
    rt("M1530 569 H1808"); num(7,1512,569)
    A(f'<text x="1300" y="1092" style="font:800 {8.5*t}px Archivo,Arial;fill:{R};letter-spacing:.1em" text-anchor="middle">NO SNOW INTO ROUTE 63</text>')
    return "".join(o)

FONTS="".join(f"@font-face{{font-family:Archivo;font-weight:{w};src:url('file:///home/claude/print/fonts/archivo-latin-{w}-normal.woff2') format('woff2')}}" for w in (500,600,700,800))
CSS = FONTS+"""
@page{size:11in 8.5in;margin:0} @page port{size:8.5in 11in;margin:0}
*{box-sizing:border-box}
body{margin:0;font-family:Archivo,Arial,sans-serif;color:#111}
.page{width:11in;height:8.5in;padding:.42in .45in .38in;display:grid;grid-template-rows:auto auto 1fr auto;gap:12px;page-break-after:always;overflow:hidden}
.page:last-child{page-break-after:auto}
.page.port{page:port;width:8.5in;height:11in}
.hd{text-align:center;padding-bottom:9px;border-bottom:2px solid #111}
.hd .org{font-size:11px;font-weight:600;letter-spacing:.16em}
.hd .ttl{font-size:21px;font-weight:800;letter-spacing:.05em;margin-top:3px}
.fields{display:flex;gap:22px;align-items:flex-end}
.fields .f{display:flex;align-items:flex-end;gap:8px;flex:1}
.fields .f.s{flex:0 0 auto}
.fields b{font-size:12px;font-weight:700;white-space:nowrap;letter-spacing:.04em}
.fields b small{font-size:10px;font-weight:500;color:#555;letter-spacing:0}
.fields i{flex:1;height:18px;border-bottom:1px solid #111}
.fields .pg{font-size:12px;font-weight:800;letter-spacing:.08em}
.map{min-height:0;display:flex}
.map svg{width:100%;height:100%}
.ft{display:flex;gap:16px;flex-wrap:wrap;align-items:center;font-size:10px;color:#555;border-top:1px solid #111;padding-top:7px;letter-spacing:.02em}
.ft b{color:#111;font-weight:700;letter-spacing:.04em}
.ft .r{margin-left:auto}
svg .sp{fill:none;stroke:#111}
svg .n{font-family:Archivo,Arial;font-weight:600;fill:#555}
svg .zl{font-family:Archivo,Arial;font-weight:800;fill:#111;text-anchor:middle;letter-spacing:.08em;paint-order:stroke;stroke:#fff;stroke-width:3px;stroke-linejoin:round}
svg .zbig{font-family:Archivo,Arial;font-weight:800;fill:#c2c2c2;letter-spacing:.06em}
svg .zs{font-family:Archivo,Arial;font-weight:700;fill:#333;letter-spacing:.1em;paint-order:stroke;stroke:#fff;stroke-width:3px;stroke-linejoin:round}
svg .lm{font-family:Archivo,Arial;font-weight:600;fill:#8a8a8a;text-anchor:middle;letter-spacing:.1em}
.plowgrid{display:grid;grid-template-columns:minmax(0,1fr) 2.45in;gap:16px;min-height:0}
.plowgrid .map svg{height:auto;align-self:center}
.steps{display:grid;align-content:start;gap:7px;font-size:10px;line-height:1.3}
.steps .st{display:grid;grid-template-columns:20px 1fr;gap:8px;padding-bottom:7px;border-bottom:1px solid #b0b0b0}
.steps .st i{width:20px;height:20px;border:1.5px solid #111;border-radius:50%;font:800 10.5px/17px Archivo;text-align:center;font-style:normal}
.steps .st b{display:block;font-size:11px;letter-spacing:.04em;text-transform:uppercase}
.steps .warn{font-weight:800;font-size:11px;letter-spacing:.04em;border:1.5px solid #111;padding:7px 9px;text-align:center}
/* check sheet */
.cols{display:grid;grid-template-columns:1fr 1fr;gap:22px;min-height:0;align-content:start}
table{width:100%;border-collapse:collapse;font-size:10px;table-layout:fixed}
th{font-size:8.5px;font-weight:700;text-align:left;letter-spacing:.08em;padding:2px 4px;border-bottom:1px solid #111}
td{border-bottom:1px solid #b0b0b0;height:.2in;padding:0 4px;vertical-align:bottom}
td.sp{font-weight:700;white-space:nowrap}
td.ck{border-left:1px solid #b0b0b0}
tr.zh td{border-bottom:1px solid #111;height:22px;font-weight:800;font-size:10.5px;letter-spacing:.08em;padding-top:7px}
tr.zh td span{font-weight:500;color:#555;font-size:9px;letter-spacing:0;margin-left:7px}
"""
ORDER=["Z11","Z10","Z9","Z1","Z12","Z7","Z2","Z3","Z4","Z5","Z6"]
AREA={"Z11":"display pad, each lined up with the stall in front","Z10":"canopy wedge by the main doors",
"Z9":"gravel island, both left of the pole","Z1":"front row, east of the Ford sign","Z12":"1 behind the sign, 2 in front of it",
 "Z7":"along the east edge, 1 = north","Z2":"east lot","Z3":"east lot","Z4":"east lot","Z5":"east lot","Z6":"along the retaining wall"}


def header(title,sub=""):
    return f'<div class="hd"><div class="org">SHAKER FAMILY FORD LINCOLN</div><div class="ttl">{title}</div></div>'
def fields(page=None,sub=""):
    pg=f'<span class="f s"><b>PAGE</b><span class="pg">{page}</span></span>' if page else ""
    return (f'<div class="fields"><span class="f"><b>DATE</b><i></i></span><span class="f"><b>CHECKED BY</b><i></i></span>'
            f'<span class="f s"><b>{sub}</b></span>{pg}</div>')
def rows():
    out=[]
    for zid in ORDER:
        z=next(q for q in ZONES if q["id"]==zid)
        out.append(("zone",z))
        nums=sorted(geom(z,k)["num"] for k in range(z["n"]))
        for n in nums: out.append(("spot",z,n))
    return out

def sheet_pages(per_col):
    rs=rows(); pages=[]; i=0
    while i<len(rs):
        cols=[]
        for c in range(2):
            col=rs[i:i+per_col]
            # don't leave a zone header alone at the bottom of a column
            if col and col[-1][0]=="zone" and i+per_col<len(rs): col=col[:-1]
            i+=len(col)
            if col and col[0][0]=="spot": col=[("cont",col[0][1])]+col
            cols.append(col)
        pages.append(cols)
    return pages

def table(col):
    h=['<table><colgroup><col style="width:13%"><col style="width:18%"><col style="width:33%"><col style="width:20%"><col style="width:8%"><col style="width:8%"></colgroup>',
       '<tr><th>SPOT</th><th>STOCK #</th><th>YEAR / MODEL</th><th>COLOR</th><th>KEYS</th><th>✓</th></tr>']
    for r in col:
        if r[0]=="cont":
            h.append(f'<tr class="zh"><td colspan="6">{r[1]["name"]}<span>continued</span></td></tr>')
        elif r[0]=="zone":
            z=r[1]; h.append(f'<tr class="zh"><td colspan="6">{z["name"]}<span>{(CAT[z["id"]].title().replace("Bmw","BMW")+" · ") if z["id"] in CAT else ""}{z["n"]} spots · {AREA[z["id"]]}</span></td></tr>')
        else:
            z,n=r[1],r[2]; h.append(f'<tr><td class="sp">{z["id"]}-{n:02d}</td><td></td><td></td><td></td><td class="ck"></td><td class="ck"></td></tr>')
    h.append('</table>'); return "".join(h)


def doc(kind):
    h=[f'<!doctype html><html><head><meta charset="utf-8"><style>{CSS}</style></head><body>']
    total=sum(z["n"] for z in ZONES)
    marks='<b>MARK</b> ✓ on lot &nbsp;·&nbsp; S sold &nbsp;·&nbsp; SV service &nbsp;·&nbsp; K keys missing &nbsp;·&nbsp; — empty'
    if kind=="map":
        guide=" &nbsp;·&nbsp; ".join(f"<b>{L}</b> {sub}" for L,_,sub,*_ in SECTIONS)
        h.append(f'<section class="page">{header("MAIN LOT — FRONT &amp; EAST SIDE")}{fields("OVERVIEW")}'
                 f'<div class="map">{svg_map()}</div><div class="ft"><span>Zoomed pages: {guide}</span><span class="r">{total} SPOTS</span></div></section>')
        for L,title,sub,vb,orient,lab in SECTIONS:
            vb=fit_box(vb,orient); sc=page_scale(vb,orient); t=min(2.0,(OV_SCALE/sc)*1.5)
            n=sum(z["n"] for z in ZONES if z["id"] in SEC_ZONES[L])
            h.append(f'<section class="page {"port" if orient=="port" else ""}">{header(title.upper())}{fields(L,"")}'
                     f'<div class="map">{svg_map(vb,t,lab,big=True,only=set(SEC_ZONES[L]),arrow={"A":"tl","B":"br","C":"tl"}[L])}</div>'
                     f'<div class="ft"><span><b>WRITE THE STOCK #</b> in each spot</span><span>{marks}</span><span class="r">{n} SPOTS</span></div></section>')
    elif kind=="plow":
        vb=(850,440,1080,684); t=1.15
        steps="".join(f'<div class="st"><i>{i+1}</i><div><b>{a}</b>{b}</div></div>' for i,(a,b) in enumerate(PLOW_STEPS))
        h.append(f'<section class="page">{header("PLOW ROUTE — MAIN LOT")}'
                 f'<div class="fields"><span class="f"><b>DATE</b><i></i></span><span class="f"><b>DRIVER</b><i></i></span><span class="f"><b>START</b><i></i></span><span class="f"><b>DONE</b><i></i></span></div>'
                 f'<div class="plowgrid"><div class="map">{svg_map(vb,t,extra=plow_overlay(t),nums=False,labels={"Z7":"top","Z12":"below"})}</div>'
                 f'<div class="steps">{steps}<div class="warn">NEVER PUSH SNOW INTO OR ACROSS ROUTE 63</div></div></div>'
                 f'<div class="ft"><span><b>V-PLOW.</b> Work from the building out. Piles stay off the Zone 1 frontage so the display line is visible from the road.</span><span class="r">PILE A back corner · PILE B front grass</span></div></section>')
    else:
        pages=sheet_pages(30)
        for pi,cols in enumerate(pages):
            h.append(f'<section class="page">{header("MAIN LOT CHECK")}{fields(f"{pi+1} / {len(pages)}","")}'
                     f'<div class="cols">{"".join(table(c) for c in cols)}</div><div class="ft"><span><b>KEYS</b> ✓ in the box, or write who has them</span><span><b>✓</b> tick once you have seen the car</span><span class="r">Walking order: sidewalk → front line → Z7 → east rows</span></div></section>')
    h.append('</body></html>'); return "".join(h)

async def main(outdir):
    async with async_playwright() as p:
        b=await p.chromium.launch(); pg=await b.new_page()
        for kind in ("map","check","plow"):
            html=doc(kind); open(f"{outdir}/{kind}.html","w").write(html)
            await pg.goto("file://"+outdir+"/blank.html"); await pg.set_content(html); await pg.evaluate("document.fonts.ready"); await pg.wait_for_timeout(300)
            await pg.pdf(path=f"{outdir}/{kind}.pdf",print_background=True,prefer_css_page_size=True)
        await b.close()
asyncio.run(main(sys.argv[1]))
