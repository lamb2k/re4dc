# setpak.py <armed.json>... : st3 lane fixture data: dc/tex.pak = the st3 VQ pak (vq33), the rel33 room archive when
# one exists, and the ps2cast merchant (PS2_CAST_MERCHANT=1: ps2lib cast/<room>/merchant-em18 registry, the prepared
# em18.drs ec1c6c16 and its four PS2 pictures, loose) in the merchant rooms.
import json,sys,os,glob,struct
P='/root/probe/lanes-20261014/st3/vq33/tex-st3vq4.pak'
RES='/root/probe/lanes-20261014/st3/resident/resident-st3.bin'   # ROOM_RESIDENT lists (resident_keys.py, e2 runs)
CAST='/mnt/c/Game Dev/Emulators/re4-assets-private/ps2lib/cast'
blob=open(P,'rb').read(); m,v,c,io,do=struct.unpack_from('<8s4I',blob,0)
packed=set('%08x-%08x'%struct.unpack_from('<2I',blob,io+16*i) for i in range(c))
for f in sys.argv[1:]:
    d=json.load(open(f)); r=d['replace']
    r['dc/tex.pak']=P
    if os.path.exists(RES): r['dc/resident.bin']=RES
    room=os.path.basename(f).split('-')[1]; notes=[]
    rel='/root/probe/lanes-20261014/st3/rel33/rel-%s/st3'%room
    if os.path.isdir(rel):
        for e in ('arc','dar'): r['st3/%s.%s'%(room,e)]=rel+'/%s.%s'%(room,e)
        notes.append('rel33')
    reg='%s/%s/merchant-em18/dc/native/%s/registry.re4nmr'%(CAST,room,room)
    if os.path.exists(reg):
        k='dc/native/%s/registry.re4nmr'%room
        if k in r and r[k]!=reg: raise SystemExit('%s: %s already staged (%s)'%(f,k,r[k]))
        r[k]=reg; r['em/em18.drs']=CAST+'/r102/merchant-em18/em/em18.drs'
        for t in glob.glob(CAST+'/r102/merchant-em18/dc/tex/*/*.re4tex'):
            key=os.path.basename(t)[:-7]
            if key in packed: continue   # the pak serves it (vqroom.py VQ)
            r['dc/tex/%s/%s.re4tex'%(key[0],key)]=t
        notes.append('merchant')
    d.setdefault('provenance',{})['st3_vq33']='dc/tex.pak = tex-st3vq.pak (vqroom.py VQ + chap05..07 + material pairs) '+' '.join(notes)
    d['remove']=[x for x in d.get('remove',[]) if x not in r]
    json.dump(d,open(f,'w'),indent=1,sort_keys=True); print(os.path.basename(f),' '.join(notes))
