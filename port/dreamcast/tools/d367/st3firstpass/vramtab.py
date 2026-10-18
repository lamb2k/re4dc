# vramtab.py <scenarios dir> [suffix]: per-room VRAM table (VRAM_ROOM_LOG lines) for REPORT.md
import re,glob,sys,os
H=sys.argv[1]; suf=sys.argv[2] if len(sys.argv)>2 else ''
RL=re.compile(r'^vram room: r=([0-9a-f]+) at=(\S+) f=(\d+) .*?pinned=(\d+) dynamic=(\d+) other=(\d+) free=(\d+) largest=(\d+) min_free=(\d+) min_largest=(\d+) peak_pinned=(\d+) loads=(\d+) evicted=(\d+) retries=(\d+)',re.M)
GL=re.compile(r'^vram gaps: r=([0-9a-f]+) at=(\S+) f=(\d+) refusals=(\d+) guard=(\d+) guard_p=(\d+) nocontig=(\d+) latched=(\d+)',re.M)
print('| room (run) | pinned | dynamic | free | largest free | min free / min largest | uploads after preload | evicted | refusals / guard / no-contig |')
print('|---|---|---|---|---|---|---|---|---|')
for d in sorted(glob.glob(H+'/cx-*'+suf)):
    f=d+'/capture/run-output.txt'
    if not os.path.exists(f): continue
    t=open(f,errors='replace').read(); room=os.path.basename(d).split('-')[1][1:]
    rows=[m for m in RL.finditer(t) if m.group(1)==room]
    if not rows: print('| %s | no vram room line |'%os.path.basename(d)); continue
    last=rows[-1]; pre=[m for m in rows if m.group(2)=='preload']
    after=int(last.group(12))-(int(pre[-1].group(12)) if pre else 0)
    g=[m for m in GL.finditer(t) if m.group(1)==room]; g=g[-1] if g else None
    print('| %s | %s | %s | %s | %s | %s / %s | %d | %s | %s |'%(os.path.basename(d),last.group(4),last.group(5),last.group(7),last.group(8),last.group(9),last.group(10),after,last.group(13),
          '%s / %s / %s'%(g.group(4),g.group(5),g.group(7)) if g else '-'))
