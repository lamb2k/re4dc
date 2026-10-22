#!/usr/bin/env python3
"""Qualify the explicitly reviewed two-key PS2 item cohort, locally only.

Reads the existing 70-row review ledger and current private inputs. Does not
reclassify the census, modify runtime tables, or approve release adoption.
"""
from pathlib import Path
import argparse, csv, hashlib, importlib.util, json, struct

HERE = Path(__file__).resolve().parent
TOOLS = HERE.parent
KEYS = {'f9282a10-6ed63371', 'fdb79120-f3f8ce57'}
FIRST = {'09b9d35d-9a1a2fc2','4f784887-fc80dbee','5926862b-e61d4941',
         'daa3d452-b10799f3','de020f0a-cc184ee1','f56596f9-c3b192f2'}
BASE_SHA = '6f65275b62838bdff6e7660a2ba8d6b2b43ffabb09cadf5ae05dabb34d9d6c1e'
RR_SHA = '5bba464a1175d8ebe153d5aecb629ea9637807c2bf4fc438a32c17148d0729da'
def sha(b): return hashlib.sha256(b).hexdigest()
def load(p,n):
    s=importlib.util.spec_from_file_location(n,p)
    m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--rr-package',type=Path,required=True)
    p.add_argument('--base-pack',type=Path,required=True)
    p.add_argument('--item-library',type=Path,required=True)
    p.add_argument('--payload-root',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True)
    a=p.parse_args()
    assert not a.out.exists(), 'fresh output required'
    cv=load(TOOLS/'texsrc22/convert.py','mipmap23_item_converter')
    rrblob=a.rr_package.read_bytes();rr=json.loads(rrblob);files=rr['replace']
    source=a.base_pack.read_bytes();stat=a.base_pack.stat()
    assert sha(source)==BASE_SHA
    rrpack=Path(files['dc/tex.pak']);original=rrpack.read_bytes()
    assert sha(original)==RR_SHA
    bp=cv.read_pak(source);op=cv.read_pak(original)
    assert bp.keys()==op.keys()
    prior_changes={'%08x-%08x'%k for k in bp if bp[k]!=op[k]}
    assert prior_changes==FIRST, 'first-six lineage or current package changed'
    resident=Path(files['dc/resident.bin']);rb=resident.read_bytes()
    preload={}
    for room,w,h,f,c,fn in struct.iter_unpack('<4H2I',rb):
        k='%08x-%08x'%(c,fn)
        if k in KEYS:
            assert room and w==h==64
            preload.setdefault(k,[]).append(dict(room='r%03x'%room,width=w,height=h,flags=f))
    assert set(preload)==KEYS
    lib=a.item_library;mb=(lib/'manifest.json').read_bytes()
    tb=(lib/'tex/tex.json').read_bytes()
    tex={r['key']:r for r in json.loads(tb)}
    manifest=json.loads(mb)
    table=TOOLS/'texsrc22/resume-review.tsv'
    review=list(csv.DictReader(table.open(),delimiter='\t'))
    assert len(review)==70
    rows=[]
    carriers={}
    for k in sorted(KEYS):
        row=next(dict(r) for r in review if r['key']==k)
        assert row['review_group']=='ps2-item'
        blob=bp[cv.key_tuple(k)]
        kind,n,*_=cv.identify(blob)
        assert kind=='vq' and n.size==64 and n.texture[3]==0 and not n.mipmapped
        # Pin the actual reviewed PS2 package, not just its descriptive label.
        assert sha(blob)==tex[k]['sha256']
        uses=[]
        for asset in manifest['assets']:
            swaps=[s for s in asset.get('swaps',[]) if s.get('key')==k]
            if not swaps: continue
            assert asset['status']=='PS2' and asset['geometry']=='ps2'
            assert not asset['unhandled_material_flags']
            assert asset['locator']['kind']=='ITM'
            room=asset['room']
            logical='st1/'+room+'.dar'
            carrier=Path(files.get(logical,str(a.payload_root/logical)))
            b=carrier.read_bytes()
            needle=b'R4NREF\0\0'+struct.pack('<II',*cv.key_tuple(k))
            offsets=[];start=0
            while (off:=b.find(needle,start))>=0:
                rec=struct.unpack_from('<8s6I',b,off)
                assert rec[3:6]==(64,64,14)
                offsets.append(off);start=off+len(needle)
            assert offsets, (k,logical,'missing positive current carrier')
            carriers[logical]=dict(source=str(carrier),sha256=sha(b),bytes=len(b))
            uses.append(dict(room=room,name=asset['name'],locator=asset['locator'],
                ps2_bin_sha256=asset['ps2_bin_sha256'],ps2_tpl_sha256=asset['ps2_tpl_sha256'],
                bin_sha256=asset['bin_sha256'],swaps=swaps,current_ref_offsets=offsets))
        assert uses
        row.update(preload_records=preload[k],source_package_sha256=sha(blob),
            source_package_bytes=len(blob),actual_generator=kind,actual_side=64,
            actual_format=0,actual_flags=n.texture[6],ps2_uses=uses)
        rows.append(row)
    gate=TOOLS/'mipmap21/mip_quality.py';holds=TOOLS/'mipmap22/room-select.tsv'
    selection=dict(schema=cv.SCHEMA,base_pack_sha256=BASE_SHA,
        quality_gate_sha256=sha(gate.read_bytes()),hold_keys_sha256=sha(holds.read_bytes()),
        approved_keys=sorted(KEYS))
    cv.validate_selection(selection,source,gate.read_bytes(),holds.read_bytes())
    assert not KEYS.intersection(cv.hold_keys(holds.read_bytes()))
    from collections import Counter
    remaining=[r for r in review if r['key'] not in FIRST|KEYS|{'c8d0db2f-3126bc5d'}]
    sampler_paths=['room/texture_package.cpp','game/platform/native_ui.cpp']
    sampler={str(p):sha((HERE.parents[2]/p).read_bytes()) for p in sampler_paths}
    report=dict(schema='re4dc-mipmap23-items-preflight-1',
        source_pack=str(a.base_pack),source_pack_sha256=BASE_SHA,source_pack_bytes=len(source),
        source_pack_mtime_ns=stat.st_mtime_ns,source_members=len(bp),
        rr_package=str(a.rr_package),rr_package_sha256=sha(rrblob),
        rr_selected_pack=str(rrpack),rr_selected_pack_sha256=RR_SHA,
        preserved_first_six=sorted(FIRST),resident=str(resident),resident_sha256=sha(rb),
        quality_gate=str(gate),quality_gate_sha256=selection['quality_gate_sha256'],
        room_hold_manifest=str(holds),room_hold_manifest_sha256=selection['hold_keys_sha256'],
        selected=rows,item_manifest_sha256=sha(mb),item_tex_manifest_sha256=sha(tb),
        current_carriers=carriers,sampler_sources_sha256=sampler,
        sampler='Native model resolve -> texture::pvr_format preserves TCW mip bit under CAST_MIPMAP -> bilinear PVR header. Base detail unchanged. Source LOD [0,0,0] is not a clamp in this native header path.',
        remaining_review_group_counts=dict(sorted(Counter(r['review_group'] for r in remaining).items())),
        private_generation_only=True,minification='unmeasured',
        shared_ganado_action='retain all 41; hold 39 unresolved consumers',
        prune_action='none',output_runtime_files='none; retain current RR resident/world/other files')
    a.out.mkdir(parents=True)
    (a.out/'selection.json').write_text(json.dumps(selection,indent=2)+'\n')
    (a.out/'input-preflight.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(selected=sorted(KEYS),preserved_first_six=sorted(FIRST),
        remaining=report['remaining_review_group_counts'],resident_sha256=sha(rb)),indent=2))
if __name__=='__main__': main()
