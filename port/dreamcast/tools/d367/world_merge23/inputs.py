"""Resolve real room inputs through the existing release dataset precedence."""
from pathlib import Path
import argparse, collections, hashlib, importlib.util, json, os, re, struct, sys, zlib

HERE=Path(__file__).resolve().parent
TOOLS=HERE.parents[1]
sys.path.insert(0,str(HERE.parent/'worldlean'))

def hostpath(path):
    value=str(path)
    if os.name=='nt' and value.startswith('/mnt/c/'):
        return Path('C:/'+value[7:])
    if os.name=='nt' and value.startswith('/root/'):
        return Path('//wsl.localhost/Ubuntu-24.04'+value)
    return Path(value)

def identity(path):
    path=Path(path)
    return dict(path=str(path),bytes=path.stat().st_size,sha256=hashlib.sha256(path.read_bytes()).hexdigest())

def validate_ownership(files,provenance):
    """Bind placement IDs to their original policy despite texture rekeying."""
    base=hostpath(provenance['history']['r4pw'][0]['path'])
    old=base.read_bytes();current=files['r4pw'].read_bytes();ids=files['ids'].read_bytes()
    oh=struct.unpack_from('<4s7I',old);ch=struct.unpack_from('<4s7I',current)
    ih=struct.unpack_from('<4sIII',ids)
    for blob,h in ((old,oh),(current,ch)):
        if h[0]!=b'R4PW' or h[1]!=1 or zlib.crc32(blob[32:])!=h[5]:raise ValueError('Policy CRC mismatch')
        if len(blob)!=32+16*h[3]+52*h[2]:raise ValueError('Policy extent mismatch')
    if ih[0]!=b'R4ID' or ih[1]!=1 or ih[2]!=oh[2] or ih[3]!=oh[5]:raise ValueError('IDs do not bind the source policy')
    if len(ids)<16+ih[2] or ch[2:5]!=oh[2:5]:raise ValueError('Placement/part/mesh counts changed')
    if old[32+16*oh[3]:]!=current[32+16*ch[3]:]:raise ValueError('Placement identities or matrices changed')
    sg=files.get('r4sg')
    if sg:
        b=sg.read_bytes();h=struct.unpack_from('<4s7I',b)
        if h[0]!=b'R4SG' or h[1]!=1 or h[6]!=oh[5] or zlib.crc32(b[32:])!=h[7]:raise ValueError('Strip groups do not bind the original policy')
    return dict(source_policy=identity(base),IDs=identity(files['ids']),
                source_policy_crc=oh[5],current_policy_crc=ch[5],
                placement_records_identical=True,ids_count=ih[2],strip_groups_source_policy_checked=sg is not None)

def release_inputs(room):
    recipe=HERE.parent/'rr/recipe.conf'
    names=re.search(r'^DATA="([^"]+)"',recipe.read_text(),re.M)[1].split(',')
    source=HERE.parent/'test11/t11-fix.py'
    spec=importlib.util.spec_from_file_location('world_merge23_t11',source)
    mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
    base=Path(mod.PAYLOAD_ROOT)/'tree'
    result={};history={}
    for ext in ('re4mesh','r4pw','r4sg','ids'):
        dest=f'dc/native/{room}/ps2-world.{ext}'
        path=base/dest
        seq=[dict(dataset='payload',path=str(path))]
        for name in names:
            if dest in mod.DATA[name]:
                path=Path(mod.DATA[name][dest]);seq.append(dict(dataset=name,path=str(path)))
        if path.exists(): result[ext]=path
        elif ext in ('re4mesh','r4pw'): raise FileNotFoundError(path)
        history[ext]=seq
    return result,dict(recipe=identity(recipe),dataset_order=names,history=history)

def census(room,files,provenance):
    import sgprice
    data=sgprice.load(files['re4mesh'],files['r4pw'],files.get('r4sg'))
    pkg=data['p'];usage=collections.Counter(pl['mesh'] for pl in pkg.placements)
    return dict(room=room,files={k:identity(v) for k,v in files.items()},provenance=provenance,
                placements=len(pkg.placements),meshes=pkg.nmesh,parts=pkg.npart,meshlets=pkg.nlet,
                clusters=pkg.ncl,levels=pkg.nlv,vertices=pkg.nvert,
                one_off_placements=sum(usage[x['mesh']]==1 for x in pkg.placements),
                instance_multiplicity=dict(collections.Counter(usage.values())),
                passes=dict(collections.Counter(x['pass_'] for x in pkg.pmeta)),
                lod_level_counts=dict(collections.Counter(x['level_count'] for x in pkg.clusters)))

if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--resolve',type=Path)
    ap.add_argument('--census',type=Path)
    ap.add_argument('--output',type=Path)
    args=ap.parse_args()
    if args.resolve:
        assert os.name!='nt','Resolve the existing Linux stager DATA in WSL.'
        rows={}
        for room in ('r100','r101','r103'):
            files,prov=release_inputs(room)
            rows[room]=dict(files={k:identity(p) for k,p in files.items()},provenance=prov)
        args.resolve.parent.mkdir(parents=True,exist_ok=True)
        with args.resolve.open('x') as f:json.dump(rows,f,indent=2)
        print(json.dumps(dict(output=str(args.resolve),rooms=list(rows))))
    elif args.census:
        source=json.loads(args.census.read_text())
        rows=[census(room,{k:hostpath(v['path']) for k,v in row['files'].items()},row['provenance']) for room,row in source.items()]
        if args.output:
            with args.output.open('x') as f:json.dump(rows,f,indent=2)
        print(json.dumps(rows,indent=2))
    else:ap.error('Choose --resolve or --census.')
