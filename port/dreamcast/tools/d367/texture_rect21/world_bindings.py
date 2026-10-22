#!/usr/bin/env python3
"""Recover exact existing native world bindings; no texture/UV/runtime mutation."""
from pathlib import Path
import argparse,hashlib,json,struct,sys,zlib
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from fullplay import fp_iso

def sha(b):return hashlib.sha256(b).hexdigest()
def inspect_sidecar(blob):
    if len(blob)<32:raise ValueError('truncated world header')
    magic,version,placements,parts,meshes,crc,r0,r1=struct.unpack_from('<4s7I',blob)
    if magic!=b'R4PW' or version!=1 or len(blob)!=32+16*parts+52*placements:raise ValueError('unsupported world extent')
    if zlib.crc32(blob[32:])&0xffffffff!=crc:raise ValueError('world body checksum mismatch')
    return [dict(key='%08x-%08x'%(a,b),width=w,height=h,render_pass=p,cull=c,texture=t,flags=f,part=i)
            for i,(a,b,w,h,p,c,t,f) in enumerate(struct.iter_unpack('<IIHH4B',blob[32:32+16*parts]))]

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    for name in ['track','world-receipt','queue','out']:ap.add_argument('--'+name,type=Path,required=True)
    a=ap.parse_args();assert not a.out.exists(),'Preserve existing output'
    world_blob=a.world_receipt.read_bytes();queue_blob=a.queue.read_bytes()
    world=json.loads(world_blob);queue=json.loads(queue_blob)
    assert world['source_pack_sha256']==queue['source_pack_sha256']
    q={r['key']:r for r in queue['rows']};assert len(q)==792
    tr=fp_iso.Track(a.track,45000);files={p.lstrip('/').lower():(e,n) for p,e,n in fp_iso.files(tr)}
    matched=[];held=[];bindings={k:[] for k in q};saved=[]
    for item in world['world_inputs']:
        path=item['path'];found=files.get(path.lower())
        if found is None:held.append(dict(path=path,reason='absent'));continue
        e,n=found;blob=tr.read_bytes(e,n)
        if n!=item['size'] or sha(blob)!=item['sha256']:
            held.append(dict(path=path,reason='different retained input',actual_sha256=sha(blob)));continue
        rows=inspect_sidecar(blob);matched.append(dict(path=path,sha256=sha(blob),parts=len(rows)))
        saved.append((path,blob))
        for r in rows:
            if r['key'] not in q:continue
            original=q[r['key']]
            if (r['width'],r['height'])!=(original['width'],original['height']):raise ValueError('native size disagrees: '+r['key'])
            bindings[r['key']].append(dict(world=path,**r))
    a.out.mkdir(parents=True)
    for path,blob in saved:
        p=a.out/'inputs'/path;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(blob)
    result=dict(schema='re4dc-rectangular-native-world-bindings-1',world_receipt_sha256=sha(world_blob),queue_sha256=sha(queue_blob),source_pack_sha256=world['source_pack_sha256'],world_inputs=len(world['world_inputs']),matched_worlds=matched,held_worlds=held,rectangular_keys=792,keys_with_exact_native_bindings=sum(bool(v) for v in bindings.values()),binding_rows=sum(map(len,bindings.values())),bindings=bindings,limits=['R4PW proves texture identity, logical dimensions and material-part binding, not original TPL wrap flags.','Current native packet explicitly uses repeat UV sampling; its dimension rejection and per-vertex transform require coordinated opt-in adaptation.','No converted texture, changed UV, runtime test, memory or performance acceptance.'])
    (a.out/'bindings.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:result[k] for k in ['world_inputs','rectangular_keys','keys_with_exact_native_bindings','binding_rows','held_worlds']}))
if __name__=='__main__':main()