#!/usr/bin/env python3
"""Assemble an unbound private C10 L0 bake using existing R4IM/R4PW and VQ.

Dedicated meshlets and vertex records isolate only the C9 house core. No part,
material, placement, owner, higher-LOD or policy edit is made here. Runtime key
overrides are the main lane's separate default-off responsibility.
"""
import argparse
import collections
import copy
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import sys
import zlib

def sha(data):return hashlib.sha256(data).hexdigest()
def fnv(data):
    h=2166136261
    for v in data:h=((h^v)*16777619)&0xffffffff
    return h
def canonical(t):return min(t,t[1:]+t[:1],t[2:]+t[:2])
def require(ok,why):
    if not ok:raise ValueError(why)

def assemble(doc,atlas,w,mesh_lod):
    source=copy.deepcopy(doc);out=copy.deepcopy(doc)
    out['vertices'],out['meshlets'],out['commands'],out['parts'],out['levels']=[],[],[],[],[]
    roles={atlas[role]['source_part']:role for role in ('wall','roof')}
    remaining={role:collections.Counter(canonical(tuple(tuple(v) for v in t['original_corners'])) for t in atlas[role]['target_triangles']) for role in ('wall','roof')}
    baked={role:{canonical(tuple(tuple(v) for v in t['original_corners'])):tuple(tuple(v) for v in t['baked_corners_existing_part_basis']) for t in atlas[role]['target_triangles']} for role in ('wall','roof')}
    require(all(len(baked[r])==len(atlas[r]['target_triangles']) for r in baked),'ambiguous duplicate target triangles')
    ranges=[];expected={};isolated_indices=set();counts=collections.Counter()
    for pi,part in enumerate(source['parts']):
        partfirst=len(out['meshlets']);base=len(out['vertices']);fc,cc=source['part_lods'][pi]
        referenced=set();plan={};role=roles.get(pi)
        for c in source['clusters'][fc:fc+cc]:
            for ordinal,level in enumerate(source['levels'][c[6]:c[6]+c[7]]):
                li=c[6]+ordinal;kept=[];core=[]
                if ordinal==0 and role:
                    for t in w.level_triangles(source,level):
                        k=canonical(t)
                        if remaining[role][k]:remaining[role][k]-=1;core.append(baked[role][k]);counts[role]+=1
                        else:kept.append(t)
                if core:
                    plan[li]=(kept,core)
                    local={tuple(source['vertices'][vi]):vi for ji in range(level[0],level[0]+level[1]) for vi in w.codec.local_vertices(source,ji)}
                    referenced.update(local[v] for t in kept for v in t)
                else:
                    for ji in range(level[0],level[0]+level[1]):referenced.update(w.codec.local_vertices(source,ji))
        oldmap={vi:base+k for k,vi in enumerate(sorted(referenced))}
        out['vertices'].extend(source['vertices'][vi] for vi in sorted(referenced))
        corner_offset={tuple(source['vertices'][vi]):new-base for vi,new in oldmap.items()}
        def pack(ts,core_role=None):
            if not ts:return
            chunks=mesh_lod.pack_meshlets(mesh_lod.stripify(ts),256,lambda v:v[:3])
            first=len(out['meshlets'])
            for chunk in chunks:
                keys=list(dict.fromkeys(v for strip in chunk for v in strip));local={v:i for i,v in enumerate(keys)}
                if core_role:
                    chunkbase=len(out['vertices']);out['vertices'].extend(keys)
                    offsets=list(range(len(keys)));isolated_indices.update(range(chunkbase,chunkbase+len(keys)))
                else:chunkbase=base;offsets=[corner_offset[v] for v in keys]
                require(max(offsets,default=0)<=65535,'part vertex pool offset overflow')
                strips=[[local[v] for v in s] for s in chunk];size=sum(1+len(s) for s in strips)
                bounds=[min(v[a] for v in keys) for a in range(3)]+[max(v[a] for v in keys) for a in range(3)]
                out['meshlets'].append([chunkbase,0,size,len(keys),0x8000|len(strips),*bounds]);out['commands'].append(dict(pool=offsets,strips=strips))
            if core_role:ranges.append(dict(part=pi,first=first,count=len(out['meshlets'])-first,role=core_role))
        for ci in range(fc,fc+cc):
            c=source['clusters'][ci]
            for ordinal in range(c[7]):
                lv=source['levels'][c[6]+ordinal];first=len(out['meshlets']);before=w.level_triangles(source,lv)
                kept,core=plan.get(c[6]+ordinal,([],[]))
                if core:
                    pack(kept);pack(core,role);expected[c[6]+ordinal]=w.canonical(kept+core)
                else:
                    for ji in range(lv[0],lv[0]+lv[1]):
                        rec=list(source['meshlets'][ji]);indices=[oldmap[v] for v in w.codec.local_vertices(source,ji)]
                        if rec[4]&0x8000:rec[0]=base;offsets=[v-base for v in indices]
                        else:
                            rec[0]=min(indices);require(indices==list(range(rec[0],rec[0]+len(indices))),'plain range no longer contiguous');offsets=list(range(len(indices)))
                        out['meshlets'].append(rec);out['commands'].append(dict(pool=offsets,strips=source['commands'][ji]['strips']))
                out['levels'].append([first,len(out['meshlets'])-first,lv[2]])
        out['parts'].append(part[:6]+[partfirst,len(out['meshlets'])-partfirst]+part[8:])
    require(all(not any(c.values()) for c in remaining.values()),'C9 target triangles not found exactly once')
    require(counts=={r:len(atlas[r]['target_triangles']) for r in ('wall','roof')} and sum(counts.values())<=128,'bounded core triangle counts')
    require(len(ranges)<=16 and ranges==sorted(ranges,key=lambda r:r['first']),'range budget/order')
    cursor=0
    for rec,cmd in zip(out['meshlets'],out['commands']):
        cursor+=cursor%2 if rec[4]&0x8000 else 0;rec[1]=cursor
        cursor+=(2*rec[3] if rec[4]&0x8000 else 0)+sum(1+len(s) for s in cmd['strips'])
    return out,ranges,expected,isolated_indices

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    for name in ('helper-dir','source','c9','bake','out'):ap.add_argument('--'+name,type=Path,required=True)
    ap.add_argument('--atlas',type=Path,help='explicit reviewed context-rebound atlas; historical bake exchange is preserved')
    a=ap.parse_args();sys.path.insert(0,str(a.helper_dir));import world_rebuild27 as w;import mesh_lod;import convert_tpl
    require(not a.out.exists(),'immutable C10 output exists')
    original,files,owners,policy=w.load(a.source)
    c9blob=(a.c9/'ps2-world.re4mesh').read_bytes();c9=w.codec.decode(c9blob,files['ps2-world.r4pw'])
    atlas_path=a.atlas or a.bake/'ATLAS-EXCHANGE.json'
    atlas=json.loads(atlas_path.read_text());require(sha(c9blob)==atlas['geometry_candidate_sha256'],'C9 geometry pin')
    require(atlas['schema']=='re4dc.world-rebuild27.house-baked-atlas/1','baked atlas schema')
    names=('ps2-world.re4mesh','ps2-world.r4pw','ps2-world.ids','ps2-world.r4tc','room.r4rc')
    source_pins=atlas['reference_source_sha256'];require(set(names)<=set(source_pins),'all five original A source pins required')
    for name in names:require(sha((a.source/name).read_bytes())==source_pins[name],'original A source hash '+name)
    for name in names[1:]:require((a.c9/name).read_bytes()==(a.source/name).read_bytes(),'C9 source companion '+name)
    prep=(a.bake/'PREPARATION.json').read_bytes();require(sha(prep)==atlas['preparation_sha256'],'bake preparation chain')
    prep_doc=json.loads(prep);provenance=(a.bake/'PS2-TEXTURE-PROVENANCE.json').read_bytes()
    require(sha(provenance)==atlas['provenance_sha256']==prep_doc['provenance_sha256'],'verified PS2 gain proof chain')
    provenance_doc=json.loads(provenance)
    for role in ('wall','roof'):
        require(provenance_doc[role]['ps2_verified'] is True,'source PS2 pixel provenance')
        require(sha((a.bake/(role+'-ps2-source.png')).read_bytes())==provenance_doc[role]['sha256'],'bake source pixel hash '+role)
    exchange_path=a.c9/'HOUSE-EXCHANGE.json';exchange=json.loads(exchange_path.read_text())
    require(exchange['candidate_sha256']==sha(c9blob),'C9 exchange pin')
    require(len(exchange['wall']['source'])==145 and len(exchange['roof']['source'])==262,'407 source core count')
    target_counts={r:len(exchange[r]['target']) for r in ('wall','roof')}
    require(sum(target_counts.values())<=128 and all(target_counts.values()),'reviewed shell triangle budget')
    for role in ('wall','roof'):
        require(len(atlas[role]['target_triangles'])==target_counts[role],'atlas/current C9 target counts')
        require(atlas[role]['source_uv_origin_step']==exchange[role]['uv_origin_step'],'existing sourcepart UV basis pin')
    # Independently prove the C9 room is clean A except its named407core. This
    # refuses any inherited C8 omissions before writing an output directory.
    role_parts={exchange[r]['part']:r for r in ('wall','roof')}
    original_part_l0=collections.defaultdict(collections.Counter);c9_part_l0=collections.defaultdict(collections.Counter)
    for pi in range(len(original['parts'])):
        fc,cc=original['part_lods'][pi]
        for ci in range(fc,fc+cc):
            c=original['clusters'][ci]
            for ordinal in range(c[7]):
                li=c[6]+ordinal;oa=w.canonical(w.level_triangles(original,original['levels'][li]));ca=w.canonical(w.level_triangles(c9,c9['levels'][li]))
                if ordinal==0:original_part_l0[pi].update(oa);c9_part_l0[pi].update(ca)
                else:require(oa==ca,'C9 altered original A higher LOD')
        if pi not in role_parts:require(original_part_l0[pi]==c9_part_l0[pi],'C9 contains noncore original A omission/change')
    for pi,role in role_parts.items():
        spec=exchange[role];require(len(spec['source_ids'])==len(spec['source']),'source core ID count')
        for (ci,ti),record in zip(spec['source_ids'],spec['source']):
            actual=w.level_triangles(original,original['levels'][original['clusters'][ci][6]])[ti]
            require(canonical(actual)==canonical(tuple(tuple(v) for v in record['corners'])),'source core mapping')
        expected=original_part_l0[pi].copy();expected.subtract(w.canonical([tuple(tuple(v) for v in t['corners']) for t in spec['source']]))
        require(all(n>=0 for n in expected.values()),'source core is not part of original A')
        target=w.canonical([tuple(tuple(v) for v in t['corners']) for t in spec['target']]);expected.update(target)
        require(+expected==c9_part_l0[pi],'C9 source core replacement is not isolated')
        for triangle,count in target.items():require(c9_part_l0[pi][triangle]==count,'ambiguous C9 target triangle identity')
    keys={};texture_report=[]
    for role in ('wall','roof'):
        blob=(a.bake/(role+'-baked.re4tex')).read_bytes();h=convert_tpl.HEADER.unpack_from(blob);t=convert_tpl.TEXTURE.unpack_from(blob,h[5]);payload=blob[h[6]:h[6]+h[7]]
        require((t[1],t[2],t[3],t[6],t[7])==(512,512,convert_tpl.FORMAT_RGB565,0,convert_tpl.PAYLOAD_VQ),'512 RGB565 base-only VQ required')
        require(t[5]==len(payload)==67584,'actual full-codebook VQ payload')
        keys[role]=[zlib.crc32(payload)&0xffffffff,fnv(payload),512,512]
        texture_report.append(dict(role=role,key=keys[role],payload_bytes=len(payload),aligned_vram_bytes=(len(payload)+31)&~31,native_file_bytes=len(blob),native_sha256=sha(blob)))
    out,ranges,expected,isolated=assemble(c9,atlas,w,mesh_lod)
    a.out.mkdir(parents=True);(a.out/'ps2-world.raw.re4mesh').write_bytes(w.codec.serialize_mesh(out));(a.out/'ps2-world.r4pw').write_bytes(files['ps2-world.r4pw'])
    run=subprocess.run([sys.executable,str(a.helper_dir/'ps2_strip_groups.py'),str(a.out/'ps2-world.raw.re4mesh'),str(a.out/'ps2-world.r4pw'),str(a.out/'ps2-world.re4mesh'),str(a.out/'ps2-world.r4sg'),'--groups','4','--report',str(a.out/'strip-groups.json')],check=True,capture_output=True,text=True)
    (a.out/'strip-groups.log').write_text(run.stdout+run.stderr)
    sg=bytearray((a.out/'ps2-world.r4sg').read_bytes());struct.pack_into('<I',sg,24,policy);(a.out/'ps2-world.r4sg').write_bytes(sg)
    for name in ('ps2-world.ids','ps2-world.r4tc','room.r4rc'):
        require((a.c9/name).read_bytes()==(a.source/name).read_bytes(),'unchanged C9 source companion '+name)
        (a.out/name).write_bytes((a.source/name).read_bytes())
    mesh=(a.out/'ps2-world.re4mesh').read_bytes();decoded=w.codec.decode(mesh,files['ps2-world.r4pw'])
    require(zlib.crc32(mesh[80:])&0xffffffff==struct.unpack_from('<I',mesh,12)[0],'fresh body CRC')
    for key in ('meshes','placements','materials','part_lods'):require(decoded[key]==original[key],'source identity '+key)
    require([c[6:] for c in decoded['clusters']]==[c[6:] for c in original['clusters']],'source cluster identities')
    owner_levels=unmodified_levels=0
    for mi,m in enumerate(c9['meshes']):
        for pi in range(m[6],m[6]+m[7]):
            fc,cc=c9['part_lods'][pi]
            for c in c9['clusters'][fc:fc+cc]:
                for ordinal in range(c[7]):
                    li=c[6]+ordinal;after=w.canonical(w.level_triangles(decoded,decoded['levels'][li]));before=w.canonical(w.level_triangles(c9,c9['levels'][li]))
                    require(after==expected.get(li,before),'unexpected oriented triangle change')
                    if li not in expected:unmodified_levels+=1
                    if mi in owners:require(after==w.canonical(w.level_triangles(original,original['levels'][li])),'changing owner geometry');owner_levels+=1
    core_meshlets={ji:r for r in ranges for ji in range(r['first'],r['first']+r['count'])};core_vertices=set();old_vertices=set();actual=collections.Counter()
    for ji in range(len(decoded['meshlets'])):
        indices=set(w.codec.local_vertices(decoded,ji))
        if ji in core_meshlets:
            core_vertices.update(indices);role=core_meshlets[ji]['role'];ts=[]
            local=w.codec.local_vertices(decoded,ji)
            for tri in w.codec.triangles(decoded,ji):ts.append(tuple(tuple(decoded['vertices'][local[k]]) for k in tri))
            actual[role]+=len(ts);require(all(v[5]==65535 for t in ts for v in t),'baked core prelight not white')
        else:old_vertices.update(indices)
    require(not core_vertices&old_vertices,'baked core shares retained/higher-LOD vertex records')
    require(actual==target_counts,'final SG meshlet range includes other geometry')
    native_exchange=dict(schema='re4dc.world-rebuild27.native-baked-core/1',candidate_sha256=sha(mesh),geometry_source='actual decoded final R4IM strip triangles',uv_convention='runtime top-left decoded through unchanged sourcepart basis',wall=[],roof=[])
    for ji,r in core_meshlets.items():
        role=r['role'];spec=exchange[role];m=decoded['meshes'][spec['mesh']];pl=decoded['placements'][spec['placement']];basis=spec['uv_origin_step'];local=w.codec.local_vertices(decoded,ji)
        for indices in w.codec.triangles(decoded,ji):
            corners=[decoded['vertices'][local[k]] for k in indices];world=[]
            for vertex in corners:
                xyz=[vertex[i]*m[11+i]+m[8+i] for i in range(3)]
                world.append([sum(pl[2+4*i+j]*xyz[j] for j in range(3))+pl[2+4*i+3] for i in range(3)])
            native_exchange[role].append(dict(meshlet=ji,corners=corners,world_mm=world,uv_top_left=[[basis[0]+v[3]*basis[2],basis[1]+v[4]*basis[3]] for v in corners],prelight_word=[v[5] for v in corners]))
    (a.out/'NATIVE-CORE-EXCHANGE.json').write_text(json.dumps(native_exchange,indent=2)+'\n')
    crc=struct.unpack_from('<I',mesh,12)[0]
    header='// PRIVATE GENERATED L0 baked core ranges; include inside re4dc::world_bake27.\n'
    header+='inline constexpr unsigned mesh_crc=0x%08xU,mesh_bytes=%dU;\n'%(crc,len(mesh))
    header+='inline constexpr Range ranges[]={\n'+''.join('{%dU,%dU,%dU,{%s}},\n'%(r['part'],r['first'],r['count'],','.join('0x%08xU'%v for v in keys[r['role']])) for r in ranges)+'};\n'
    header+='inline constexpr unsigned textures[2][4]={\n'+''.join('{'+','.join('0x%08xU'%v for v in keys[role])+'},\n' for role in ('wall','roof'))+'};\n'
    (a.out/'world_rebuild27_bake_certificates.inc').write_text(header)
    row=[0x101,len(files['ps2-world.r4pw']),len(out['placements']),len(out['parts']),len(out['meshes']),struct.unpack_from('<I',files['ps2-world.r4pw'],20)[0],fnv(files['ps2-world.r4pw']),crc,len(mesh),policy]
    (a.out/'world_rebuild27_certificates.inc').write_text('// PRIVATE source-policy mapping, independent from bake range override.\nstatic constexpr Certificate rebuild27_certificates[]={\n{'+','.join('0x%08xU'%v for v in row)+'},\n};\n')
    texture_dir=a.out/'tex';texture_dir.mkdir()
    for role,key in keys.items():(texture_dir/('%08x-%08x.re4tex'%tuple(key[:2]))).write_bytes((a.bake/(role+'-baked.re4tex')).read_bytes())
    receipt=dict(schema='re4dc.world-rebuild27.baked-package/1',c9_sha256=sha(c9blob),atlas_sha256=sha(atlas_path.read_bytes()),preparation_sha256=sha(prep),provenance_sha256=sha(provenance),baseline_five_source_sha256=source_pins,context_original_source_A=True,all_noncore_original_A_exact=True,candidate_sha256=sha(mesh),candidate_crc='%08x'%crc,candidate_bytes=len(mesh),ranges=[dict(r,key=keys[r['role']]) for r in ranges],textures=texture_report,full_incremental_vram_bytes=sum(r['aligned_vram_bytes'] for r in texture_report),source_triangles=407,candidate_core_triangles=sum(target_counts.values()),owner_meshes_exact=len(owners),owner_levels_exact=owner_levels,other_levels_exact=unmodified_levels,distinct_baked_vertex_records=len(core_vertices),retained_core_vertex_overlap=0,source_identity_tables_unchanged=True,whole_companions_unchanged=True,all_higher_lods_exact=True,appearance_accepted=False,timing_available=False,tool_sha256=sha(Path(__file__).read_bytes()))
    (a.out/'RECEIPT.json').write_text(json.dumps(receipt,indent=2)+'\n')
    (a.out/'RECIPE.txt').write_text('PRIVATE C10 baked L0 house core, unbound until separate default-off main runtime override.\nCommand: '+json.dumps(sys.argv)+'\nAll parts, R4PW, placements, owner paths, higherLODs, R4ID, R4TC and whole room.r4rc unchanged.\nOnly selected C9 core gets private meshlets/vertex records, new encoded atlas UV, white prelight.\nNew two512RGB565VQ maps cost fullincremental135168VRAMbytes; originals remain resident. No timing/appearance acceptance.\n')
    (a.out/'SHA256SUMS').write_text(''.join(sha(p.read_bytes())+'  '+str(p.relative_to(a.out))+'\n' for p in sorted(a.out.rglob('*')) if p.is_file()))
    print(json.dumps(receipt,indent=2))

if __name__=='__main__':main()
