# mkres.py: ROOM_RESIDENT lists for the island rooms from the e2 runs (vram12 resident_keys.py list/pack).
import subprocess,glob,os,re
L='/root/probe/lanes-20261014/st3'; RK=L+'/tree/port/dreamcast/tools/d367/vram/resident_keys.py'
logs=sorted(glob.glob('/mnt/c/Game Dev/Emulators/re4-rfp-20261015-st3e2/scenarios/*/capture/run-output.txt'))
os.makedirs(L+'/resident',exist_ok=True)
rooms=sorted({re.search(r'cx-(r3[0-9a-f]+)-',l).group(1) for l in logs})
made=[]
for r in rooms:
    rl=[l for l in logs if '/cx-%s-'%r in l]
    out=L+'/resident/%s.tsv'%r
    p=subprocess.run(['python3',RK,'list',r[1:],out]+rl,capture_output=True,text=True)
    n=sum(1 for _ in open(out)) if os.path.exists(out) else 0
    print(r,n,p.stdout.strip()[-80:],p.stderr.strip()[-120:])
    if n: made.append(out)
p=subprocess.run(['python3',RK,'pack',L+'/resident/resident-st3.bin']+made,capture_output=True,text=True)
print(p.stdout[-300:],p.stderr[-300:])
