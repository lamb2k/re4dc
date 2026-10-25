"""Known-format identity adapters, NOT visibility/collision certification.

Every caller requires byte identity of the complete input bundle. These adapters
validate dependencies, parse/repack records, and recompute checksums; existing
geometric proofs and external SAT provenance are inherited without endorsement.
"""
import math
from pathlib import Path
import struct
import sys
import tempfile

from package import crc,finite,local_vertices,require,sha

ROOM_HEAD=struct.Struct('<4sHHIIIIHHIiiffI12s')
ROOM_DIR=struct.Struct('<4sHHIIIIII')
ROOM_SECTIONS={b'SRCB':(1,),b'GRID':(1,),b'VIS\0':(1,2),b'OCCL':(1,2),
               b'SCNK':(1,),b'SCDD':(1,),b'SCCN':(1,),b'SCPS':(1,)}


class Records:
    def __init__(self,data,label):
        self.data=data; self.at=0; self.out=bytearray(); self.label=label

    def row(self,fmt):
        s=struct.Struct(fmt)
        require(s.size <= len(self.data)-self.at,self.label+' truncated record')
        values=s.unpack_from(self.data,self.at);self.at+=s.size
        finite([v for v in values if isinstance(v,float)],self.label)
        self.out.extend(s.pack(*values))
        return values

    def opaque(self,n):
        require(0<=n<=len(self.data)-self.at,self.label+' payload extent')
        value=self.data[self.at:self.at+n]; self.at+=n; self.out.extend(value)
        return value

    def pad(self,alignment):
        padding=self.opaque(-self.at%alignment)
        require(not any(padding),self.label+' nonzero padding')

    def finish(self):
        require(self.at==len(self.data),self.label+' extra/unknown bytes')
        require(bytes(self.out)==self.data,self.label+' reserialization changed payload')
        return bytes(self.out)


def bindings(mesh,side):
    import provenance
    return struct.unpack_from('<I',mesh,12)[0],len(mesh),provenance.policy_crc(mesh,side)[0]


def pvs(data,doc,mesh,side):
    r=Records(data,'R4PV');h=r.row('<4s7I3f5I')
    mc,mb,pc=bindings(mesh,side)
    require(h[:5]==(b'R4PV',1,mc,mb,pc),'R4PV stale identity')
    _,_,_,_,_,ni,nx,nz,x0,z0,cell,ns,nb,nc,p0,p1=h
    actual=sum(sum(doc['part_lods'][pi][1] for pi in range(doc['meshes'][p[0]][6],
               sum(doc['meshes'][p[0]][6:8]))) for p in doc['placements'])
    require(0<ni<65536 and ni==actual and nx and nz and nx*nz<=65536 and ns<=65535 and
        nb==(ni+7)//8 and nc<=nx*nz and cell>0 and not(p0 or p1) and
        math.isfinite(x0+nx*cell) and math.isfinite(z0+nz*cell),'R4PV layout/instances')
    require(len(data)<=262144 and len(data)%32==0,'R4PV file extent')
    valid=0
    for _ in range(nx*nz):
        index,lo,hi,pad=r.row('<Hhhh')
        require(not pad and (index==65535 or (index<ns and lo<=hi)),'R4PV cell')
        valid+=index!=65535
    require(valid==nc,'R4PV cell count')
    for _ in range(ns):
        bits=r.opaque(nb)
        if ni%8:require(bits[-1]>>(ni%8)==0,'R4PV out-of-range bits')
    r.pad(32)
    struct.pack_into('<3I',r.out,8,mc,mb,pc)
    return r.finish()


def pcl(data,doc,mesh,side):
    r=Records(data,'PCL1');h=r.row('<4s7I');mc,mb,pc=bindings(mesh,side)
    require(h[0]==b'PCL1' and h[2:5]==(mc,pc,mb) and not h[7],'PCL1 stale identity')
    for _ in range(h[5]):
        c=r.row('<6f2H')
        require(all(a<=b for a,b in zip(c[:3],c[3:6])) and c[6]+c[7]<=h[6] and c[7]<=24,'PCL1 cell bounds/portals')
    for _ in range(h[6]):
        p=r.row('<I5f');require(p[0]<3 and p[2]<=p[3] and p[4]<=p[5],'PCL1 portal')
    struct.pack_into('<3I',r.out,8,mc,pc,mb)
    return r.finish()


