#!/usr/bin/env python3
"""Authenticate the opening room's water-material IDs from the original PS2 code.
Private inputs only. Emits hash/offset metadata; never emits code or asset bytes.
"""
import argparse,hashlib,importlib.util,json,pathlib,resource,signal,struct,sys
ROOT=pathlib.Path(__file__).resolve().parents[5]
PINS={'elf':'465d144f526603d0dcc35ad1fdb4e82cc3a1481c22289f321482cc910fb9f1ad','rel':'01718aa3fdb13d69bc00d4b577a09231d33cf612eee79a1c489c86813c496f5f','smd':'a3718d4e470e17a40769accdb7a2552a8058d79397051279b9b4b6a9ae8768da'}
def sha(data):return hashlib.sha256(data).hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument('--elf',type=pathlib.Path,required=True);p.add_argument('--rel',type=pathlib.Path,required=True);p.add_argument('--smd',type=pathlib.Path,required=True);p.add_argument('--out',type=pathlib.Path,required=True);a=p.parse_args()
 resource.setrlimit(resource.RLIMIT_AS,(256*1024*1024,256*1024*1024));signal.alarm(120)
 if a.out.exists():raise ValueError('output exists')
 refs={}
 for k in PINS:
  path=getattr(a,k);d=path.read_bytes()
  if sha(d)!=PINS[k]:raise ValueError('wrong original '+k)
  refs[k]={'path':str(path),'bytes':len(d),'sha256':sha(d)}
 spec=importlib.util.spec_from_file_location('early_water_ps2dis',ROOT/'port/dreamcast/tools/d367/ps2ref/ps2dis.py');D=importlib.util.module_from_spec(spec);spec.loader.exec_module(D)
 E=D.Elf(a.elf);R=D.Rel(a.rel)
 assert R.W(0x3378)>>26==3 and (R.W(0x3378)&0x3ffffff)*4==0x6500,'R100Init target'
 calls={pc:R.relocs[pc][1] for pc in (0x652c,0x659c,0x65b8,0x65c8,0x65d4,0x6600,0x6610,0x661c)}
 assert calls[0x652c]=='GetTexRenderMgr__FPP12TexRenderMng'
 assert calls[0x659c].startswith('EstSet__')
 assert calls[0x65b8]==calls[0x6600]=='SmdGetObjPtr__Fi'
 assert R.W(0x65bc)==0x0000202d and R.W(0x6604)==0x24040001,'water IDs 0/1'
 assert R.W(0x6544)==0x240200f7 and R.W(0x65d8)==0x240500ff,'source texture/blend'
 assert R.W(0x65e0)==0x241300f0 and R.W(0x65e8)==0x24120002,'alpha/shader'
 assert R.W(0x65f0)==0x2411001e and R.W(0x65f8)==0x24100080,'refraction'
 # Original SmdSetup stores each object by the SMD row's byte51, not its ordinal.
 assert E.W(0x275388)==0x92230033 and E.W(0x2753bc)==0x92250033
 assert E.W(0x2753c4)==0x00051880 and E.W(0x2753dc)==0xac700000
 # Original getter indexes that same object table by the supplied ID * 4.
 assert E.W(0x275b64)==0x00041880 and E.W(0x275b74)==0x00651821 and E.W(0x275b7c)==0x8c630000
 smd=a.smd.read_bytes();n=struct.unpack_from('<H',smd,2)[0];ids=[smd[16+64*i+51] for i in range(n)]
 bindings=[]
 for wanted in (0,1):
  matches=[i for i,v in enumerate(ids) if v==wanted]
  assert len(matches)==1,'nonunique source water ID'
  i=matches[0];off=16+64*i
  bindings.append({'source_object_id':wanted,'placement':i,'bin':smd[off+48],'row_offset':off,'row_sha256':sha(smd[off:off+64])})
 result={'schema':'r100-authenticated-ps2-water-material-v1','inputs':refs,'source_callsite':{'module':'st1_0.rel','R100Init':'0x3178','callsite':'0x3378','material_setup':'0x6500..0x665c'},'PS2_SmdSetup':'0x275330..0x2754c4','PS2_SmdGetObjPtr':'0x275b28..0x275bac','bindings':bindings,'material':{'blend_source_texture':247,'blend_ratio':255,'object_alpha':240,'shader_type':2,'refract_pow':30,'refract_ratio':128,'target_width':64,'target_height':64},'interpretation':'Original PS2 code authenticates IDs and SMD row mapping. This does not prove the current baked package carries shader/refraction state, dynamic target ancestry, look, memory, or runtime acceptance.'}
 a.out.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'bindings':bindings,'metadata_sha256':sha(a.out.read_bytes())}))
if __name__=='__main__':main()
