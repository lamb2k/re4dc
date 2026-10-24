"""Public, deliberately awkward fixtures. Contains no recovered game data."""
from pathlib import Path
import json
import struct
import sys

import package as p


def document():
    d=dict(schema=p.SCHEMA,meshes=[],parts=[],meshlets=[],vertices=[],commands=[],
           palette=[0xffffffff],part_lods=[],clusters=[],levels=[],classes=[1,5],
           rules=[[0,0],[0,0],[125,200],[0,600],[0,80],[0,0],[0,0],[0,0]],
           materials=[],placements=[])
    index_size=0
    for pi in range(3):
        base=len(d['vertices']); first=len(d['meshlets'])
        # Vertex3 shares a position but has its own UV/color seam. The first
        # strip contains repeated-index degenerates; odd/even parity is kept.
        verts=[[0,0,0,0,65535,0xffff],[65535,1,0,65535,0,0x801f],
               [0,65535,65535,32768,1,0x7c00],[0,0,0,1,65534,0x83e0],
               [32767,32768,10,12345,54321,0x8001]]
        d['vertices']+=verts
        commands=[dict(pool=list(range(5)),strips=[[0,1,2,2,3,4],[1,4,2]]),
                  dict(pool=[0,2,4],strips=[[0,1,2]])]
        for li,command in enumerate(commands):
            ix=li>0
            if ix and index_size&1:index_size+=1
            sb=sum(1+len(s) for s in command['strips'])
            ids=command['pool']; pos=[verts[k][:3] for k in ids]
            d['meshlets'].append([base,index_size,sb,len(ids),len(command['strips'])|(0x8000 if ix else 0),
                 *[min(v[a] for v in pos) for a in range(3)],*[max(v[a] for v in pos) for a in range(3)]])
            d['commands'].append(command)
            d['levels'].append([first+li,1,0.0 if li==0 else p.f32(37.125+pi)])
            index_size+=sb+(2*len(ids) if ix else 0)
        d['parts'].append([pi*96,64+pi,pi,pi*90,pi,0,first,2,
                          p.f32(-0.1234567),p.f32(-2.75),p.f32(1e-5),p.f32(3e-5)])
        d['part_lods'].append([pi,1])
        d['clusters'].append([0,0,0,65535,65535,65535,2*pi,2])
        d['materials'].append([0x11223344+pi,0x99aabbcc-pi,64<<pi,128,pi,pi,pi,1 if pi==2 else 0])
    for mi,(first,count) in enumerate(((0,2),(2,1))):
        d['meshes'].append([17+mi,0,0x50,5,count,3,first,count,
          p.f32(-1234.125),p.f32(-0.0),p.f32(555.875),
          p.f32(0.025),p.f32(1.25),p.f32(0.00001),
          -1234.125,0.0,555.875,10000.0,90000.0,600.0])
    d['placements']=[
        [0,0,1.0,0.0,0.0,1000.0,0.0,1.0,0.0,0.0,0.0,0.0,1.0,-2000.0],
        [0,1,-1.0,0.25,0.0,-3000.0,0.0,2.0,0.125,4000.0,0.0,0.0,0.5,123.75],
        [1,2,0.0,0.0,1.0,10.0,0.0,1.0,0.0,20.0,-1.0,0.0,0.0,30.0]]
    return d


def basic_files():
    d=document(); mesh=p.serialize_mesh(d); side=p.serialize_policy(d)
    p.decode(mesh,side)
    bound=struct.unpack_from('<I',side,20)[0]
    ids=struct.pack('<4s3I',b'R4ID',1,3,bound)+bytes([7,7,255]);ids+=bytes(-len(ids)%32)
    tc=struct.pack('<4s5I',b'R4TC',1,1,3,bound,p.crc(bytes([0,3,10])))+bytes([0,3,10,0])
    sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'visibility23'))
    import metadata
    sg,_=metadata.build(mesh,side,4)
    return {'ps2-world.re4mesh':mesh,'ps2-world.r4pw':side,'ps2-world.ids':ids,
            'ps2-world.r4tc':tc,'ps2-world.r4sg':sg}


