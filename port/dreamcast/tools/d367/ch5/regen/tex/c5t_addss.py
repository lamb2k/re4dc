# addss.py <pak in> <pak out> <work> <tex dir>...: add the prepared sub-screen pictures (chap05..07) to the pak; padded
# 16-bit images >= 32 KiB with both sides >= 64 become VQ (vq_native_ui's UI rule; chap01..04 ship that way).
import sys,pathlib,json,hashlib
T='/root/probe/lanes-20261018/ch5regen/game-249effe5/port/dreamcast/tools'
sys.path.insert(0,T); sys.path.insert(0,T+'/d367'); sys.path.insert(0,T+'/d367/vram')
import vq_native_ui as vq, texpack, vq_pak
src,dst,work=sys.argv[1],sys.argv[2],pathlib.Path(sys.argv[3])
pkgs=vq_pak.read_pak(open(src,'rb').read())
outd=work/'ss-vq'; prev=work/'ss-prev'; outd.mkdir(parents=True,exist_ok=True); prev.mkdir(exist_ok=True)
rep=[]
for d in sys.argv[4:]:
    for f in sorted(pathlib.Path(d).glob('*.re4tex')):
        key=f.stem; k=tuple(int(x,16) for x in key.split('-')); blob=f.read_bytes(); kind='raw'
        if k in pkgs: rep.append((key,'already')); continue
        try:
            w,h,fmt,flags,_=vq.read_package(blob)
            if w*h*2>=32768 and w>=64 and h>=64:
                e=vq.encode(key,f.parent,outd,vq.PVRTEX,(w,h),prev)
                blob,rule=vq_pak.restamp(blob,(outd/(key+'.re4tex')).read_bytes()); kind='vq %.1f dB'%e['psnr_db']
        except ValueError: pass
        pkgs[k]=blob; rep.append((key,kind))
out,_=texpack.build(pkgs); texpack.verify(out); open(dst,'wb').write(out)
for r in rep: print(*r)
print('pak',dst,hashlib.sha256(out).hexdigest(),len(pkgs))
