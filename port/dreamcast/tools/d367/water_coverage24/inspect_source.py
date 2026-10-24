#!/usr/bin/env python3
"""Bounded read-only correspondence evidence for early PS2 water paths.
Does not classify a material as water, emit assets, or grant GC-ASSET acceptance.
"""
import argparse, collections, hashlib, importlib.util, json, math, pathlib, re, resource, signal, struct, sys, time
sys.dont_write_bytecode = True

def digest(data): return hashlib.sha256(data).hexdigest()
def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module); return module

def pin(path):
    data = path.read_bytes()
    return {'path': str(path), 'bytes': len(data), 'sha256': digest(data)}

def inspect_obj(path):
    """Streaming OBJ material/geometry census. Only positions are retained."""
    vertices = []; groups = []; group = None; material = None
    def bucket():
        return {'triangles': 0, 'horizontal_area_mm2': 0., 'total_area_mm2': 0.,
                'min': [math.inf]*3, 'max': [-math.inf]*3, 'horizontal_y_min': math.inf, 'horizontal_y_max': -math.inf}
    with path.open() as stream:
        for line in stream:
            if line.startswith('v '):
                vertices.append(tuple(float(v)*100 for v in line.split()[1:4]))
            elif line.startswith('g '):
                match = re.fullmatch(r'PS2SCENARIO#SMD_(\d+)#SMX_(\d+)#TYPE_([0-9A-Fa-f]+)#BIN_(\d+)#(?:(COLOR|NORMAL)#)?', line[2:].strip())
                if not match: raise ValueError('unsupported OBJ group')
                group = {'placement': int(match[1]), 'smx': int(match[2]), 'status': int(match[3],16),
                         'bin': int(match[4]), 'kind': match[5], 'materials': {}}
                groups.append(group)
            elif line.startswith('usemtl '): material = line.split()[1]
            elif line.startswith('f '):
                if group is None or material is None: raise ValueError('face before group/material')
                indices = [int(v.split('/')[0]) - 1 for v in line.split()[1:]]
                if len(indices)!=3 or any(v<0 or v>=len(vertices) for v in indices): raise ValueError('unsupported face')
                a,b,c = [vertices[v] for v in indices]
                u = [b[i]-a[i] for i in range(3)]; v = [c[i]-a[i] for i in range(3)]
                normal = (u[1]*v[2]-u[2]*v[1], u[2]*v[0]-u[0]*v[2], u[0]*v[1]-u[1]*v[0])
                area2 = math.sqrt(sum(x*x for x in normal)); row=group['materials'].setdefault(material,bucket()); row['triangles']+=1
                row['total_area_mm2'] += area2*.5
                for p in (a,b,c):
                    for i in range(3): row['min'][i]=min(row['min'][i],p[i]); row['max'][i]=max(row['max'][i],p[i])
                if area2 and abs(normal[1])/area2>=.999:
                    row['horizontal_area_mm2']+=area2*.5
                    row['horizontal_y_min']=min(row['horizontal_y_min'],a[1],b[1],c[1]); row['horizontal_y_max']=max(row['horizontal_y_max'],a[1],b[1],c[1])
    for g in groups:
        for r in g['materials'].values():
            for key in ('horizontal_y_min','horizontal_y_max'):
                if not math.isfinite(r[key]):r[key]=None
    return groups

def inspect_smd(path, ps2bin):
    d=path.read_bytes(); magic,n,binbase,tplbase,unused=struct.unpack_from('<HHIII',d)
    if magic!=0x40 or not 0<n<4096 or 16+64*n>len(d):raise ValueError('unsupported SMD header')
    rows=[]
    for i in range(n):
        f=struct.unpack_from('<12fBBBBIII',d,16+64*i)
        if not all(math.isfinite(x) for x in f[:12]):raise ValueError('nonfinite placement')
        rows.append({'placement':i,'position':f[:3],'angles':f[4:7],'scale':f[8:11], 'bin':f[12],'tpl':f[13],'smx':f[15],'status':f[17],
                     'placement_span_sha256':digest(d[16+64*i:16+64*(i+1)])})
    nb=max(r['bin'] for r in rows)+1
    if not 16+64*n<=binbase<=len(d)-4*nb:raise ValueError('BIN table bounds')
    starts=[binbase+struct.unpack_from('<I',d,binbase+4*i)[0] for i in range(nb)]
    cuts=sorted(set(starts+[tplbase,len(d)])); bins={}
    for bid in sorted(set(r['bin'] for r in rows)):
        start=starts[bid]
        if not binbase+4*nb<=start<tplbase:raise ValueError('BIN outside region')
        end=min(x for x in cuts if x>start); raw=d[start:end]
        external=path.parent/(path.stem+'_BIN')/('%04d.BIN'%bid)
        ext=external.read_bytes()
        if raw!=ext:raise ValueError('extracted BIN differs from SMD member '+str(bid))
        model=ps2bin.parse_bin(raw)
        points=[tuple(v['p'][i]*s['factor'] for i in range(3)) for node in model.nodes for s in node['segments'] for v in s['verts']]
        bins[bid]={'offset':start,'bytes':len(raw),'sha256':digest(raw),'materials':model.materials,
                   'vertices':len(points),'bbox_local':[list(map(min,zip(*points))),list(map(max,zip(*points)))] if points else None}
    t=tplbase+struct.unpack_from('<I',d,tplbase)[0]
    tpl=path.with_suffix('.TPL').read_bytes()
    if d[t:t+len(tpl)]!=tpl:raise ValueError('standalone TPL differs from embedded SMD TPL')
    return {'header':{'magic':magic,'placements':n,'bin_table':binbase,'tpl_table':tplbase},'embedded_tpl':{'offset':t,'bytes':len(tpl),'sha256':digest(tpl)},'placements':rows,'bins':bins}

