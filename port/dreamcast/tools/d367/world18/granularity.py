"""Lossless source-path culling-granularity trial; private inputs/outputs only.

Merge at most factor adjacent meshlets inside one original cluster/LOD/part,
subject to the renderer's 256-local-corner limit. Keep the complete source pool
and exact ordered strip corner records. With R4SG, merge factor consecutive
source group records; retain the existing four-record format with empty padding.
No runtime, release recipe, source activation or placement changes.
"""
from pathlib import Path
import argparse, collections, copy, hashlib, json, struct, sys, zlib

def sha(b): return hashlib.sha256(b).hexdigest()

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--tools', type=Path, required=True)
    ap.add_argument('--source', type=Path, required=True)
    ap.add_argument('--output', type=Path, required=True)
    ap.add_argument('--factor', type=int, choices=(2,4), required=True)
    a=ap.parse_args();sys.path.insert(0,str(a.tools))
    from package_io import read, write, let_corners, INDEXED
    blob=(a.source/'ps2-world.re4mesh').read_bytes();p=read(blob)
    side=(a.source/'ps2-world.r4pw').read_bytes()
    sgpath=a.source/'ps2-world.r4sg';sgh=None;oldsg=None
    if sgpath.exists():
        b=sgpath.read_bytes();sgh=struct.unpack_from('<4s7I',b)
        assert sgh[:4]==(b'R4SG',1,len(p['lets']),4)
        assert sgh[4:7]==(struct.unpack_from('<I',blob,12)[0],len(blob),struct.unpack_from('<I',side,20)[0])
        assert zlib.crc32(b[32:])==sgh[7]
        oldsg=[list(struct.iter_unpack('<8H',b[32+i*64:32+(i+1)*64])) for i in range(len(p['lets']))]
    parsed=[let_corners(p,m) for m in p['lets']]
    groups=[]
    for li,(corners,strips) in enumerate(parsed):
        if oldsg is None: groups.append([strips]);continue
        byend={};end=0
        for j,s in enumerate(strips):end+=1+len(s);byend[end]=j+1
        cur=0;gs=[];prev=0
        for rec in oldsg[li]:
            if rec[6]==prev:continue
            stop=byend[rec[6]];gs.append(strips[cur:stop]);cur=stop;prev=rec[6]
        assert cur==len(strips);groups.append(gs)
    out=copy.deepcopy(p);out.update(lets=[],strip=bytearray(),levels=[],parts=[],clusters=[])
    sgbytes=bytearray();mapping=[];hist=collections.Counter();covered=[]
    def emit(ids):
        corners=list(dict.fromkeys(v for i in ids for v in parsed[i][0]))
        assert len(corners)<=256
        fv=min(corners);assert max(corners)-fv<=65535
        local={v:i for i,v in enumerate(corners)}
        streams=[[[local[parsed[i][0][k]] for k in st] for st in group] for i in ids for group in groups[i]]
        merged=[sum(streams[j:j+a.factor],[]) for j in range(0,len(streams),a.factor)] if oldsg else streams
        if oldsg:assert len(merged)<=4
        if len(out['strip'])&1:out['strip'].append(0)
        fs=len(out['strip']);out['strip'].extend(struct.pack('<%dH'%len(corners),*[v-fv for v in corners]))
        s0=len(out['strip']);sc=0;records=[]
        for group in merged:
            ks=[k for st in group for k in st]
            for st in group:out['strip'].append(len(st));out['strip'].extend(st);sc+=1
            if oldsg:
                xyz=[p['verts'][corners[k]][:3] for k in ks]
                lo=[min(v[j] for v in xyz) for j in range(3)];hi=[max(v[j] for v in xyz) for j in range(3)]
                records.append([*lo,*hi,len(out['strip'])-s0,min(ks)|(max(ks)<<8)])
        sb=len(out['strip'])-s0
        if oldsg:
            assert sb<=65535
            records.extend([[0,0,0,0,0,0,sb,1]]*(4-len(records)))
            sgbytes.extend(b''.join(struct.pack('<8H',*r) for r in records))
        lo=[min(p['lets'][i][5+j] for i in ids) for j in range(3)]
        hi=[max(p['lets'][i][8+j] for i in ids) for j in range(3)]
        out['lets'].append([fv,fs,sb,len(corners),sc|INDEXED,*lo,*hi])
        mapping.append(ids);hist[len(ids)]+=1;covered.extend(ids)
    for pi,part in enumerate(p['parts']):
        first=len(out['lets']);fc,cc=p['plods'][pi]
        for ci in range(fc,fc+cc):
            c=p['clusters'][ci];fl=len(out['levels'])
            for lv in p['levels'][c[6]:c[6]+c[7]]:
                lm=len(out['lets']);batch=[];keys=set()
                for li in range(lv[0],lv[0]+lv[1]):
                    add=set(parsed[li][0])
                    if batch and (len(batch)>=a.factor or len(keys|add)>256 or max(keys|add)-min(keys|add)>65535):
                        emit(batch);batch=[];keys=set()
                    batch.append(li);keys.update(add)
                if batch:emit(batch)
                out['levels'].append([lm,len(out['lets'])-lm,lv[2]])
            out['clusters'].append(c[:6]+[fl,c[7]])
        out['parts'].append(part[:6]+[first,len(out['lets'])-first]+part[8:])
    assert sorted(covered)==list(range(len(p['lets']))), 'duplicate or orphan meshlet'
    newblob=write(out);q=read(newblob)
    def level_stream(obj,lv):
        return [[obj['verts'][corners[k]] for k in s] for li in range(lv[0],lv[0]+lv[1])
                for corners,ss in [let_corners(obj,obj['lets'][li])] for s in ss]
    for ci,c in enumerate(p['clusters']):
        for k in range(c[7]):
            assert level_stream(p,p['levels'][c[6]+k])==level_stream(q,q['levels'][q['clusters'][ci][6]+k]),(ci,k)
    assert q['meshes']==p['meshes'] and q['verts']==p['verts'] and q['pal']==p['pal'] and q['plods']==p['plods']
    assert all(x[:6]+x[8:]==y[:6]+y[8:] for x,y in zip(p['parts'],q['parts']))
    assert p['clusters']==q['clusters']
    a.output.mkdir(parents=True,exist_ok=False)
    for f in a.source.glob('ps2-world.*'):
        if f.suffix not in ('.re4mesh','.r4sg'):(a.output/f.name).write_bytes(f.read_bytes())
    (a.output/'ps2-world.re4mesh').write_bytes(newblob)
    if oldsg:
        h=struct.pack('<4s7I',b'R4SG',1,len(q['lets']),4,struct.unpack_from('<I',newblob,12)[0],len(newblob),sgh[6],zlib.crc32(sgbytes))
        (a.output/'ps2-world.r4sg').write_bytes(h+sgbytes)
    before_groups=sum(len(gs) for gs in groups) if oldsg else len(p['lets'])
    after_groups=sum(1 for r in struct.iter_unpack('<8H',sgbytes) if (r[7]&255)<=(r[7]>>8)) if oldsg else len(q['lets'])
    report=dict(requested_factor=a.factor,meshlets_before=len(p['lets']),meshlets_after=len(q['lets']),
        achieved_meshlet_factor=len(p['lets'])/len(q['lets']),merge_batch_histogram=dict(hist),
        culling_units_before=before_groups,culling_units_after=after_groups,achieved_culling_unit_factor=before_groups/after_groups,
        mesh_bytes_before=len(blob),mesh_bytes_after=len(newblob),groups_bytes_before=sgpath.stat().st_size if oldsg else 0,
        groups_bytes_after=len(sgbytes)+32 if oldsg else 0,source_mesh_sha256=sha(blob),output_mesh_sha256=sha(newblob),
        all_ordered_six_u16_strip_corners_equal=True,all_source_identity_material_placement_tables_equal=True,
        all_source_global_vertex_records_equal=True,verified_cluster_levels=len(q['levels']),
        limitation='256 local corners and original cluster/LOD/part boundaries cap neighbour merges; four SG records retained with empty padding',
        files={f.name:sha(f.read_bytes()) for f in sorted(a.output.glob('ps2-world.*'))},source_meshlets_per_output=mapping)
    (a.output/'granularity.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k!='source_meshlets_per_output'},indent=2))

if __name__=='__main__':main()