def occluders(data,doc,mesh,side):
    r=Records(data,'R4OC');h=r.row('<4s7I');mc,mb,pc=bindings(mesh,side)
    require(h[:5]==(b'R4OC',1,mc,mb,pc) and h[6:]==(0,0),'R4OC stale identity')
    for _ in range(h[5]):r.row('<16f')
    struct.pack_into('<3I',r.out,8,mc,mb,pc)
    return r.finish()


def far_shell(data):
    """Separate pre-existing world representation; no R4IM binding is invented."""
    r=Records(data,'FSH1');h=r.row('<4s7I')
    magic,version,ng,nm,nv,nb,bound,room=h
    require(magic==b'FSH1' and version in (1,2) and bound==crc(data[32:]),'FSH1 identity/CRC')
    for _ in range(nm):
        key,fnv,w,height,reserved=r.row('<IIHHI')
        require(w and height and not reserved,'FSH1 material')
    groups=[r.row('<12fIHHII') for _ in range(ng)]
    vertices=[r.row('<3hH2h') for _ in range(nv)]
    strips=r.opaque(nb);first_vertex=first_strip=0
    for g in groups:
        fv,vc,material,fs,sb=g[12:]
        require(all(a<=b for a,b in zip(g[:3],g[3:6])) and g[9]>0 and
            fv==first_vertex and 0<vc<=256 and fv+vc<=nv and fs==first_strip and fs+sb<=nb and
            (material&0x3fff)<nm and (version==2 or material<0x4000),'FSH1 group')
        at=fs
        while at<fs+sb:
            n=strips[at];at+=1
            require(n>=3 and n<=fs+sb-at and all(x<vc for x in strips[at:at+n]),'FSH1 strip')
            at+=n
        first_vertex+=vc;first_strip+=sb
    require(first_vertex==nv and first_strip==nb,'FSH1 table coverage')
    struct.pack_into('<I',r.out,24,crc(r.out[32:]))
    return r.finish()


def srcb(data,count,files):
    r=Records(data,'SRCB');seen=set()
    mapping={b'R4IM':'ps2-world.re4mesh',b'R4PW':'ps2-world.r4pw',b'R4ID':'ps2-world.ids'}
    for _ in range(count):
        tag,size,digest=r.row('<4sI32s')
        require(tag==b'SAT\0' or tag in mapping,'unsupported SRCB source tag')
        if tag in mapping:
            require(tag not in seen,'duplicate SRCB world identity');seen.add(tag)
            name=mapping[tag]
            require(name in files and len(files[name])==size and sha(files[name])==digest.hex(),'SRCB stale '+name)
            struct.pack_into('<I32s',r.out,r.at-36,len(files[name]),bytes.fromhex(sha(files[name])))
    return r.finish(),seen