def main():
    p=argparse.ArgumentParser(); p.add_argument('--source',type=pathlib.Path,required=True);p.add_argument('--bindings',type=pathlib.Path,required=True);p.add_argument('--out',type=pathlib.Path,required=True);p.add_argument('--iso',type=pathlib.Path,required=True)
    a=p.parse_args(); resource.setrlimit(resource.RLIMIT_AS,(256*1024*1024,256*1024*1024));signal.alarm(120)
    if a.out.exists():raise ValueError('output exists')
    start=time.monotonic(); bindings=json.loads(a.bindings.read_text()); out={'schema':'early-water-source-correspondence-v1','bindings':pin(a.bindings),'source':{},'rooms':{}}
    for name in ('src/game/espgen45.cpp','src/game/water_ps2_table.inc','src/game/water_ps2_ext.inc','src/st1/r100.cpp','src/st1/r107.cpp','src/st1/r10a.cpp','port/dreamcast/tools/ps2_bin.py'):
        out['source'][name]=pin(a.source/name)
    B=load('early_water_ps2_bin',a.source/'port/dreamcast/tools/ps2_bin.py')
    index=B.afs_index(a.iso)
    out['iso']={'path':str(a.iso),'bytes':a.iso.stat().st_size,'full_iso_hashed':False}

    for room in ('r100','r107','r10a'):
        refs=bindings['rooms'][room]['world_material_inputs']; paths={pathlib.Path(r['path']).suffix:pathlib.Path(r['path']) for r in refs}
        for ref in refs:
            actual=pin(pathlib.Path(ref['path']))
            if actual['sha256']!=ref['sha256'] or actual['bytes']!=ref['bytes']:raise ValueError('bound source drift')
        smd=paths['.SMD']; obj=smd.with_suffix('.scenario.obj')
        member=B.afs_read(a.iso,room+'.dat',index)
        if digest(member)!=bindings['rooms'][room]['member']['sha256']:raise ValueError('original PS2 room member changed')
        original_smd=[(k,v) for k,tag,v in B.dat_entries(member) if tag=='SMD']
        if len(original_smd)!=1 or original_smd[0][1]!=smd.read_bytes():raise ValueError('input SMD differs from actual PS2 DAT member')
        geometry=inspect_obj(obj); source=inspect_smd(smd,B)
        for group in geometry:
            row=source['placements'][group['placement']]
            if row['bin']!=group['bin'] or row['smx']!=group['smx'] or row['status']!=group['status']:raise ValueError('OBJ/SMD mapping drift')
        out['rooms'][room]={'member':bindings['rooms'][room]['member'],'world_pins':refs,'obj':pin(obj),'smd':source,'geometry':geometry}
        print(room,'placements',len(source['placements']),'bins',len(source['bins']),'groups',len(geometry),file=sys.stderr)
    out['elapsed_seconds']=time.monotonic()-start;out['interpretation']='Source geometry/material correspondence only. Horizontal areas and alpha are candidate evidence, never semantic water proof. No assets emitted or runtime/guest/console acceptance.'
    a.out.write_text(json.dumps(out,indent=2,allow_nan=False)+'\n');print(json.dumps({'sha256':digest(a.out.read_bytes()),'bytes':a.out.stat().st_size,'elapsed_seconds':out['elapsed_seconds']}))
if __name__=='__main__':main()
