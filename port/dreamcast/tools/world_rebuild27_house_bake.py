#!/usr/bin/env python3
"""Prepare/encode a private PS2-only Blender bake for the bounded C9 3D house.

No runtime binding, stage, recipe, renderer or source geometry is modified.
The two new maps are incremental residency; original PS2 textures remain resident.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import struct
import subprocess
import sys

HERE=Path(__file__).resolve().parent
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def require(ok,message):
    if not ok:raise ValueError(message)

def prepare(a):
    require(not a.out.exists(),'immutable output already exists')
    exchange=json.loads(a.exchange.read_text());proof=json.loads(a.textures.read_text())
    require(exchange['schema']=='re4dc.world-rebuild27.house-exchange/1','C9 exchange schema')
    target_total=sum(len(exchange[role]['target']) for role in ('wall','roof'))
    require(0<target_total<=128,'reviewed one-house target cap')
    for role,key,source_count in [('wall','0c77c65b-a7d392ac',145),('roof','5f6ca8e9-290510a7',262)]:
        obj=exchange[role];tex=proof[role]
        require(obj['source_material_key']==key,'source material key '+role)
        require(len(obj['source'])==source_count and 0<len(obj['target'])<=128,'bounded C9 counts')
        require(tex['ps2_verified'] is True and tex['material_key']==key,'verified PS2 texture required '+role)
        path=Path(tex['path']);require(sha(path)==tex['sha256'],'source image digest '+role)
        for kind in ('source','target'):
            for t in obj[kind]:
                require(len(t['world_mm'])==len(t['uv'])==len(t['prelight_rgba'])==3,'triangle corner shape')
                require(all(len(p)==3 for p in t['world_mm']),'world position shape')
                require(all(len(v)==4 and all(0<=c<=1 for c in v) for v in t['prelight_rgba']),'source prelight range')
    a.out.mkdir(parents=True)
    shutil.copy2(a.exchange,a.out/'HOUSE-EXCHANGE.json');shutil.copy2(a.textures,a.out/'PS2-TEXTURE-PROVENANCE.json')
    for role in ('wall','roof'):shutil.copy2(proof[role]['path'],a.out/(role+'-ps2-source.png'))
    producer=a.out/'producer';producer.mkdir()
    for helper in (HERE/'house_bake27').glob('*.py'):shutil.copy2(helper,producer/helper.name)
    shutil.copy2(Path(__file__),producer/Path(__file__).name)
    recipe=dict(schema='re4dc.world-rebuild27.house-bake/1',exchange_sha256=sha(a.exchange),provenance_sha256=sha(a.textures),tool_sha256=sha(Path(__file__)),blender_script_sha256=sha(HERE/'house_bake27/blender_bake.py'),source_policy='PS2 geometry, PS2 texture texels and PS2 prelight only',reference_triangles=407,target_triangles=target_total,dimensions=[512,512],maps=2,mipmaps=False,source_geometry_untouched=True,incremental_texture_residency=True,original_textures_retained=True,runtime_binding='Main must isolate the selected house core from shared source material parts before any target adoption',appearance_accepted=False,timing_available=False)
    recipe['roof_continuation']=a.roof_continuation
    recipe['producer_files_sha256']={p.name:sha(p) for p in sorted(producer.iterdir()) if p.is_file()}
    (a.out/'PREPARATION.json').write_text(json.dumps(recipe,indent=2)+'\n')
    (a.out/'RECIPE.txt').write_text('Private unaccepted C9 3D shell with PS2-only baked static detail.\nPrepare command: '+json.dumps(sys.argv)+'\nBlender Cycles EMIT selected-to-active; source texture multiplied by source corner prelight. No new lights or generated image content.\nTwo 512x512 RGB565/VQ maps, no mipmaps initially. Original textures stay resident; all texture costs incremental.\nGeometry remains the reviewed C9 '+str(target_total)+' triangles with real windows, doors, wall thickness, roof notches and raised roof ridge.\nNumeric color: Non-Color images, Raw view, verbatim stored inverse-gained PS2 R4IM prelight; no extra gain/inverse gain or generated lighting.\nNo runtime binding, staging, SDK/Flycast, disc, SD or production recipe action.\n')
    print(json.dumps(recipe,indent=2))

def encode(a):
    sys.path.insert(0,str(HERE));import convert_tpl
    require((a.out/'BLENDER-BAKE-RECEIPT.json').exists(),'actual Blender bake receipt required')
    report=dict(encoder=str(a.pvrtex),encoder_sha256=sha(a.pvrtex),mipmaps=False,original_textures_retained=True,full_incremental_vram_bytes=0,maps=[])
    for role in ('wall','roof'):
        png=a.out/(role+'-baked.png');dt=a.out/(role+'-baked.dt');package=a.out/(role+'-baked.re4tex')
        require(png.exists() and not dt.exists() and not package.exists(),'bake input or immutable encoded output')
        cmd=[str(a.pvrtex),'-i',str(png),'-o',str(dt),'-f','RGB565','-c','256','-p',str(a.out/(role+'-vq-preview.png'))]
        r=subprocess.run(cmd,check=True,capture_output=True,text=True);(a.out/(role+'-encode.log')).write_text(r.stdout+r.stderr)
        blob,metadata=convert_tpl.package_existing_vq(dt.read_bytes(),'world-rebuild27-house-'+role)
        package.write_bytes(blob);(a.out/(role+'-texture-package.json')).write_text(json.dumps(metadata,indent=2)+'\n')
        h=convert_tpl.HEADER.unpack_from(blob);desc=convert_tpl.TEXTURE.unpack_from(blob,h[5])
        # HEADER offsets are read by the existing packer's metadata; inspect
        # returned backing explicitly rather than treating package file size as VRAM.
        payload_bytes=metadata['vram_bytes'];aligned=(payload_bytes+31)&~31
        require(metadata['width']==metadata['height']==512 and metadata['payload']=='vq','encoded dimensions/layout')
        require(desc[5]==payload_bytes and payload_bytes==2048+512*512//4,'actual descriptor compact VQ backing')
        row=dict(role=role,width=512,height=512,encoded_file_bytes=dt.stat().st_size,native_package_file_bytes=len(blob),actual_vq_payload_bytes=payload_bytes,aligned_vram_bytes=aligned,mip_backing_bytes=0,encoder_metadata=metadata,dt_sha256=sha(dt),native_package_sha256=sha(package),base_vq_theory_bytes=2048+512*512//4)
        report['full_incremental_vram_bytes']+=aligned
        report['maps'].append(row)
    report['full_incremental_native_package_bytes']=sum(r['native_package_file_bytes'] for r in report['maps'])
    report['runtime_allocation_acceptance']='Encoded payload/alignment accounting only; main must prove contiguous VRAM and per-core material binding. No original texture residency is subtracted.'
    (a.out/'ENCODED-TEXTURE-BUDGET.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))

def main():
    ap=argparse.ArgumentParser(description=__doc__);sp=ap.add_subparsers(dest='operation',required=True)
    p=sp.add_parser('prepare');p.add_argument('--exchange',type=Path,required=True);p.add_argument('--textures',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    p.add_argument('--roof-continuation',action='store_true',help='explicit bounded PS2-only same-component roof texture continuation; geometry unchanged')
    p=sp.add_parser('encode');p.add_argument('--out',type=Path,required=True);p.add_argument('--pvrtex',type=Path,required=True)
    a=ap.parse_args();prepare(a) if a.operation=='prepare' else encode(a)

if __name__=='__main__':main()
