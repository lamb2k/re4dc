#!/usr/bin/env python3
"""Pinned independent C decoder and separate scalar sampling seal, no NumPy."""
import argparse
import ctypes
import hashlib
import json
from pathlib import Path
import shutil
import struct
import sys
import atlas_split as atlas
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'texture_actors21'))
import actor_candidate


def scalar(pixels,side,u,v):
    import math
    x,y=u*side-.5,v*side-.5;a,b=math.floor(x),math.floor(y);fx,fy=x-a,y-b
    out=[0.,0.,0.,0.]
    for dx,wx in ((0,1-fx),(1,fx)):
        for dy,wy in ((0,1-fy),(1,fy)):
            p=pixels[max(0,min(side-1,b+dy))*side+max(0,min(side-1,a+dx))]
            for c in range(4):out[c]+=p[c]*wx*wy
    return out


def reference(base,side,small):
    scale=side//small;out=[]
    for y in range(small):
        for x in range(small):
            sums=[0.,0.,0.,0.]
            for yy in range(y*scale,(y+1)*scale):
                for xx in range(x*scale,(x+1)*scale):
                    p=base[yy*side+xx]
                    for c in range(4):sums[c]+=p[c]
            out.append([s/(scale*scale) for s in sums])
    return out


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('candidate',type=Path);ap.add_argument('--source-root',type=Path,required=True)
    ap.add_argument('--source-pack',type=Path,required=True);ap.add_argument('--oracle',type=Path,required=True)
    ap.add_argument('--oracle-sha256',required=True);a=ap.parse_args()
    out=a.candidate
    if (out/'independent-seal.json').exists():raise ValueError('preserve existing seal')
    report=json.loads((out/'report.json').read_text())
    pack=a.source_pack.read_bytes()
    if atlas.sha(pack)!=atlas.PACK_SHA or atlas.sha(a.oracle.read_bytes())!=a.oracle_sha256:
        raise ValueError('source pack or independent oracle hash changed')
    entries=actor_candidate.read_pak(pack)
    lib=ctypes.CDLL(str(a.oracle.resolve()));call=lib.mipmap_oracle_decode
    call.argtypes=[ctypes.c_void_p,ctypes.c_size_t,ctypes.c_uint,ctypes.c_uint,ctypes.c_int,ctypes.c_uint,ctypes.c_void_p,ctypes.c_size_t]
    call.restype=ctypes.c_int
    decoded=0
    def decode(native,side):
        nonlocal decoded
        raw=ctypes.create_string_buffer(native.payload);rgba=ctypes.create_string_buffer(side*side*4)
        result=call(raw,len(native.payload),native.texture[3],native.size,native.mipmapped,side.bit_length()-1,rgba,len(rgba))
        expected=bytes(c for p in atlas.mip.decode_level(native,side) for c in p)
        if result!=len(rgba) or rgba.raw!=expected:raise ValueError('independent decoder disagreement')
        decoded+=1
        pixels=rgba.raw
        return [tuple(pixels[i:i+4]) for i in range(0,len(pixels),4)]
    rows=[]
    for row in report['textures']:
        actor=row['actor'];cohort='leon-v1' if actor=='standard' else 'leon-extra-v1'
        folder=out/actor;key=actor_candidate.parse_key(row['source_key'])
        source=(folder/'original-atlas.re4tex').read_bytes()
        if source!=entries[key] or actor_candidate.parse_key(row['derived_key']) in entries:
            raise ValueError('source winner changed or new key collision')
        original=atlas.mip.read_native_vq(source)
        candidate=atlas.mip.read_native_vq((folder/'candidate.re4tex').read_bytes())
        baseline=atlas.mip.read_native_vq((a.source_root/cohort/'replacements'/(row['source_key']+'.re4tex')).read_bytes())
        if candidate.codebook!=original.codebook:raise ValueError('codebook changed')
        old_base=decode(original,512)
        levels={s:decode(candidate,s) for s in (1,2,4,8,16,32,64,128)}
        old_levels={s:decode(baseline,s) for s in (1,2,4,8,16,32,64,128,256,512)}
        x,y,side=row['physical_crop']
        crop=[old_base[(y+yy)*512+x+xx] for yy in range(side) for xx in range(side)]
        if levels[side]!=crop:raise ValueError('independent base crop differs')
        arr=atlas.chunks(actor,a.source_root/cohort/'inputs')
        coordinates=[]
        for run in row['bindings']['runs']:
            if run['texture']!='isolated':continue
            folder_run=folder/'bindings'/f"run-{run['index']:03d}"
            uv=list(struct.iter_unpack('<2H',(folder_run/'uv.bin').read_bytes()))
            for tri in atlas.read_fe((folder_run/'stream.meshlets').read_bytes()):
                words=[uv[c[2]] for c in tri]
                for aa in range(5):
                    for bb in range(5-aa):
                        weights=(aa/4,bb/4,(4-aa-bb)/4)
                        s=sum(w*p[0] for w,p in zip(weights,words))/32768
                        t=sum(w*p[1] for w,p in zip(weights,words))/32768
                        coordinates.append(((s*side+x)/512,(t*side+y)/512,s,t))
        error=max(abs(c-d) for u,v,s,t in coordinates for c,d in zip(scalar(old_base,512,u,v),scalar(levels[side],side,s,t)))
        if error>1e-10:raise ValueError('independent base sampling differs')
        quality=[]
        for lod in (2,3,4,5):
            old_side=512>>lod;new_side=side>>lod;ref=reference(crop,side,new_side)
            errors=[0.,0.]
            for u,v,s,t in coordinates:
                want=scalar(ref,new_side,s,t)
                old=scalar(old_levels[old_side],old_side,u,v);new=scalar(levels[new_side],new_side,s,t)
                for c in range(3):errors[0]+=(old[c]-want[c])**2;errors[1]+=(new[c]-want[c])**2
            errors=[e/(len(coordinates)*3) for e in errors]
            previous=row['sampling']['levels'][lod]
            if abs(previous['before_mse']-errors[0])>1e-8 or abs(previous['after_mse']-errors[1])>1e-8:
                raise ValueError('independent scalar and vector sampling disagree')
            quality.append(dict(lod=lod,before_mse=errors[0],after_mse=errors[1]))
        rows.append(dict(actor=actor,source_atlas_exact=True,new_key_not_in_6501=True,codebook_exact=True,
            crop_base_pixels_exact=True,base_bilinear_samples=len(coordinates),base_bilinear_max_error=error,
            independently_decoded_candidate_levels=8,independent_scalar_matches_vector=True,quality=quality,
            new_key=row['derived_key'],candidate_sha256=row['candidate_sha256']))
    receipt=dict(schema='re4dc-atlas-independent-seal-1',oracle_sha256=a.oracle_sha256,
        source_pack_sha256=atlas.sha(pack),all_6501_source_entries_unmodified=True,
        independent_decodes_including_baselines=decoded,candidate_levels=16,textures=rows,
        target_runtime_sampling_vram_look_and_hardware_accepted=False)
    dump=out/'independent-seal.json';atlas.dump(dump,receipt)
    (out/'oracle').mkdir();shutil.copy2(a.oracle,out/'oracle'/a.oracle.name)
    manifest=''.join(atlas.sha(p.read_bytes())+'  '+p.relative_to(out).as_posix()+'\n' for p in sorted(out.rglob('*')) if p.is_file())
    (out/'SHA256SUMS').write_text(manifest)
    print(json.dumps(dict(textures=len(rows),candidate_levels=16,all_decodes=decoded,
        sha256sums=atlas.sha((out/'SHA256SUMS').read_bytes()),sampling_pass=True)))

if __name__=='__main__':main()
