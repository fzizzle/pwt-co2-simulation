import re,sys
h=open(sys.argv[1]).read()
svgs=re.findall(r'<svg viewBox="0 0 1600 900".*?</svg>',h,flags=re.S)[:23]
out=['<div style="display:grid;grid-template-columns:repeat(8,1fr);gap:6px;background:#888;padding:6px">']
for s in svgs[1:]:
    out.append(s.replace('viewBox="0 0 1600 900"','viewBox="1380 20 200 160"',1))
out.append('</div>')
open(sys.argv[2],"w").write("<html><body style='margin:0'>"+"".join(out)+"</body></html>")
