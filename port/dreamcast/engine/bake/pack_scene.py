"""Bake one captured scene into little-endian, material-grouped replay tables."""
import argparse, collections, json, math, struct, sys, zlib
from pathlib import Path
from pool import bind_shared_positions
from supplement import matched_environment, records
from geometry import World, unpack, actor_strips

class Table:
    def __init__(self): self.rows=[]; self.ids={}
    def add(self,row):
        idx=self.ids.get(row)
        if idx is None: idx=len(self.rows); self.rows.append(row); self.ids[row]=idx
        return idx
def pack(fmt,*values): return struct.pack("<"+fmt,*values)
def block(items):
    offsets=[0]; data=bytearray()
    for item in items:
        data.extend(item); data.extend(bytes((-len(data))%4)); offsets.append(len(data))
    return pack("I",len(items))+pack(f"{len(offsets)}I",*offsets)+data

class Baker:
    def __init__(self,disc,scene,room,supplement=None):
        self.supplement=supplement
        self.environment=Table();self.volumes=Table();self.bounds={}; self.pools={}
        self.path=scene
        self.world=World(disc/f"native/r{room:x}")
        self.texpack=bytearray((disc/"tex.pak").read_bytes())   # bytearray: the bake may append composites
        count,idx=unpack("2I",self.texpack,12)
        self.lookup={(a,b):(c,d) for a,b,c,d in struct.iter_unpack("<4I",self.texpack[idx:idx+16*count])}
        self.textures=Table();self.headers=Table();self.geometry=Table();self.poses=Table();self.lights=Table();self.draws=Table()
        self.wcache={};self.acache={};self.frames=[]
        self.ram=None
        self.assets={}
        from native_world import sky_bytes   # lane eng-bake1: an empty sky for rooms with none
        sky=sky_bytes(disc/f"native/r{room:x}")
        w,h,n,self.top,self.bottom=unpack("HHI2f",sky,8)
        at=unpack("H",sky,38)[0]
        assert sky[:4]==b"R4SK" and len(sky[at:])==n
        desc=b"Sky"+bytes(61)+pack("8I",w,h,0,144,n,0,2,0)
        self.sky=self.textures.add(pack("8s10I",b"RE4DCTX",2,48,96,1,48,144,n,zlib.crc32(sky[at:]),1,0)+desc+sky[at:])
        self.skyhdr=self.headers.add(pack("9I",self.sky,0x8084000a,0xc2000000,0x2080a440|((w.bit_length()-4)<<3)|(h.bit_length()-4),0x48000000,0,0,0,0))
    def source(self,addr,n):
        if self.ram is None:self.ram=next(self.path.glob("resource-ram-*.raw")).read_bytes()
        at=(addr&0x1fffffff)-0xc000000
        if at<0 or at+n>len(self.ram): raise ValueError(f"unavailable source range {addr:x}+{n}")
        return self.ram[at:at+n]
    def asset(self,digest):
        if digest not in self.assets:self.assets[digest]=(self.path/"resources"/digest).read_bytes()
        return self.assets[digest]
    def header(self,key,phase,cull=0,blend=None,world=False,fog=False,actor_state=None):
        off,size=self.lookup[key];pkg=bytes(self.texpack[off:off+size])
        tid=self.textures.add(pkg)
        at=unpack("I",pkg,24)[0]; w,h,fmt,_,_,flags,payload,_=unpack("8I",pkg,at+64)
        li=[0,0,4,2,2,2][phase]
        src,dst=blend or ((1,0) if li==0 else (4,5))
        cmd=0x8084000a|(li<<24)|(128 if world and phase==0 else 0)
        pm1=((7 if phase==5 else 6)<<29)|((cull+bool(cull))<<27)|(1<<25)|(int(li==2)<<26)
        pm2=(src<<29)|(dst<<26)|((0 if fog else 2)<<22)|(int(li!=0)<<20)|(1<<13)|(4<<8)|((3 if li else 1)<<6)|((w.bit_length()-4)<<3)|(h.bit_length()-4)
        if actor_state:
            depth,wrap_s,wrap_t,masked=actor_state
            pm1=(pm1&~((7<<29)|(1<<26)))|((7 if depth==2 else 6)<<29)|(int(depth!=0)<<26)
            pm2=(pm2&~(3<<6))|(3<<6)|(int(not masked)<<19)|(int(not wrap_s)<<16)|(int(not wrap_t)<<15)
        fmtbits=(1,0,2,5,5,6)[fmt]<<27 | ((payload==2)<<30) | (bool(flags&4)<<31)
        return self.headers.add(pack("9I",tid,cmd,pm1,pm2,fmtbits,0,0,0,0))
    def geo(self,strips,actor=False):
        if actor: strips=sorted(strips,key=lambda s:s[0][6])
        out=bytearray()
        for strip in strips:
            if len(strip)<3:continue
            # Per-strip bounding box is evaluated only for the near-plane test.
            low=[min(v[c] for v in strip) for c in range(3)]
            high=[max(v[c] for v in strip) for c in range(3)]
            bone=strip[0][6] if all(v[6]==strip[0][6] for v in strip) else 65535
            out+=pack("2H6f",len(strip),bone,*low,*high)
            out+=b"".join(pack("5fIH3h",*v) for v in strip)
        return self.geometry.add(bytes(out))
    def actor(self,d,ids):
        model,info,part,pos,uv,serial,pals,size,flags=unpack("9I",d)
        stream,norm,pc,nc,ps,ns,lod,crc,fnv,cull,blend=unpack("11I",d,84)
        q,nq,du,dv=unpack("4f",d,128)
        side=ids.get("uv_signed") or ids.get("uv_unsigned")
        if side:
            signed="uv_signed" in ids
        else:
            data=unpack("I",self.source(info+12,4))[0]
            model_tex=unpack("I",self.source(data+16,4))[0]
        # Coarse replacement views may point at a different geometry/UV stream
        # than the source model; the submitted part's UV pointer is authoritative.
            signed=bool(unpack("I",self.source(data+32,4))[0]&0x80000000) if model_tex==uv else False
        cache=(tuple(ids.values()),lod,uv,signed,q,nq,du,dv,bool(pals))
        if cache not in self.acache:
            blob=self.asset(ids["stream"]); posdata=self.asset(ids["position"]); normal=self.asset(ids["normal"]) if ids["normal"] else b""
            # Separate position and normal indices so UV seams and repeated strip
            # corners never duplicate either vertex pass within a submitted part.
            positions, normals = {}, {}
            indices = []
            for strip in actor_strips(blob,lod,signed):
                section = []
                for vi,ni,ti in strip:
                    vi &= 16383
                    ni &= 16383
                    xyz = unpack("3h",posdata,vi*ps)
                    bone = unpack("H",posdata,vi*ps+6)[0] if pals and ps==8 else 0
                    xyz += (bone if bone<pals else 0,)
                    normal_xyz = unpack("3b" if ns==4 else "3h",normal,ni*ns) if normal else (0,0,0)
                    nb = unpack("B" if ns==4 else "H",normal,ni*ns+(3 if ns==4 else 6))[0] if pals and ns in (4,8) and normal else 0
                    nrm = (*normal_xyz,nb if nb<pals else 0)
                    rawuv = self.asset(side)[ti*4:ti*4+4] if side else self.source(uv+ti*4,4)
                    a,b = unpack("2h" if signed else "2H",rawuv)
                    vi = positions.setdefault(xyz,len(positions))
                    ni = normals.setdefault(nrm,len(normals))
                    section.append((vi,ni,a,b))
                if len(section)>=3:
                    indices.append(section)
            def sorted_stream(records):
                ordered = sorted(records,key=lambda v:v[-1])
                return b"".join(pack("3hH",*r) for r in ordered), {records[r]:i for i,r in enumerate(ordered)}
            posrows,pindex=sorted_stream(positions)
            normrows,nindex=sorted_stream(normals)
            if max(len(positions),len(normals))>32767:raise ValueError("kernel signed index overflow")
            out=bytearray(pack("4s3I4fI",b"IDX2",len(positions),len(normals),len(indices),q,nq,du,dv,signed))
            out+=posrows+normrows
            for strip in indices:
                out+=pack("I",len(strip))
                for v,n,a,b in strip:
                    out+=pack("2H2h" if signed else "4H",pindex[v],nindex[n],a,b)
            self.acache[cache]=self.geometry.add(bytes(out))
        return self.acache[cache],(crc,fnv),cull,blend
    def frame(self,path):
        b=path.read_bytes(); sources=iter(json.loads(path.with_suffix(".json").read_text()))
        extra=(self.supplement/path.name).read_bytes() if self.supplement else b
        env=volume=b"";folds=materials=None
        if self.supplement or any(k==16 for k,_ in records(b)):
            folds,materials,env,volume=matched_environment(b,extra)
        fog=bool(env and unpack("I",env,12)[0])
        items=[]; phases=[[] for i in range(6)]; i=28
        while i<len(b):
            k,n=unpack("2I",b,i);items.append((k,i+8-28,b[i+8:i+8+n]));i+=8+n
        camera=next(d for k,_,d in items if k==1)
        refs={off:d for _,off,d in items}
        def submit(phase,header,geo,pose=b"",light=b"",front=False):
            draw=pack("4I",header,geo,self.poses.add(pose),self.lights.add(light))
            phases[phase].append((header,self.draws.add(draw)|(int(front)<<31)))
        view=unpack("25f",camera); uv=[]
        for nx,ny in [(-1,1),(1,1),(-1,-1)]:
            xc=(nx+view[14])/view[13];yc=(ny+view[16])/view[15]
            dx,dy,dz=[view[j]*xc+view[4+j]*yc-view[8+j] for j in range(3)]
            u=math.atan2(dx,dz)/math.tau
            if uv:u-=math.floor(u-uv[0][0]+.5)
            else:u%=1
            v=(self.top-math.degrees(math.atan2(dy,math.hypot(dx,dz))))/(self.top-self.bottom)
            uv.append((u,v))
        uv.append(tuple(b+c-a for a,b,c in zip(*uv)))
        sky_depth=1./unpack("f",env)[0] if env else 1e-7
        skyverts=[(x,y,sky_depth,*st,0xffffffff,0,0,0,0) for (x,y),st in zip([(0,0),(640,0),(0,480),(640,480)],uv)]
        submit(0,self.skyhdr,self.geo([skyverts]))
        it=iter(items); pending=None
        for k,off,d in it:
            if k in (4,5,12,13,14,15,16,17):continue
            if k==2:
                part,ps,count=unpack("3I",d);_,_,picks=next(it)
                mat=self.world.material(part)
                phase=(0,2,3)[ps];head=self.header(mat[:2],phase,mat[5],world=True,fog=fog)
                m=unpack("12f",d,12);near=view[18]/(view[17]-1)
                for pick in struct.iter_unpack("<H6B",picks):
                    token=(part,pick[:3])
                    if token not in self.wcache:
                        strips=self.world.geometry(part,pick)
                        geo=self.geo(strips)
                        self.wcache[token]=geo
                        verts=[v for strip in strips for v in strip]
                        if verts:self.bounds[geo]=[(min(v[j] for v in verts),max(v[j] for v in verts)) for j in range(3)]
                    geo=self.wcache[token]
                    if geo not in self.bounds:continue
                    # Conservative bounds from the actual selected strips. The
                    # recorded view is fixed for this picture; boundary pieces
                    # still take the runtime near-plane clipper.
                    low=-m[11]+sum(min(-m[8+j]*a,-m[8+j]*b) for j,(a,b) in enumerate(self.bounds[geo]))
                    submit(phase,head,geo,d[12:],front=low>near+0.01)
            elif k==3:
                g,key,cull,blend=self.actor(d,next(sources))
                idx=off+len(d)+8
                palette=b""; light=b""
                while idx in refs:
                    kind=unpack("I",b,28+idx-8)[0]
                    if kind not in (4,5,12,13):break
                    value=refs[idx]
                    if kind>=12:value=refs[unpack("I",value)[0]]
                    if kind in (4,12):palette=value
                    else:light=value
                    idx+=len(refs[idx])+8
                phase=1 if blend==0 else 3
                if materials is None:
                    head=self.header(key,phase,cull,fog=fog)
                else:
                    crc,fnv,li,depth,ws,wt,fogged,masked=unpack("8I",next(materials))
                    phase={0:1,4:2,2:3}[li]
                    modes=((4,5),(4,1),(1,1),(2,1),(1,0))
                    head=self.header((crc,fnv),phase,cull,modes[blend],fog=bool(fogged),actor_state=(depth,ws,wt,masked))
                if folds is not None:light=next(folds)
                submit(phase,head,g,d[36:84]+palette,light)
            elif k in (6,7):
                phase=4 if k==6 else 5
                key=unpack("II",d)
                if k==6:
                    xyzuv=unpack("20f",d,28);color,src,dst=unpack("IBB",d,108)
                    verts=[(xyzuv[j],xyzuv[4+j],xyzuv[8+j],xyzuv[12+j],xyzuv[16+j],color,0,0,0,0) for j in (0,1,3,2)]
                else:
                    xyuv=unpack("16f",d,28);color,mode,_=unpack("3I",d,92)
                    src,dst=((4,5),(4,1),(1,1),(2,1),(2,0))[mode]
                    verts=[(xyuv[2*j],xyuv[2*j+1],1.,xyuv[8+2*j],xyuv[9+2*j],color,0,0,0,0) for j in (0,1,3,2)]
                if k==7:
                    off,size=self.lookup[key];pkg=bytes(self.texpack[off:off+size])
                    flags=unpack("I",pkg,44)[0]
                    iw,ih=unpack("2I",d,8)
                    if flags>>31:iw,ih=flags&2047,(flags>>11)&2047
                    w,h=unpack("2I",pkg,unpack("I",pkg,24)[0]+64)
                    verts=[(*v[:3],v[3]*iw/w,v[4]*ih/h,*v[5:]) for v in verts]
                submit(phase,self.header(key,phase,0,(src,dst)),self.geo([verts]))
        bind_shared_positions(self,phases)
        frame=bytearray(camera)
        for phase,draws in enumerate(phases):
            if phase==1:draws.sort(key=lambda t:(unpack("I",self.draws.rows[t[1]],8)[0],t[0]))
            elif phase<3:draws.sort(key=lambda t:t[0])
            frame+=pack("I",len(draws))+b"".join(pack("I",ix) for _,ix in draws)
        frame+=pack("2I",self.environment.add(env),self.volumes.add(volume))
        self.frames.append(bytes(frame))
    def finish(self,room):
        # Keep only the bindings and geometry reached after shared positions
        # are assigned. Construction-time rows can otherwise occupy guest RAM.
        compact_draws=Table(); compact_geometry=Table()
        draw_ids={}; geometry_ids={}
        for i,frame in enumerate(self.frames):
            frame=bytearray(frame)
            at=100
            for phase in range(6):
                count=unpack("I",frame,at)[0];at+=4
                for j in range(count):
                    tag=unpack("I",frame,at)[0];idx=tag&0x7fffffff
                    if idx not in draw_ids:
                        binding=self.draws.rows[idx];geo=unpack("I",binding,4)[0]
                        if geo not in geometry_ids:geometry_ids[geo]=compact_geometry.add(self.geometry.rows[geo])
                        draw_ids[idx]=compact_draws.add(binding[:4]+pack("I",geometry_ids[geo])+binding[8:])
                    struct.pack_into("<I",frame,at,(tag&0x80000000)|draw_ids[idx]);at+=4
            self.frames[i]=bytes(frame)
        self.draws=compact_draws;self.geometry=compact_geometry
        tables=[self.textures,self.headers,self.geometry,self.poses,self.lights,self.draws]
        sections=[block(t.rows) for t in tables]+[block(self.frames),block(self.environment.rows),block(self.volumes.rows)]
        data=block(sections)
        print("section bytes",list(map(len,sections)),"unique",list(map(lambda t:len(t.rows),tables)))
        return pack("4s4I",b"M1PK",2,room,len(data),zlib.crc32(data))+data

def main():
    ap=argparse.ArgumentParser();ap.add_argument("disc",type=Path);ap.add_argument("capture",type=Path);ap.add_argument("room",type=lambda s:int(s,16));ap.add_argument("out",type=Path)
    ap.add_argument("--supplement",type=Path)
    a=ap.parse_args()
    files=sorted(a.capture.glob("picture-*.bin"))
    if len(files)!=300:raise ValueError("need 300 pictures")
    baker=Baker(a.disc,a.capture,a.room,a.supplement)
    for pic in files:baker.frame(pic)
    a.out.write_bytes(baker.finish(a.room))
if __name__=="__main__":main()

