"""Convert all body/head appearances and the standard Leon hand blobs into indexed actor models."""
import struct
from geometry import actor_strips

def models(disc, private_tables, cloth_bind, material):
    meta=private_tables.read_bytes()
    binds=meta[:(119+5*34)*48]
    binds=binds[:64*48]+cloth_bind[64*48:110*48]+binds[110*48:]
    textures=list(struct.iter_unpack("<4I",meta[len(binds):len(binds)+80]))
    enemy_hands=[]
    at=len(binds)+80
    for app in range(5):
        parts=[]
        for role in (2,3):
            pc,nc,pal,sb,uvbytes=struct.unpack_from("<5I",meta,at);at+=20
            arrays=[]
            for size in (8*pc,8*nc,16*pal,sb,uvbytes):
                arrays.append(meta[at:at+size]);at+=size
            parts.append((role,[arrays[i] for i in (0,1,4,3,2)]))
        enemy_hands.append(parts)
    files=[(disc/"native/pl00/leon_lod.re4lp").read_bytes(),(disc/"native/ganado/ganado_lod.re4gl").read_bytes()]
    hands=(disc/"native/pl00/leon_hands_pl00.re4hp").read_bytes()
    hrows,hblobs=struct.unpack_from("<HH",hands,4+2)
    # header uses a u32 magic and u16 version, row, blob and source counts.
    hand_parts={}
    for i in range(hblobs):
        role,flags,pc,nc,pal,tri,*fields=struct.unpack_from("<BBHHHH5HHH",hands,32+12*hrows+24*i)
        if not flags&1:continue
        at=32*fields[-1];arrays=[]
        for size in fields[:5]:
            arrays.append(hands[at:at+size]);at+=(size+31)&~31
        hand_parts[role]=arrays
    catalog=[]
    for model in range(6):
        leon=model==0
        b=files[0 if leon else 1]
        base=32*struct.unpack_from("<I",b,72)[0]
        directory=128 if leon else 88+(model-1)*128
        parts=[]
        for j in range(6 if leon else 2):
            r=struct.unpack_from("<16I",b,directory+64*j)
            parts.append((r[0],[b[base+o:base+o+n] for o,n in zip(r[6:11],r[11:])]))
        parts+=list(hand_parts.items()) if leon else enemy_hands[model-1]
        texture=(0xec255e66,0x76812316) if leon else textures[model-1][:2]
        weights={};vertices={};normals={};strips=bytearray();bindings=[]
        for role,(pos,nrm,uv,gx,skin) in parts:
            mats=[weights.setdefault(w,len(weights)) for w in (skin[i:i+16] for i in range(0,len(skin),16))]
            def vector(records,buf,index):
                x,y,z,bone=struct.unpack_from("<3hH",buf,index*8)
                return records.setdefault((x,y,z,mats[bone]),len(records))
            start=len(strips)
            for strip in actor_strips(gx,0,False):
                strips+=struct.pack("<I",len(strip))
                for v,n,t in strip:
                    u,vv=struct.unpack_from("<2H",uv,t*4)
                    strips+=struct.pack("<4H",vector(vertices,pos,v&16383),vector(normals,nrm,n&16383),u,vv)
            key=(0xfc24a99c,0x03d13534) if leon and role==7 else texture
            header=material(key,3 if leon and role==7 else 1)
            bindings.append((role,header,start,len(strips)-start))
        first=0 if leon else 119+(model-1)*34
        bones=119 if leon else 34
        raw=struct.pack("<6I",bones,len(weights),len(vertices),len(normals),len(bindings),len(strips))
        raw+=binds[first*48:(first+bones)*48]+b"".join(weights)
        raw+=b"".join(struct.pack("<3hH",*r) for r in vertices)+b"".join(struct.pack("<3hH",*r) for r in normals)
        raw+=b"".join(struct.pack("<4I",*r) for r in bindings)+strips
        catalog.append(raw)
    return catalog
