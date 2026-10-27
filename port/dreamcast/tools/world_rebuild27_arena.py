#!/usr/bin/env python3
"""Private three-arm r101 house-only arena, using the existing R4IM/R4PW codec.

No staging, runtime selection, actor filtering or performance acceptance lives here.
Source identities and all four companions remain immutable. A separately reviewed
placement whitelist is required because source meshes can have multiple instances.
"""
import argparse
import collections
import json
from pathlib import Path
import sys
import world_rebuild27 as w


def components(d, ordinal=0):
    """Connected positional source components across clusters at one LOD ordinal."""
    for mi, mesh in enumerate(d['meshes']):
        for pi in range(mesh[6], mesh[6]+mesh[7]):
            first,count=d['part_lods'][pi]
            ts={}
            for ci in range(first,first+count):
                cluster=d['clusters'][ci]
                if ordinal>=cluster[7]:continue
                li=cluster[6]+ordinal
                for ti,t in enumerate(w.level_triangles(d,d['levels'][li])):ts[(li,ti)]=t
            parent={}
            def find(v):
                parent.setdefault(v,v)
                while parent[v]!=v:parent[v]=parent[parent[v]];v=parent[v]
                return v
            for t in ts.values():
                r=find(t[0][:3])
                for v in t[1:]:parent[find(v[:3])]=r
            grouped=collections.defaultdict(list)
            for ident,t in ts.items():grouped[find(t[0][:3])].append(ident)
            for ids in sorted(grouped.values(),key=lambda group:min(group)):
                yield mi,pi,ids,[ts[i] for i in ids]


def world_triangles(d,mi,pli,ts):
    m=d['meshes'][mi];p=d['placements'][pli]
    return [[[sum(p[2+4*a+j]*(v[j]*m[11+j]+m[8+j]) for j in range(3))+p[2+4*a+3]
               for a in range(3)]for v in t]for t in ts]


def inspect(a):
    w.require(not a.out.exists(),'immutable inspection output exists')
    d,files,owners,policy=w.load(a.source)
    lo,hi=a.bounds[:3],a.bounds[3:]
    rows=[]
    for ordinal in range(max(c[7]for c in d['clusters'])):
        for mi,pi,ids,ts in components(d,ordinal):
            for pli,p in enumerate(d['placements']):
                if p[0]!=mi:continue
                world=world_triangles(d,mi,pli,ts)
                low=[min(v[k]for t in world for v in t)for k in range(3)]
                high=[max(v[k]for t in world for v in t)for k in range(3)]
                if not all(high[k]>=lo[k]and low[k]<=hi[k]for k in range(3)):continue
                rows.append(dict(component='%d:%d:%d:%d'%(pli,pi,ordinal,min(ids)[0]*100000+min(ids)[1]),
                    mesh=mi,part=pi,placement=pli,lod=ordinal,source_ids=ids,
                    source_triangles=len(ts),source_material=d['materials'][pi],changing_owner=mi in owners,
                    low=low,high=high,fully_contained=all(low[k]>=lo[k]and high[k]<=hi[k]for k in range(3)),
                    world_mm=world))
    a.out.mkdir(parents=True)
    result=dict(schema='re4dc.world-rebuild27.arena-components/1',source_sha256={n:w.sha(v)for n,v in files.items()},
                bounds=a.bounds,scope='geometric census only; semantic house selection NOT established',components=rows)
    (a.out/'COMPONENTS.json').write_text(json.dumps(result,separators=(',',':'))+'\n')
    print(json.dumps(dict(output=str(a.out),components=len(rows),lod0=sum(x['lod']==0 for x in rows))))


