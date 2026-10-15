# setpak.py <armed.json>... : point dc/tex.pak at the st3 VQ pak (vq33) and, for r330, the rel33 room archive.
import json,sys,os
P='/root/probe/lanes-20261014/st3/vq33/tex-st3vq.pak'
for f in sys.argv[1:]:
    d=json.load(open(f)); r=d['replace']
    r['dc/tex.pak']=P
    room=os.path.basename(f).split('-')[1]
    rel='/root/probe/lanes-20261014/st3/rel33/rel-%s/st3'%room
    if os.path.isdir(rel):
        for e in ('arc','dar'): r['st3/%s.%s'%(room,e)]=rel+'/%s.%s'%(room,e)
    d.setdefault('provenance',{})['st3_vq33']='dc/tex.pak = tex-st3vq.pak (vqroom.py: 467 island 16-bit textures as VQ)'+(' + rel33 room archive' if os.path.isdir(rel) else '')
    d['remove']=[x for x in d.get('remove',[]) if x not in r]
    json.dump(d,open(f,'w'),indent=1,sort_keys=True); print(f, 'rel33' if os.path.isdir(rel) else '')