def grid(data,w,h):
    r=Records(data,'GRID');np,ns,nc,nw,bw,bh,nblock,pad=r.row('<8H')
    require(not pad and bw==(w+7)//8 and bh==(h+7)//8,'GRID dimensions')
    for _ in range(bw*bh):require(r.row('<H')[0] in (65535,) or
        struct.unpack_from('<H',r.data,r.at-2)[0]<nblock,'GRID block reference')
    r.pad(4)
    for _ in range(nblock*64):
        x=r.row('<H')[0];require(x==65535 or x<nc,'GRID combo reference')
    for _ in range(nc):
        floor,first,count,pad=r.row('<HHBB')
        require(floor<np and first+count<=nw and not pad,'GRID combo')
    r.pad(4)
    for _ in range(np):r.row('<3f')
    for _ in range(ns):r.row('<6h')
    for _ in range(nw):require(r.row('<H')[0]<ns,'GRID wall reference')
    return r.finish()


def vis(data,version,w,h,policy_crc):
    r=Records(data,'VIS')
    if version==2:
        vw,vh,div,nrow,nb,ntgt,rng,span,bound,ncam,step,espan,pad=r.row('<8HI3H6s')
        require(bound==policy_crc and not any(pad) and step>0 and espan>=step,'VIS identity/eye bands')
    else:
        vw,vh,div,nrow,nb,ntgt,rng,span=r.row('<8H');ncam=0
    require(div and vw==(w+div-1)//div and vh==(h+div-1)//div and nb==(ntgt+7)//8,'VIS dimensions')
    for _ in range(vw*vh):
        if version==2:
            eye,ne,nband,band,fc,ft,pad=r.row('<hBBhHHH')
            require(not pad and (fc==65535 or (ne and fc+ne<=ncam and ft+nband<=ntgt)),'VIS camera cell')
        else:
            elo,ehi,band,nband,pad,row,ft=r.row('<hhhBBHH')
            require(not pad and (row==65535 or (row<nrow and ft+nband<=ntgt)),'VIS v1 cell')
    if version==2:
        for _ in range(ncam):require(r.row('<H')[0]<nrow,'VIS row reference')
        r.pad(4)
    r.opaque(nrow*nb)  # Existing proof bits; no new visibility assertion.
    if version==2:struct.pack_into('<I',r.out,16,policy_crc)
    return r.finish()


def occl(data,version,w,h,policy_crc,placements):
    r=Records(data,'OCCL')
    if version==2:
        vw,vh,div,no,nl,rng,bound,cap,spacing,inset,npool,pad=r.row('<6HI4H8s')
    else:
        vw,vh,div,no,nl,rng,bound,cap,spacing,inset,pad=r.row('<6HI3H10s');npool=0
    require(bound==policy_crc and not any(pad),'OCCL stale policy/padding')
    require(div and vw==(w+div-1)//div and vh==(h+div-1)//div,'OCCL dimensions')
    for _ in range(no):
        v=r.row('<13fbBH')
        require(v[12]>=0 and v[13] in (-1,1),'OCCL thickness/side')
        require((version==2 and v[14]>0 and v[15]+v[14]<=npool) or
                (version==1 and v[14:]==(0,0)),'OCCL source range')
    for _ in range(vw*vh):
        first,count,pad=r.row('<HBB');require(first+count<=nl and count<=cap and not pad,'OCCL cell')
    for _ in range(nl):require(r.row('<H')[0]<no,'OCCL occluder reference')
    r.pad(4)
    for _ in range(npool):require(r.row('<H')[0] in placements,'OCCL source placement')
    if version==2:r.pad(4)
    struct.pack_into('<I',r.out,12,policy_crc)
    return r.finish()


def scnk(data,doc,mesh):
    r=Records(data,'SCNK');head=r.row('<4s7I');mc=struct.unpack_from('<I',mesh,12)[0]
    require(head[:5]==(b'SCNK',1,mc,len(mesh),len(doc['meshlets'])) and
            head[6:]==(32,32+32*head[4]),'SCNK identity/layout')
    recs=[r.row('<IHH4f4bI') for _ in range(head[4])];total=0
    for ji,rec in enumerate(recs):
        off,np,nv,*_=rec
        require(r.at==head[7]+off and 0<np<=nv==doc['meshlets'][ji][3] and not rec[-1] and rec[6]>=0,'SCNK record')
        points=[r.row('<3H') for _ in range(np)];r.pad(4)
        indices=r.opaque(nv);r.pad(4)
        require(all(k<np for k in indices),'SCNK point reference')
        require([list(points[k]) for k in indices]==[doc['vertices'][v][:3] for v in local_vertices(doc,ji)],'SCNK point map stale')
        total+=np
    require(total==head[5],'SCNK point count')
    struct.pack_into('<2I',r.out,8,mc,len(mesh))
    return r.finish()


def scdd(data,mesh):
    # Reuse the existing actual generator, including its indexed-pool overlap
    # guard. It regenerates the repeat/mask payload, not merely its CRC header.
    sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scenery19'))
    import scdd_compile
    with tempfile.TemporaryDirectory(prefix='b11-scdd-') as td:
        root=Path(td);(root/'ps2-world.re4mesh').write_bytes(mesh)
        expected,_=scdd_compile.scdd(root)
    require(data==expected,'SCDD stale/invalid repeat map')
    return expected


def sccn(data,doc,mesh,files):
    r=Records(data,'SCCN');h=r.row('<4I');mc=struct.unpack_from('<I',mesh,12)[0]
    require('ps2-world.r4sg' in files,'SCCN requires R4SG dependency')
    groups=struct.unpack_from('<I',files['ps2-world.r4sg'],12)[0]
    require(h==(mc,len(mesh),len(doc['meshlets']),groups),'SCCN stale identity/groups')
    table=r.row('<64f');require(all(v>=0 for v in table),'SCCN cone table')
    for _ in range(h[2]*h[3]):
        x,y,z,k,radius=r.row('<3bBf')
        require(k<64 and radius>=0 and (k==0 or x or y or z),'SCCN cone record')
    r.pad(16)
    struct.pack_into('<4I',r.out,0,mc,len(mesh),len(doc['meshlets']),groups)
    return r.finish()


def room(data,doc,mesh,side,files):
    require(64<=len(data)<=1048576,'R4RC size')
    h=ROOM_HEAD.unpack_from(data);mc,mb,pc=bindings(mesh,side)
    require(h[:3]==(b'R4RC',1,64) and 0<h[4]<=8 and h[5]==len(data) and not h[6] and
            not any(h[-1]) and h[-2]==crc(data[64:]),'R4RC header/CRC')
    finite(h[12:14],'R4RC bounds');require(h[7]>0 and h[8]>0 and h[9]>0 and h[12]<=h[13],'R4RC grid/bounds')
    if 'interior.cell' in files:
        require(struct.unpack_from('<I',files['interior.cell'],4)[0]==h[3],'R4RC/PCL1 room disagreement')
    require(64+32*h[4]<=len(data),'R4RC directory extent')
    dirs=[ROOM_DIR.unpack_from(data,64+32*i) for i in range(h[4])]
    tags=[d[0] for d in dirs]
    require(len(set(tags))==len(tags) and b'SRCB' in tags,'R4RC duplicate/missing SRCB')
    rebuilt=[];source_tags=set()
    for tag,version,flags,offset,length,count,stride,alignment,reserved in dirs:
        require(tag in ROOM_SECTIONS and version in ROOM_SECTIONS[tag], 'unsupported R4RC section/version '+repr(tag))
        require(alignment==16 and not reserved and flags in ((0,1,2,3) if tag==b'GRID' else (0,)), 'R4RC section flags/alignment')
        require(offset%16==0 and offset>=64+32*h[4] and offset<=len(data) and length<=len(data)-offset,'R4RC section bounds')
        raw=data[offset:offset+length]
        if tag==b'SRCB':
            require(stride==40 and length==40*count,'SRCB directory');out,source_tags=srcb(raw,count,files)
        elif tag==b'GRID':
            require(count==h[7]*h[8] and stride==0,'GRID directory');out=grid(raw,h[7],h[8])
        elif tag==b'VIS\0':
            require(stride==12 and length>=16,'VIS directory')
            require(count==struct.unpack_from('<H',raw)[0]*struct.unpack_from('<H',raw,2)[0],'VIS cell count')
            out=vis(raw,version,h[7],h[8],pc)
        elif tag==b'OCCL':
            require(stride==56 and length>=32 and count==struct.unpack_from('<H',raw,6)[0],'OCCL directory')
            out=occl(raw,version,h[7],h[8],pc,{p[1] for p in doc['placements']})
        elif tag==b'SCNK':
            require(count==len(doc['meshlets']) and stride in (0,32),'SCNK directory');out=scnk(raw,doc,mesh)
        elif tag==b'SCDD':
            require(count==len(doc['meshlets']) and stride==0,'SCDD directory');out=scdd(raw,mesh)
        elif tag==b'SCCN':
            require(count==len(doc['meshlets']) and stride==16,'SCCN directory');out=sccn(raw,doc,mesh,files)
        else:
            require(count==len(doc['parts']) and stride==4,'SCPS directory')
            out=struct.pack('<4I',mc,mb,count,0)+bytes(4*count)
            out+=bytes(-len(out)%16)
            require(raw==out,'SCPS identity/nonzero initial slots')
        rebuilt.append((tag,version,flags,out,count,stride,alignment,reserved))
    if set(tags)-{b'SRCB',b'GRID'}:
        require({b'R4IM',b'R4PW'}<=source_tags,'R4RC render tables require exact world SRCB dependencies')
    body=bytearray();directory=bytearray();base=64+32*len(dirs)
    for tag,version,flags,out,count,stride,alignment,reserved in rebuilt:
        body.extend(bytes(-(base+len(body))%16))
        directory.extend(ROOM_DIR.pack(tag,version,flags,base+len(body),len(out),count,stride,alignment,reserved))
        body.extend(out)
    body.extend(bytes(-(base+len(body))%16));payload=directory+body
    head=list(h);head[5]=64+len(payload);head[-2]=crc(payload)
    result=ROOM_HEAD.pack(*head)+payload
    require(result==data,'R4RC noncanonical layout/padding or changed record')
    return result
