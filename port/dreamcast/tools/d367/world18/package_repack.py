"""Repack private Blender cluster substitutions through the existing stripifier/meshlet packer.

Retains all material, part, cluster and source mesh identities. Unmodified levels
must preserve the complete oriented six-u16-corner triangle multiset. This is a
host experiment writer, not a stager or recipe change.
"""
from pathlib import Path
import argparse,collections,json,struct,sys,hashlib
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parents[1]))
import mesh_lod
from package_io import read,write,let_corners,INDEXED

def triangles(p,lv):
    out=[]
    for li in range(lv[0],lv[0]+lv[1]):
        corners,strips=let_corners(p,p['lets'][li])
        for s in strips:
            for k in range(len(s)-2):
                ix=(s[k],s[k+1],s[k+2]) if k%2==0 else (s[k+2],s[k+1],s[k])
                t=tuple(tuple(p['verts'][corners[i]]) for i in ix)
                if len({v[:3] for v in t})==3:out.append(t)
    return out

def canonical(ts):return collections.Counter(min(t,t[1:]+t[:1],t[2:]+t[:2]) for t in ts)
def split(s):
    start=0
    while len(s)-start>255:
        yield s[start:start+254];start+=252
    if len(s)-start>=3:yield s[start:]

def source_strips(p,lv):
    for li in range(lv[0],lv[0]+lv[1]):
        corners,strips=let_corners(p,p['lets'][li])
        for s in strips:yield [tuple(p['verts'][corners[k]]) for k in s]

def ordered_chunks(strips):
    chunk=[];keys=set()
    for s in strips:
        if chunk and len(keys|set(s))>256:yield chunk;chunk=[];keys=set()
        chunk.append(s);keys.update(s)
    if chunk:yield chunk

def main():
    ap=argparse.ArgumentParser();ap.add_argument('source',type=Path);ap.add_argument('changes',type=Path);ap.add_argument('output',type=Path)
    ap.add_argument('--preserve-source-strip-order',action='store_true')
    a=ap.parse_args();src=read(a.source.read_bytes());chg=json.loads(a.changes.read_text())['changes']
    out=dict(meshes=src['meshes'],parts=[],lets=[],verts=[],strip=bytearray(),pal=src['pal'],plods=src['plods'],clusters=[],levels=[])
    for pi,part in enumerate(src['parts']):
        firstlet=len(out['lets']);pool={};fv=len(out['verts']);newverts=[]
        fc,cc=src['plods'][pi]
        for ci in range(fc,fc+cc):
            c=src['clusters'][ci];fl=len(out['levels']);replacement=chg.get(str(ci))
            for level in range(c[7]):
                lv=src['levels'][c[6]+level]
                ts=([tuple(tuple(k) for k in t) for t in replacement['triangles']]
                    if replacement and replacement['level']==level else triangles(src,lv))
                changed=replacement and replacement['level']==level
                strips=([sub for s in source_strips(src,lv) for sub in split(s)] if a.preserve_source_strip_order and not changed
                        else [sub for s in mesh_lod.stripify(ts) for sub in split(s)])
                chunks=list(ordered_chunks(strips)) if a.preserve_source_strip_order else mesh_lod.pack_meshlets(strips,256,lambda c:c[:3])
                lm=len(out['lets'])
                for chunk in chunks:
                    keys=list(dict.fromkeys(k for s in chunk for k in s));local={k:i for i,k in enumerate(keys)}
                    offsets=[]
                    for k in keys:
                        if k not in pool:pool[k]=len(newverts);newverts.append(k)
                        offsets.append(pool[k])
                    assert len(newverts)<=65536
                    if len(out['strip'])&1:out['strip'].append(0)
                    fs=len(out['strip']);out['strip'].extend(struct.pack('<%dH'%len(keys),*offsets));ss=len(out['strip'])
                    for s in chunk:out['strip'].append(len(s));out['strip'].extend(local[k] for k in s)
                    lo=[min(k[j] for k in keys) for j in range(3)];hi=[max(k[j] for k in keys) for j in range(3)]
                    out['lets'].append([fv,fs,len(out['strip'])-ss,len(keys),len(chunk)|INDEXED,*lo,*hi])
                out['levels'].append([lm,len(out['lets'])-lm,lv[2]])
            out['clusters'].append(c[:6]+[fl,c[7]])
        out['verts'].extend(newverts);out['parts'].append(part[:6]+[firstlet,len(out['lets'])-firstlet]+part[8:])
    blob=write(out);check=read(blob);same=changed=0
    for ci,c in enumerate(src['clusters']):
        for level in range(c[7]):
            aa=triangles(src,src['levels'][c[6]+level]);bb=triangles(check,check['levels'][c[6]+level])
            if str(ci) in chg and chg[str(ci)]['level']==level:
                expected=[tuple(tuple(k) for k in t) for t in chg[str(ci)]['triangles']]
                assert canonical(bb)==canonical(expected),(ci,level,'changed triangle mismatch');changed+=1
            else:assert canonical(aa)==canonical(bb),(ci,level,'unmodified triangle mismatch');same+=1
            if a.preserve_source_strip_order and not (str(ci) in chg and chg[str(ci)]['level']==level):
                assert aa==bb,(ci,level,'ordered triangle mismatch')
    a.output.write_bytes(blob)
    report=dict(source_sha256=hashlib.sha256(a.source.read_bytes()).hexdigest(),output_sha256=hashlib.sha256(blob).hexdigest(),
                bytes_before=a.source.stat().st_size,bytes_after=len(blob),unchanged_levels_verified=same,changed_levels_verified=changed,
                source_identity_tables_unchanged=True,diagnostic_only=True)
    a.output.with_suffix('.repack.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))

if __name__=='__main__':main()
