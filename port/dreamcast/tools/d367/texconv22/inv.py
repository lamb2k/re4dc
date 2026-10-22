import struct,sys,zlib,collections,json
sys.path.insert(0,'/root/work/lanes/texconv22/tree/port/dreamcast/tools/d367/vram')
from vq_pak import read_pak
H=struct.Struct("<8s10I"); T=struct.Struct("<64s8I")
def info(b):
    h=H.unpack_from(b); t=T.unpack_from(b,h[5])
    crcok = h[8]==zlib.crc32(b[48:])&0xffffffff
    return dict(cnt=h[4],w=t[1],h=t[2],fmt=t[3],size=t[5],flags=t[6],pay=t[7],name=t[0].rstrip(b'\0').decode('latin1'),crc_full=crcok)
p=read_pak(open(sys.argv[1],'rb').read())
c=collections.Counter(); rows={}
for k,b in p.items():
    i=info(b); key='%08x-%08x'%k; rows[key]=i
    c[(i['fmt'],i['pay'],bool(i['flags']&4))]+=1
print(len(p)); 
for k,v in sorted(c.items()): print(k,v)
print('crc_full', sum(r['crc_full'] for r in rows.values()))
json.dump(rows,open(sys.argv[2],'w'))