def complete_files(legacy=False):
    """All supported dependency formats; visibility bits allow everything.

    Empty occluders and disabled cones make no geometric hiding assertions.
    This fixture is not a PVS23 certificate and cannot be sold as one.
    """
    import proof_identity as proof
    files=basic_files();d=p.decode(files['ps2-world.re4mesh'],files['ps2-world.r4pw'])
    mesh,side=files['ps2-world.re4mesh'],files['ps2-world.r4pw']
    mc,mb,pc=proof.bindings(mesh,side);room=0x123
    ninst=sum(sum(d['part_lods'][pi][1] for pi in range(d['meshes'][x[0]][6],sum(d['meshes'][x[0]][6:8]))) for x in d['placements'])
    pv=struct.pack('<4s7I3f5I',b'R4PV',1,mc,mb,pc,ninst,1,1,0.,0.,4000.,1,(ninst+7)//8,1,0,0)
    pv+=struct.pack('<Hhhh',0,-10,100,0)+bytes([(1<<ninst)-1]);pv+=bytes(-len(pv)%32)
    files['ps2-world.pvs']=pv
    files['interior.cell']=struct.pack('<4s7I',b'PCL1',room,mc,pc,mb,1,0,0)+struct.pack('<6f2H',-10.,-10.,-10.,10.,10.,10.,0,0)
    files['ps2-world.occl']=struct.pack('<4s7I',b'R4OC',1,mc,mb,pc,0,0,0)
    src=b''.join(struct.pack('<4sI32s',tag,len(files[name]),bytes.fromhex(p.sha(files[name]))) for tag,name in
                 ((b'R4IM','ps2-world.re4mesh'),(b'R4PW','ps2-world.r4pw'),(b'R4ID','ps2-world.ids')))
    grid=struct.pack('<8H',1,0,1,0,1,1,1,0)+struct.pack('<H',0)+bytes(2)+bytes(128)
    grid+=struct.pack('<HHBB',0,0,0,0);grid+=bytes(-len(grid)%4);grid+=struct.pack('<3f',0.,0.,0.)
    if legacy:
        vis=struct.pack('<8H',1,1,1,1,1,1,2400,100)+struct.pack('<hhhBBHH',0,100,0,1,0,0,0)+bytes([1])
        oc=struct.pack('<6HI3H10s',1,1,1,0,0,2400,pc,32,150,100,bytes(10))+bytes(4)
    else:
        vis=struct.pack('<8HI3H6s',1,1,1,1,1,1,2400,100,pc,1,50,100,bytes(6))
        vis+=struct.pack('<hBBhHHH',0,1,1,0,0,0,0)+bytes(4)+bytes([1])
        oc=struct.pack('<6HI4H8s',1,1,1,0,0,2400,pc,32,150,100,0,bytes(8))+bytes(4)
    recs=[];points=bytearray();total=0
    for ji,m in enumerate(d['meshlets']):
        source=[tuple(d['vertices'][v][:3]) for v in p.local_vertices(d,ji)]
        unique=list(dict.fromkeys(source));idx=[unique.index(x) for x in source]
        recs.append(struct.pack('<IHH4f4bI',len(points),len(unique),len(source),0.,0.,0.,1e9,0,0,0,-128,0))
        points.extend(b''.join(struct.pack('<3H',*v) for v in unique));points.extend(bytes(-len(points)%4))
        points.extend(idx);points.extend(bytes(-len(points)%4));total+=len(unique)
    nk=struct.pack('<4s7I',b'SCNK',1,mc,mb,len(recs),total,32,32+32*len(recs))+b''.join(recs)+points
    import tempfile
    sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scenery19'))
    import scdd_compile
    with tempfile.TemporaryDirectory(prefix='b11-fixture-') as td:
        (Path(td)/'ps2-world.re4mesh').write_bytes(mesh);dd,_=scdd_compile.scdd(Path(td))
    cn=struct.pack('<4I',mc,mb,len(d['meshlets']),4)+bytes(256+8*4*len(d['meshlets']));cn+=bytes(-len(cn)%16)
    ps=struct.pack('<4I',mc,mb,len(d['parts']),0)+bytes(4*len(d['parts']));ps+=bytes(-len(ps)%16)
    sections=[(b'SRCB',1,0,src,3,40),(b'GRID',1,3,grid,1,0),(b'VIS\0',1 if legacy else 2,0,vis,1,12),
              (b'OCCL',1 if legacy else 2,0,oc,0,56),(b'SCNK',1,0,nk,len(recs),32),
              (b'SCDD',1,0,dd,len(recs),0),(b'SCCN',1,0,cn,len(recs),16),(b'SCPS',1,0,ps,len(d['parts']),4)]
    body=bytearray();dirs=bytearray();base=64+32*len(sections)
    for tag,ver,flags,data,count,stride in sections:
        body.extend(bytes(-(base+len(body))%16))
        dirs.extend(proof.ROOM_DIR.pack(tag,ver,flags,base+len(body),len(data),count,stride,16,0));body.extend(data)
    body.extend(bytes(-(base+len(body))%16));payload=dirs+body
    files['room.r4rc']=proof.ROOM_HEAD.pack(b'R4RC',1,64,room,len(sections),64+len(payload),0,
        1,1,1000,0,0,-100.,100000.,p.crc(payload),bytes(12))+payload
    shell_body=struct.pack('<IIHHI',*d['materials'][0][:4],0)
    shell_body+=struct.pack('<12fIHHII',0.,0.,0.,10.,10.,0.,0.,0.,0.,1.,0.,0.,0,3,0,0,4)
    shell_body+=b''.join(struct.pack('<3hH2h',*v,65535,u,w) for v,u,w in
                        (((0,0,0),0,0),((10,0,0),2048,0),((0,10,0),0,2048)))
    shell_body+=bytes([3,0,1,2])
    files['far-shell.fsh']=struct.pack('<4s7I',b'FSH1',1 if legacy else 2,1,1,3,4,p.crc(shell_body),room)+shell_body
    report=dict(source='public:synthetic-identity-fixture',source_sha256=p.sha(b'public fixture'),
        inc_sha256=p.sha(b'public synthetic policy'),args={'fixture':True},meshes=len(d['meshes']),
        placements=len(d['placements']),source_triangles=15,re4mesh_bytes=mb,re4mesh_sha256=p.sha(mesh),
        r4pw_bytes=len(side),r4pw_sha256=p.sha(side),level0_triangles=15,summary={'fixture':True})
    files['ps2-world.json']=json.dumps(report,indent=1).encode()
    return files


def converter_files(converter=None):
    """Exercise the unchanged real converter, including an empty coarsest LOD."""
    c=converter or p.crb
    pos=[(x*100.,0.,z*100.) for z in range(5) for x in range(5)]
    tris=[]
    for z in range(4):
        for x in range(4):
            a=z*5+x;b=a+1;e=a+5;f=e+1
            tris.extend([tuple((i,0,i,0) for i in t) for t in ((a,e,b),(b,e,f))])
    src=dict(flags=0,nvtx=len(pos),nparts=1,positions=pos,
        parts=[dict(offset=0,size=0,flags=0,texture=0,alpha=255,strips=[],loose=tris)],
        uv=lambda i:(pos[i][0]/400.,pos[i][2]/400.),normal=lambda i:(0.,1.,0.),
        color=lambda i:(255,255,255,255),bytes=0)
    mesh,_=c.convert_lod([(0x50,False,0,None)],1.0,source=lambda _:src,color_mode='prelit',
        share=True,eps_world=(100.,1000.),min_gain=.99,max_levels=3)
    body=p.PW_PART.pack(0x12345678,0xaabbccdd,64,64,0,2,0,0)
    body+=p.PW_PLACE.pack(0,0,1.,0.,0.,0.,0.,1.,0.,0.,0.,0.,1.,0.)
    side=p.PW_HEAD.pack(b'R4PW',1,1,1,1,p.crc(body),0,0)+body
    return {'ps2-world.re4mesh':mesh,'ps2-world.r4pw':side}


def write(folder,files=None):
    folder=Path(folder);folder.mkdir(parents=True,exist_ok=False)
    for name,data in (files or basic_files()).items():
        (folder/name).write_bytes(data)


if __name__=='__main__':
    write(sys.argv[1])
