#!/usr/bin/env python3
"""Pin the original PS2 target-replacement path, distinct from recovered GX refraction."""
import argparse,hashlib,importlib.util,json,pathlib,resource,signal
ROOT=pathlib.Path(__file__).resolve().parents[5]
ELF_SHA='465d144f526603d0dcc35ad1fdb4e82cc3a1481c22289f321482cc910fb9f1ad'
def main():
 p=argparse.ArgumentParser();p.add_argument('--elf',type=pathlib.Path,required=True);p.add_argument('--out',type=pathlib.Path,required=True);a=p.parse_args();resource.setrlimit(resource.RLIMIT_AS,(256*1024*1024,256*1024*1024));signal.alarm(120)
 if a.out.exists():raise ValueError('output exists')
 raw=a.elf.read_bytes();assert hashlib.sha256(raw).hexdigest()==ELF_SHA
 sp=importlib.util.spec_from_file_location('water_ps2dis',ROOT/'port/dreamcast/tools/d367/ps2ref/ps2dis.py');D=importlib.util.module_from_spec(sp);sp.loader.exec_module(D);E=D.Elf(a.elf)
 assert E.lookup('TexBlend__FPC11cPolyHeaderP10cModelInfoRP9TEXHeader')==0x25ca40
 # Independent original PS2 path: info blend table at140; wildcard247;
 # target ID-248; read manager TEX0; replace current TEXHeader pointer.
 expected={0x25ca78:0x8cb2008c,0x25ca90:0x241e00f7,0x25caa0:0x92820001,0x25caa4:0x9203ffff,
           0x25cac0:0x2484ff08,0x25cac4:0xdc430008,0x25cacc:0xae770000}
 for pc,word in expected.items():assert E.W(pc)==word,hex(pc)
 calls=E.callers(0x25ca40);assert calls==[0x258354,0x258d58,0x25be00,0x25d0a4,0x25d9f8]
 assert E.W(0x22dd74)==0xac85008c and E.W(0x22dd78)==0x34420004
 # Assign passes zero to PSM_size and constructs TEX0 with PSM bits zero:
 # original target storage is GS PSMCT32, not the DC owner's ARGB4444.
 assert E.W(0x2785f8)==0x0000202d and E.W(0x27860c)>>26==3
 assert E.W(0x278608)==0x8e32005c and E.W(0x278610)==0x8e330060
 # Trans registers target storage before effects and source model OT entries.
 assert (E.W(0x27e594)&0x3ffffff)*4==0x278340
 assert (E.W(0x27e5b8)&0x3ffffff)*4==0x1ea240
 assert (E.W(0x27e684)&0x3ffffff)*4==0x257a68
 result={'schema':'original-ps2-texblend-target-v1','elf_sha256':ELF_SHA,'TexBlend':'0x25ca40..0x25cb14','callers':[hex(c) for c in calls],
 'behavior':'Wildcard247 substitutes target manager TEX0/TEXHeader directly for the authored material texture. Original mesh UV remains the coordinate source. This is not recovered GX screen-space RefractShaderSetup.',
 'source_target':{'dimensions':[64,64],'format':'GS PSMCT32','storage_bytes':16384,'dimension_pin':'st1_0.rel material setup0x65ac..0x65b4 from bind_r100.py','format_pin':'Assign__12TexRenderMng0x2785d8..0x2786d4 PSM_size(0), TEX0 PSM bits0'},
 'source_order':{'Trans_PreTexRender':'0x27e594','Trans_EspTrans':'0x27e5b8','Trans_AppendModelOt':'0x27e684','qualification':'Original same-Trans registration order proved; exact GPU target-raster scheduling not reconstructed by this witness.'},
 'dc_candidate':{'dimensions':[64,64],'format':'PVR ARGB4444 linear','storage_bytes':8192,'timing':'existing PVR owner captures frameN packets and renders before frameN+1 main scene; explicit one-native-frame delay','pass':'only authenticated two current surfaces remapped OP0 to TR2 with raw source alpha240; exact GS alpha/pass semantics remain unqualified'},
 'retired_inference':'Full-frame captured-scene/refraction prerequisite came from recovered GC code and is withdrawn. No such capture is required by the authenticated PS2 TexBlend replacement path.'}
 a.out.write_text(json.dumps(result,indent=2)+'\n');print(hashlib.sha256(a.out.read_bytes()).hexdigest())
if __name__=='__main__':main()
