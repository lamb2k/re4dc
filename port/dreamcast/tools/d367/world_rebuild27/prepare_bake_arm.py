#!/usr/bin/env python3
"""Prepare a private baked-house arm, preserving its frozen baseline and pack.

This is input preparation only. It does not master a disc, run a guest, certify
room residency, or modify a recipe. All new textures use the existing loose
package path; the complete original tex.pak is retained byte for byte.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys


def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda:f.read(4*1024*1024),b''):h.update(b)
    return h.hexdigest()


def require(ok,why):
    if not ok:raise ValueError(why)


def manifest(root):
    return {p.relative_to(root).as_posix():{'size':p.stat().st_size,'sha256':sha(p)}
            for p in sorted(root.rglob('*')) if p.is_file()}


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    for key in ('source','baseline-manifest','candidate','sdk-out','raw','out'):
        ap.add_argument('--'+key,type=Path,required=True)
    for key in ('baseline-manifest-sha256','candidate-receipt-sha256','candidate-files-sha256','raw-sha256'):
        ap.add_argument('--'+key,required=True)
    a=ap.parse_args()
    for key in ('source','baseline_manifest','candidate','sdk_out','raw','out'):
        setattr(a,key,getattr(a,key).resolve())
    require(not a.out.exists(),'output must be fresh')
    require(a.out!=a.source and a.source not in a.out.parents and a.out not in a.source.parents,'disjoint stage/source')
    require(sha(a.baseline_manifest)==a.baseline_manifest_sha256,'baseline manifest pin')
    expected=json.loads(a.baseline_manifest.read_text())
    require(manifest(a.source)==expected,'complete source baseline identity')
    receipt_path=a.candidate/'RECEIPT.json'
    require(sha(receipt_path)==a.candidate_receipt_sha256,'candidate receipt pin')
    receipt=json.loads(receipt_path.read_text())
    file_manifest=a.candidate/'SHA256SUMS'
    require(sha(file_manifest)==a.candidate_files_sha256,'candidate complete file-manifest pin')
    recorded={}
    for line in file_manifest.read_text().splitlines():
        digest,name=line.split('  ',1);rel=Path(name)
        require(not rel.is_absolute() and '..' not in rel.parts and name not in recorded,'safe unique candidate file')
        require(sha(a.candidate/rel)==digest,'candidate file identity '+name);recorded[name]=digest
    for name in ('RECEIPT.json','ps2-world.re4mesh','ps2-world.r4sg','world_rebuild27_bake_certificates.inc'):
        require(name in recorded,'candidate file manifest missing '+name)
    require(receipt['schema']=='re4dc.world-rebuild27.baked-package/1','bake receipt schema')
    require(sha(a.candidate/'ps2-world.re4mesh')==receipt['candidate_sha256'],'candidate mesh pin')
    require(sha(a.raw)==a.raw_sha256,'programme pin')
    knobs={}
    for line in (a.sdk_out/'resolved-knobs.txt').read_text().splitlines():
        if '=' in line:
            k,v=line.split('=',1);knobs[k]=v
    for k,v in {'WORLD_REBUILD27':'1','WORLD_REBUILD27_BAKE':'1','TEX_RESIDENT':'1','TEX_PACK':'1'}.items():
        require(knobs.get(k)==v,'required resolved knob '+k)
    relative=Path('dc/native/r101')
    for name in ('ps2-world.r4pw','ps2-world.ids','ps2-world.r4tc','room.r4rc'):
        require(sha(a.candidate/name)==expected[(relative/name).as_posix()]['sha256'],'fixed companion '+name)
    require(len(receipt['textures'])==2,'two texture packages required')
    additions={}
    for row in receipt['textures']:
        crc,fnv,w,h=row['key'];require((w,h)==(512,512),'512 atlas size')
        name='%08x-%08x.re4tex'%(crc,fnv)
        p=a.candidate/'tex'/name
        require(sha(p)==row['native_sha256'],'texture package pin')
        dest=Path('dc/tex')/('%x'%(crc>>28))/name
        require(dest.as_posix() not in expected and dest not in additions,'new, disjoint texture identity')
        additions[dest]=p
    # Verify the new identities cannot be shadowed by the unchanged packed lookup.
    sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
    import texpack
    packed=(a.source/'dc/tex.pak').read_bytes();count,_=texpack.verify(packed)
    import struct
    keys={(struct.unpack_from('<4I',packed,2048+16*i)[:2]) for i in range(count)}
    require(all(tuple(row['key'][:2]) not in keys for row in receipt['textures']),'atlas identity already in source pack')
    subprocess.run([sys.executable,str(Path(__file__).with_name('prepare_arm.py')),
                    '--source',str(a.source),'--candidate',str(a.candidate),'--out',str(a.out)],check=True,capture_output=True,text=True)
    replacements={relative/name:a.candidate/name for name in ('ps2-world.re4mesh','ps2-world.r4sg')}
    replacements[Path('1ST_READ.BIN')]=a.raw
    # Overlay entry points are linked with this programme, never borrowed by label.
    overlays=sorted(a.sdk_out.glob('*.ovl'))
    require(len(overlays)==15,'exact fifteen linked overlays required')
    for p in overlays:
        dest=Path('dc')/p.name;require(dest.as_posix() in expected,'unknown linked overlay')
        replacements[dest]=p
    replacements.update(additions)
    for rel,p in replacements.items():
        dest=a.out/rel;dest.parent.mkdir(parents=True,exist_ok=True)
        if dest.exists():dest.unlink() # remove only this newly created hardlink
        shutil.copyfile(p,dest)
        expected[rel.as_posix()]={'size':p.stat().st_size,'sha256':sha(p)}
    actual=manifest(a.out);require(actual==expected,'complete arm readback identity')
    require(sha(a.out/'dc/tex.pak')==sha(a.source/'dc/tex.pak'),'original packed textures unchanged')
    result={'scope':'private prepared inputs only; no disc, guest, release or console acceptance',
            'source':str(a.source),'out':str(a.out),'candidate_receipt_sha256':a.candidate_receipt_sha256,'candidate_files_sha256':a.candidate_files_sha256,
            'raw_sha256':a.raw_sha256,'files':len(actual),
            'replacements':{r.as_posix():actual[r.as_posix()] for r in replacements},
            'all_other_files_identical':True,'new_textures_loose':True,'original_pack_retained':True,
            'incremental_vram_bytes':receipt['full_incremental_vram_bytes']}
    a.out.with_name(a.out.name+'-bake-preparation.json').write_text(json.dumps(result,indent=2)+'\n')
    a.out.with_name(a.out.name+'-manifest.json').write_text(json.dumps(actual,indent=2,sort_keys=True)+'\n')
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()