"""Decode selected world strips and actor levels from their private source tables."""
import struct
from pathlib import Path

def unpack(fmt, data, offset=0):
    return struct.unpack_from("<"+fmt,data,offset)

class World:
    def __init__(self, directory):
        self.mesh=(directory/"ps2-world.re4mesh").read_bytes()
        self.side=(directory/"ps2-world.r4pw").read_bytes()
        sg=directory/"ps2-world.r4sg"
        self.sg=sg.read_bytes() if sg.is_file() else bytes(32)
        self.groups=unpack("I",self.sg,12)[0]
        assert self.mesh[:4]==b"R4IM" and self.side[:4]==b"R4PW"
        self.parts,self.lets,self.verts,self.strips=unpack("4I",self.mesh,44)
    def material(self,part):
        return unpack("IIHHBBBB",self.side,32+16*part)
    def geometry(self,part,pick):
        li,nr,mask,lo,hi,_,_=pick
        first,strip,size,n,sc,*bounds=unpack("IIIHH6H",self.mesh,self.lets+28*li)
        at=self.strips+strip
        if sc&0x8000:
            offsets=unpack(f"{n}H",self.mesh,at)
            at+=2*n
        else: offsets=range(n)
        ub,vb,us,vs=unpack("4f",self.mesh,self.parts+36*part+20)
        marked=self.material(part)[-1]&1
        vertices=[]
        for idx in offsets:
            x,y,z,u,v,c=unpack("6H",self.mesh,self.verts+12*(first+idx))
            if marked:
                colour=sum(((c>>shift)&15)*17<<(shift*2) for shift in (0,4,8,12))
            else:
                colour=0xff000000 | sum((((c>>sh)&31)*255//31)<<out for sh,out in ((0,0),(5,8),(10,16)))
            vertices.append((x,y,z,ub+us*u,vb+vs*v,colour,0,0,0,0))
        selected=[]
        if nr==255: selected=[(0,size)]
        elif nr:
            end=0
            for g in range(self.groups):
                start=end
                end=unpack("H",self.sg,32+(li*self.groups+g)*16+12)[0]
                if mask & 1<<g: selected.append((start,end))
        strips=[]
        for start,end in selected:
            while start<end:
                k=self.mesh[at+start]; start+=1
                if k<3 or start+k>end: raise ValueError("world strip crossed group")
                strips.append([vertices[i] for i in self.mesh[at+start:at+start+k]])
                start+=k
        return strips

def raw_strips(blob,stride):
    i=0
    while i<len(blob):
        op=blob[i];i+=1
        if op==0: continue
        n=struct.unpack_from(">H",blob,i)[0];i+=2
        corners=[]
        for _ in range(n):
            ix=struct.unpack_from(">3H" if stride==6 else ">4H",blob,i);i+=stride
            corners.append((ix[0],ix[1],ix[-1]))
        if op==0x98: yield corners
        elif op==0x90:
            for k in range(0,n,3): yield corners[k:k+3]
        elif op==0x80:
            for k in range(0,n,4): yield [corners[k+t] for t in (0,1,3,2)]
        elif op==0xa0:
            for k in range(2,n): yield [corners[0],corners[k-1],corners[k]]
        else: raise ValueError(f"unrecognised primitive {op:x}")

def actor_strips(blob,level,signed_uv):
    if blob[:2]!=b"\xfe\x03":
        yield from raw_strips(blob,8 if signed_uv else 6)
        return
    _,_,flags,levels,meshlets,_,rec4,idx4,lod4,_=unpack("4B6H",blob)
    stride=3+bool(flags&1)+bool(flags&2)
    for m in range(meshlets):
        counts,first,index=unpack("IHH",blob,32+8*m)
        offset=idx4*4
        if level:
            if level>levels: raise ValueError("invalid captured actor level")
            _,tab,lists=unpack("fHH",blob,lod4*4+8*(level-1))
            counts,index,_=unpack("IHH",blob,tab*4+8*m)
            offset=lists*4
        strip=[]
        for v in blob[offset+index:offset+index+((counts>>8)&4095)]:
            entry=first+(v&127)
            strip.append(unpack("3H",blob,rec4*4+entry*stride*2))
            if v&128:
                if len(strip)>=3: yield strip
                strip=[]
        if strip: raise ValueError("unterminated actor strip")


