"""Build every part of each model from its source ModelData, TPL and inverse-bind tables."""
from geometry import unpack, actor_strips
from pack_scene import pack

def build_extra(assets, prior, wanted):
    # The RAM snapshot contains the relocated, immutable room asset archive.
    # Follow source model data only. No draw records or per-picture pick lists are opened.
    raw=next(prior.glob("resource-ram-*.raw")).read_bytes()
    def ptr(at):return unpack("I",raw,at)[0]&0xffffff
    result=[]
    for model in wanted:
        bones=raw[model+258];bone=ptr(model+244);binds=[]
        for _ in range(bones):
            if not bone:raise ValueError("short source skeleton")
            binds.append(raw[bone+248:bone+296]);bone=ptr(bone+244)
        infos=ptr(model+348)
        weights={};vectors=[{},{}];bindings=[];strips=bytearray()
        while infos:
            data=ptr(infos+12);tpl=ptr(infos+16);infos=ptr(infos+20)
            if not data:continue
            count=unpack("H",raw,data+26)[0];part=ptr(data+28)
            flags=unpack("I",raw,data+32)[0];signed=bool(flags&0x80000000)
            compact=bool(flags&0x20000000)
            head=ptr(data);rigid=min(raw[head] if head else 0,bones-1)
            skin=ptr(data+20);pal=raw[data+24];ext=unpack("H",raw,data+42)[0]
            pos=ptr(data+48);normal=ptr(data+52);uv=ptr(data+16)
            q=16/(2**raw[data+40])
            def weight(b):
                ids=[rigid,0,0];num=1;values=[1.,0.,0.]
                if skin and (pal>1 or ext>1):
                    if ext>255:
                        *ids,num=unpack("4H",raw,skin+12*b)
                        pct=unpack("3B",raw,skin+12*b+8)
                    else:
                        *ids,num=unpack("4B",raw,skin+8*b)
                        pct=unpack("3B",raw,skin+8*b+4)
                    if not 1<=num<=3 or any(i>=bones for i in ids[:num]):raise ValueError("invalid skin reference")
                    ids=list(ids[:num])+[0]*(3-num);values=[v*.01 for v in pct]
                record=pack("4B3f",*ids,num,*values)
                return weights.setdefault(record,len(weights))
            def vector(kind,index):
                if not kind:
                    x,y,z,b=unpack("3hH",raw,pos+8*index);scale=q
                elif compact:
                    x,y,z,b=unpack("3bB",raw,normal+4*index);scale=256
                else:
                    x,y,z,b=unpack("3hH",raw,normal+8*index);scale=1
                record=tuple(min(32767,max(-32768,round(t*scale))) for t in (x,y,z))+(weight(b),)
                return vectors[kind].setdefault(record,len(vectors[kind]))
            desc=ptr(tpl+8)
            for _ in range(count):
                size=unpack("I",raw,part+24)[0]
                stream=raw[part+32:part+32+size]
                tex=raw[part+12];th=ptr(desc+tex*8);pixels=ptr(th+8)
                if raw[pixels:pixels+6]!=b"R4NREF":raise ValueError(f"missing static texture identity at {pixels:x}")
                key=unpack("2I",raw,pixels+8)
                header=assets.header(key,1,fog=True)
                start=len(strips)
                for strip in actor_strips(stream,0,signed):
                    strips+=pack("I",len(strip))
                    for v,n,t in strip:
                        u,vv=unpack("2h" if signed else "2H",raw,uv+t*4)
                        if signed:u*=128;vv*=128
                        strips+=pack("4H",vector(0,v&16383),vector(1,n&16383),u&65535,vv&65535)
                bindings.append((0,header,start,len(strips)-start));part+=32+size
        if not bindings:raise ValueError("no source parts")
        result.append(pack("6I",bones,len(weights),len(vectors[0]),len(vectors[1]),len(bindings),len(strips))+
                      b"".join(binds)+b"".join(weights)+b"".join(pack("3hH",*v) for pool in vectors for v in pool)+
                      b"".join(pack("4I",*row) for row in bindings)+strips)
    return result