def build(a):
    import copy,struct,subprocess,zlib
    import mesh_lod
    import world_rebuild27_bake_pack as bake
    w.require(not a.out.exists(),'immutable arena output exists')
    plan_bytes=a.plan.read_bytes();plan=json.loads(plan_bytes)
    w.require(plan['schema']=='re4dc.world-rebuild27.arena-plan/1','arena plan schema')
    toolchain={'helper':'world_rebuild27.py','bake_assembler':'world_rebuild27_bake_pack.py','strip_groups':'ps2_strip_groups.py','codec':'d367/world_blender_roundtrip/package.py'}
    w.require(set(plan['toolchain_sha256'])==set(toolchain),'exact toolchain pin inventory')
    for key,name in toolchain.items():w.require(w.sha((Path(__file__).parent/name).read_bytes())==plan['toolchain_sha256'][key],'toolchain pin '+key)
    sources={};source_files={}
    for arm in ('A','B','C'):
        spec=plan['inputs'][arm];root=Path(spec['path'])
        w.require(set(spec['sha256'])==set(w.SOURCE_INPUTS),'all five pins '+arm)
        files={n:(root/n).read_bytes()for n in w.SOURCE_INPUTS}
        for n,blob in files.items():w.require(w.sha(blob)==spec['sha256'][n],'input pin '+arm+' '+n)
        source_files[arm]=files
        sources[arm]=w.codec.decode(files[w.SOURCE_INPUTS[0]],files[w.SOURCE_INPUTS[1]],True)
    d=sources['A'];files=source_files['A']
    for arm in ('B','C'):
        for n in w.UNCHANGED_COMPANIONS:w.require(source_files[arm][n]==files[n],'unchanged input companion '+arm+' '+n)
        for key in ('meshes','placements','materials','part_lods'):
            w.require(sources[arm][key]==d[key],'source identity '+arm+' '+key)
        w.require([c[6:]for c in sources[arm]['clusters']]==[c[6:]for c in d['clusters']],'cluster identity '+arm)
    exchange_blob=Path(plan['exchange']['path']).read_bytes()
    native_blob=Path(plan['native_core']['path']).read_bytes()
    w.require(w.sha(exchange_blob)==plan['exchange']['sha256'],'exchange pin')
    w.require(w.sha(native_blob)==plan['native_core']['sha256'],'native core pin')
    exchange=json.loads(exchange_blob);native=json.loads(native_blob)
    w.require(exchange['candidate_sha256']==plan['inputs']['B']['sha256'][w.SOURCE_INPUTS[0]],'B exchange identity')
    w.require(native['candidate_sha256']==plan['inputs']['C']['sha256'][w.SOURCE_INPUTS[0]],'C native identity')
    selected=collections.defaultdict(set);placements=set();selected_records=[]
    catalog={}
    for ordinal in range(max(c[7]for c in d['clusters'])):
        for mi,pi,ids,ts in components(d,ordinal):
            catalog[(mi,pi,ordinal,tuple(tuple(i)for i in ids))]=ts
    by_placement=collections.defaultdict(set)
    for rec in plan['components']:
        key=(rec['mesh'],rec['part'],rec['lod'],tuple(tuple(i)for i in rec['source_ids']))
        w.require(key in catalog,'exact complete selected source component '+rec['component'])
        pli=rec['placement'];w.require(0<=pli<len(d['placements'])and d['placements'][pli][0]==rec['mesh'],'selected source placement')
        for li,ti in rec['source_ids']:selected[li].add(ti);by_placement[pli].add((li,ti))
        placements.add(pli);selected_records.append(rec)
    by_mesh=collections.defaultdict(set)
    for pli,ids in by_placement.items():by_mesh[d['placements'][pli][0]].update(ids)
    for pli,ids in by_placement.items():w.require(ids==by_mesh[d['placements'][pli][0]],'shared mesh selection must agree at every whitelisted placement')
    base={li:[t for ti,t in enumerate(w.level_triangles(d,level))if ti in selected[li]]for li,level in enumerate(d['levels'])}
    expected={'A':base,'B':copy.deepcopy(base)};core={};atlas={}
    for role in ('wall','roof'):
        spec=exchange[role];part=spec['part'];source_ids=spec['source_ids']
        w.require(len(source_ids)=={'wall':145,'roof':262}[role],'source core size')
        for (ci,ti),record in zip(source_ids,spec['source']):
            li=d['clusters'][ci][6];t=w.level_triangles(d,d['levels'][li])[ti]
            w.require(ti in selected[li]and w.canonical([t])==w.canonical([tuple(tuple(v)for v in record['corners'])]),'selected source core')
            expected['B'][li].remove(t)
        target=[tuple(tuple(v)for v in t['corners'])for t in spec['target']]
        first=d['clusters'][min(ci for ci,ti in source_ids)][6]
        expected['B'][first].extend(target);core[role]=target
        def shape(t):return min(tuple(v[:3]for v in t),tuple(v[:3]for v in t[1:]+t[:1]),tuple(v[:3]for v in t[2:]+t[:2]))
        baked_by_shape={shape(tuple(tuple(v)for v in t['corners'])):tuple(tuple(v)for v in t['corners'])for t in native[role]}
        w.require(len(baked_by_shape)==len(target),'unambiguous C geometry')
        atlas[role]={'source_part':part,'target_triangles':[]}
        for t in target:
            bt=baked_by_shape[shape(t)]
            for shift in range(3):
                rotated=bt[shift:]+bt[:shift]
                if all(old[:3]==new[:3]for old,new in zip(t,rotated)):break
            else:raise ValueError('C corner orientation differs')
            atlas[role]['target_triangles'].append(dict(original_corners=t,baked_corners_existing_part_basis=rotated))
    w.require(sum(map(len,core.values()))==112,'reviewed 112 core')
    # Verify actual full-world B/C inputs contain only the already reviewed core replacement.
    for arm in ('B','C'):
        all_expected={li:w.level_triangles(d,lv)for li,lv in enumerate(d['levels'])}
        for role in ('wall','roof'):
            spec=exchange[role]
            for ci,ti in sorted(spec['source_ids'],reverse=True):
                li=d['clusters'][ci][6];all_expected[li].pop(ti)
            li=d['clusters'][min(ci for ci,ti in spec['source_ids'])][6]
            all_expected[li].extend(core[role]if arm=='B'else[tuple(tuple(v)for v in t['corners'])for t in native[role]])
        for li,lv in enumerate(sources[arm]['levels']):
            w.require(w.canonical(w.level_triangles(sources[arm],lv))==w.canonical(all_expected[li]),'full-world input noncore/higher identity '+arm+' level'+str(li))
    class Levels(dict):
        def __init__(self,values):
            super().__init__();self.cursor=collections.Counter()
            for ci,c in enumerate(d['clusters']):dict.__setitem__(self,ci,[values[c[6]+i]for i in range(c[7])if d['levels'][c[6]+i][1]])
        def __getitem__(self,ci):
            k=self.cursor[ci];self.cursor[ci]+=1;return dict.__getitem__(self,ci)[k]
    docs={}
    for arm in ('A','B'):
        working=copy.deepcopy(d);working.pop('index_layout',None);working['schema']=w.codec.SCHEMA
        docs[arm]=w.install_shells(working,Levels(expected[arm]))
    docs['C'],ranges,c_expected,isolated=bake.assemble(docs['B'],atlas,w,mesh_lod)
    expected['C']={li:w.level_triangles(docs['B'],lv)for li,lv in enumerate(docs['B']['levels'])}
    for li in c_expected:expected['C'][li]=w.level_triangles(docs['C'],docs['C']['levels'][li])
    policy=struct.unpack_from('<I',files['ps2-world.ids'],12)[0]
    c_receipt_blob=Path(plan['inputs']['C']['path'],'RECEIPT.json').read_bytes()
    w.require(w.sha(c_receipt_blob)==plan['c_receipt_sha256'],'actual C receipt pin')
    c_receipt=json.loads(c_receipt_blob)
    w.require(c_receipt['candidate_sha256']==plan['inputs']['C']['sha256'][w.SOURCE_INPUTS[0]],'C receipt identity')
    keys={r['role']:r['key']for r in c_receipt['ranges']}
    w.require(set(keys)=={'wall','roof'}and len(set(tuple(k)for k in keys.values()))==2,'actual two-role C material inventory')
    used_parts={r['part']for r in selected_records};textures={tuple(d['materials'][p][:4])for p in used_parts}
    textures.update(tuple(k)for k in keys.values());texture_rows=[]
    import hashlib
    import convert_tpl
    pak_path=Path(plan['texture_archive']['path'])
    with pak_path.open('rb') as f:
        w.require(hashlib.file_digest(f,'sha256').hexdigest()==plan['texture_archive']['sha256'],'source texture archive pin')
        f.seek(0);magic,version,count,ioff,doff,index_crc=struct.unpack('<8s5I',f.read(28))
        w.require(magic==b'RE4PAK1\0'and version==1,'existing texture archive format')
        f.seek(ioff);index=f.read(doff-ioff);w.require(zlib.crc32(index)&0xffffffff==index_crc,'texture archive index CRC')
        entries={tuple(row[:2]):tuple(row[2:])for row in(struct.unpack_from('<4I',index,16*i)for i in range(count))}
        for key in sorted(textures):
            name='%08x-%08x.re4tex'%key[:2]
            if list(key)in keys.values():
                path=Path(plan['inputs']['C']['path'],'tex',name);blob=path.read_bytes();location=dict(path=str(path))
                expected_tex=next(t for t in c_receipt['textures']if t['key']==list(key))
                w.require(w.sha(blob)==expected_tex['native_sha256'],'actual baked texture pin')
            else:
                w.require(key[:2]in entries,'selected source texture absent from actual archive')
                offset,size=entries[key[:2]];f.seek(offset);blob=f.read(size)
                location=dict(archive=str(pak_path),offset=offset,archive_sha256=plan['texture_archive']['sha256'])
            h=convert_tpl.HEADER.unpack_from(blob);t=convert_tpl.TEXTURE.unpack_from(blob,h[5])
            w.require(all(1<=v<=1024 and not(v&(v-1))for v in t[1:3]),'supported native texture dimensions')
            texture_rows.append(dict(key=key,**location,sha256=w.sha(blob),bytes=len(blob),payload_bytes=h[7],native_dimensions=t[1:3],logical_dimensions=key[2:],dimension_contract='original pinned source logical identity; native rect replacement dimensions recorded separately',native_format=t[3],native_flags=t[7]))
    # Every input, selected component and texture pin has been checked before output creation.
    a.out.mkdir(parents=True);(a.out/'arena-plan.json').write_bytes(plan_bytes)
    rows=[];results=[]
    for index,arm in enumerate(('A','B','C')):
        out=a.out/'native/r101'/('arena'+str(index));out.mkdir(parents=True)
        raw=w.codec.serialize_mesh(docs[arm]);w.require(w.codec.serialize_policy(docs[arm])==files['ps2-world.r4pw'],'unchanged output policy')
        (out/'ps2-world.raw.re4mesh').write_bytes(raw)
        for n in w.UNCHANGED_COMPANIONS:(out/n).write_bytes(files[n]);w.require((out/n).read_bytes()==files[n],'companion readback '+n)
        run=subprocess.run([sys.executable,str(Path(__file__).parent/'ps2_strip_groups.py'),str(out/'ps2-world.raw.re4mesh'),str(out/'ps2-world.r4pw'),str(out/'ps2-world.re4mesh'),str(out/'ps2-world.r4sg'),'--groups','4','--report',str(out/'strip-groups.json')],capture_output=True,text=True,check=True)
        (out/'strip-groups.log').write_text(run.stdout+run.stderr)
        sg=bytearray((out/'ps2-world.r4sg').read_bytes());struct.pack_into('<I',sg,24,policy);(out/'ps2-world.r4sg').write_bytes(sg)
        mesh=(out/'ps2-world.re4mesh').read_bytes();final=w.codec.decode(mesh,files['ps2-world.r4pw'])
        crc=struct.unpack_from('<I',mesh,12)[0];w.require(zlib.crc32(mesh[80:])&0xffffffff==crc,'actual payload CRC')
        for li,level in enumerate(final['levels']):w.require(w.canonical(w.level_triangles(final,level))==w.canonical(expected[arm][li]),'final selected-level identity '+arm+str(li))
        for key in ('meshes','placements','materials','part_lods'):w.require(final[key]==d[key],'final source identity '+key)
        w.require([c[6:]for c in final['clusters']]==[c[6:]for c in d['clusters']],'final cluster identity')
        row=[0x101,len(files['ps2-world.r4pw']),len(d['placements']),len(d['parts']),len(d['meshes']),struct.unpack_from('<I',files['ps2-world.r4pw'],20)[0],w.fnv(files['ps2-world.r4pw']),crc,len(mesh),policy];rows.append(row)
        receipt=dict(arm=arm,candidate_sha256=w.sha(mesh),candidate_crc='%08x'%crc,candidate_bytes=len(mesh),source_pins=plan['inputs'],l0_triangles=sum(len(w.level_triangles(final,final['levels'][c[6]]))for c in final['clusters']),all_level_triangles=sum(len(v)for v in expected[arm].values()),selected_source_components=len(selected_records),placements=sorted(placements),companions_readback_verified=True,companion_sha256={n:w.sha((out/n).read_bytes())for n in w.UNCHANGED_COMPANIONS},all707_level_geometry_checked=True,source_identity_tables_exact=True,house_scope='explicit structural source component selection; no loose props/terrain/other houses',appearance_accepted=False,timing_available=False)
        if arm=='C':
            core_indices={i:r['role']for r in ranges for i in range(r['first'],r['first']+r['count'])};actual=collections.Counter();core_vertices=set();other_vertices=set()
            for ji in range(len(final['meshlets'])):
                local=w.codec.local_vertices(final,ji)
                if ji in core_indices:
                    core_vertices.update(local);actual[core_indices[ji]]+=len(list(w.codec.triangles(final,ji)))
                    w.require(all(final['vertices'][vi][5]==65535 for vi in local),'C baked-only prelight')
                else:other_vertices.update(local)
            w.require(not(core_vertices&other_vertices)and actual=={'wall':63,'roof':49},'isolated exact baked ranges')
            receipt['baked_ranges']=[dict(r,key=keys[r['role']])for r in ranges]
            header='// PRIVATE; include inside re4dc::world_bake27.\ninline constexpr unsigned mesh_crc=0x%08xU,mesh_bytes=%dU;\n'%(crc,len(mesh))
            header+='inline constexpr Range ranges[]={\n'+''.join('{%dU,%dU,%dU,{%s}},\n'%(r['part'],r['first'],r['count'],','.join('0x%08xU'%v for v in keys[r['role']]))for r in ranges)+'};\n'
            header+='inline constexpr unsigned textures[2][4]={\n'+''.join('{'+','.join('0x%08xU'%v for v in keys[role])+'},\n'for role in ('wall','roof'))+'};\n'
            (a.out/'world_rebuild27_bake_certificates.inc').write_text(header)
        (out/'RECEIPT.json').write_text(json.dumps(receipt,indent=2)+'\n');results.append(receipt)
    cert='// PRIVATE source-policy admission, all three arena arms.\nstatic constexpr Certificate rebuild27_certificates[]={\n'+''.join('{'+','.join('0x%08xU'%v for v in row)+'},\n'for row in rows)+'};\n'
    (a.out/'world_rebuild27_certificates.inc').write_text(cert)
    arena='// PRIVATE; include inside re4dc::house_arena27.\nconstexpr unsigned placements[]={'+','.join(str(v)+'U'for v in sorted(placements))+'};\n'
    arena+='constexpr unsigned textures[][4]={\n'+''.join('{'+','.join('0x%08xU'%v for v in row['key'])+'},\n'for row in texture_rows)+'};\n'
    arena+='constexpr unsigned mesh_identity[3][2]={\n'+''.join('{0x%sU,%dU},\n'%(r['candidate_crc'],r['candidate_bytes'])for r in results)+'};\n'
    (a.out/'world_rebuild27_arena.inc').write_text(arena)
    (a.out/'TEXTURE-UNION.json').write_text(json.dumps(texture_rows,indent=2)+'\n')
    (a.out/'RECEIPT.json').write_text(json.dumps(dict(schema=plan['schema'],tool_sha256=w.sha(Path(__file__).read_bytes()),plan_sha256=w.sha(plan_bytes),arms=results,placements=sorted(placements),union_texture_keys=len(texture_rows),source_core_triangles=407,target_core_triangles=112,complete_house_scope_requires_overview_review=True,qualification='source-only, no timing/appearance acceptance'),indent=2)+'\n')
    (a.out/'RECIPE.txt').write_text('PRIVATE house-only arena; three existing-format packages, diagnostic whitelist required.\nCommand: '+json.dumps(sys.argv)+'\nSource geometry component selection only; original identities/companions retained.\nA exact source attributes, B corrected R4 core, C actual existing baked core.\nNo runtime, staging, production, original asset pruning, gameplay or timing claim.\n')
    (a.out/'SHA256SUMS').write_text(''.join(w.sha(p.read_bytes())+'  '+p.relative_to(a.out).as_posix()+'\n'for p in sorted(a.out.rglob('*'))if p.is_file()))
    print(json.dumps(dict(output=str(a.out),arms=[{k:r[k]for k in ('arm','candidate_sha256','candidate_crc','candidate_bytes','l0_triangles')}for r in results],placements=len(placements),textures=len(texture_rows)),indent=2))

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    sub=ap.add_subparsers(dest='command',required=True)
    p=sub.add_parser('inspect');p.add_argument('--source',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True)
    p.add_argument('--bounds',type=float,nargs=6,default=[-2500,-350,6000,12500,7000,22000]);p.set_defaults(run=inspect)
    p=sub.add_parser('build');p.add_argument('--plan',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.set_defaults(run=build)
    a=ap.parse_args();a.run(a)


if __name__=='__main__':main()