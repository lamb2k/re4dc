#!/usr/bin/env python3
"""Read-only original r100 EST0 texture inputs; no converter, runtime admission or plan approval."""
import argparse,hashlib,importlib.util,json,pathlib,resource,signal,struct,sys
ROOT=pathlib.Path(__file__).resolve().parents[5]
def sha(d):return hashlib.sha256(d).hexdigest()
def module(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def static_texture(data,tex):
 # Only the four observed single-picture, no-duration-table sources. Do not
 # extend the water-row animation parser by appending fabricated bytes.
 def read(fmt,off):
  size=struct.calcsize('<'+fmt)
  if off<0 or off+size>len(data):raise ValueError('field outside EFF')
  return struct.unpack_from('<'+fmt,data,off)
 h=read('12I',0)
 if h[0]!=11:raise ValueError('unexpected EFF version')
 n=read('I',h[1])[0]
 if not 0<n<4096:raise ValueError('texture count')
 ids=[read('H',h[1]+4+8*i)[0] for i in range(n)]
 if len(set(ids))!=n or tex not in ids:raise ValueError('ambiguous/missing ID')
 def table(base):
  if not base or read('I',base)[0]!=n:raise ValueError('table count')
  out=[base+read('I',base+4+4*i)[0] for i in range(n)]
  if any(x<base+4+4*n or x>=len(data) for x in out):raise ValueError('table bounds')
  return out
 tpls,anms=table(h[6]),table(h[7]);index=ids.index(tex);t,a=tpls[index],anms[index]
 cuts=[*tpls,*anms,*h[1:],len(data)]
 alimit=min(x for x in cuts if x>a);limit=min(x for x in cuts if x>t)
 magic,count,start=read('3I',t)
 if magic!=0x1000 or count!=1 or start<12 or t+start+48>limit:raise ValueError('not bounded single-picture TPL')
 if a+16>alimit or read('H',a+8)[0]!=1 or read('B',a+12)[0]!=0:raise ValueError('not static no-duration animation')
 off=t+start;w,height,depth,inter=read('4H',off);io,po=read('2I',off+32)
 if not w or not height or depth not in (8,9) or inter&~3:raise ValueError('unsupported original picture')
 bits=4 if depth==8 else 8;pixel_bytes=(w*height*bits+7)//8;palette_bytes=96 if bits==4 else 1024
 if min(io,po)<start+48 or t+io+pixel_bytes>limit or t+po+palette_bytes>limit:raise ValueError('picture spans outside original component')
 return {'texture':tex,'tpl_offset':t,'animation_offset':a,'animation_header_sha256':sha(data[a:a+16]),'animation':{'frames':1,'data_num':0,'duration_table':'absent; source header only'},'pictures':[{'descriptor_offset':off,'descriptor_sha256':sha(data[off:off+48]),'pixels_offset':t+io,'pixels_bytes':pixel_bytes,'pixels_sha256':sha(data[t+io:t+io+pixel_bytes]),'palette_offset':t+po,'palette_bytes':palette_bytes,'palette_sha256':sha(data[t+po:t+po+palette_bytes]),'width':w,'height':height,'depth':depth,'interlace':inter}]}
def main():
 p=argparse.ArgumentParser();p.add_argument('--iso',type=pathlib.Path,required=True);p.add_argument('--out',type=pathlib.Path,required=True);a=p.parse_args()
 resource.setrlimit(resource.RLIMIT_AS,(256*1024*1024,256*1024*1024));signal.alarm(120)
 if a.out.exists():raise ValueError('output exists')
 sys.path.insert(0,str(ROOT/'port/dreamcast/tools'));import ps2_bin as B
 A=module('water24_original_recipes',ROOT/'tools/audit_ps2_fx_recipes.py')
 index=B.afs_index(a.iso);members={};effs={}
 for name,entry in [('r100.dat',6),('Core.dat',1)]:
  off,size=index[name]
  if size>128*1024*1024:raise ValueError('member exceeds bounded scan')
  raw=B.afs_read(a.iso,name,index)
  if len(raw)!=size:raise ValueError('short member')
  if name=='r100.dat' and sha(raw)!='75fe9de6fe15af37a454ae6d0a0667aec6a578a898afb5028bf79acf8b4b6441':raise ValueError('wrong original r100 member')
  entries=[d for i,tag,d in B.dat_entries(raw) if i==entry and tag=='EFF']
  if len(entries)!=1:raise ValueError('missing/ambiguous exact EFF entry')
  effs[name]=entries[0];members[name]={'offset':off,'bytes':size,'sha256':sha(raw),'eff_entry':entry,'eff_bytes':len(entries[0]),'eff_sha256':sha(entries[0])}
 records=[r for r in A.decode_eff(effs['r100.dat'],'<') if r['table']=='est' and r['no']==0]
 if [(r['id'],r['tex'],r['parts'],r['tool_flags']) for r in records]!=[(0x47,0x56,0xfb,0x10000),(0x47,0x1d,0xfb,0x30000),(0x47,0xca,0xfc,0x10000),(0x08,0xfc,0xfd,0x10000)]:raise ValueError('original EST0 recipe changed')
 textures=[]
 for tex,member in [(0x56,'Core.dat'),(0x1d,'Core.dat'),(0xca,'r100.dat'),(0xfc,'Core.dat')]:
  textures.append({'member':member,'eff_entry':members[member]['eff_entry'],**static_texture(effs[member],tex)})
 result={'schema':'original-r100-est0-texture-inputs-v1','iso_bytes':a.iso.stat().st_size,'iso_full_sha256':'NOT HASHED','members':members,'records':records,'textures':textures,
 'source_binding':'Actual r100 setup invokes EST0; four original records and exact PS2 descriptor/pixel/palette/animation spans are pinned here. Main Core.dat EFF entry1 is the existing common-pack source selection; duplicate texture IDs in other Core EFF entries cannot substitute for it.',
 'qualification':'This is original source metadata only, not a complete runtime contributor allowlist. Actual target assignment, recipe/lifetime equivalence, converted package ancestry, accepted live Entry membership, frame selection, loaded payload and source-owner admission must be independently proved. No filename, texture ID, converter success or shader flag grants positive origin.',
 'asset_conversion':False,'runtime_origin_admitted':False,'current_payload_bound':False}
 a.out.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'sha256':sha(a.out.read_bytes()),'records':len(records),'textures':[{ 'tex':x['texture'],'member':x['member'],'frames':len(x['pictures']) } for x in textures]}))
if __name__=='__main__':main()
