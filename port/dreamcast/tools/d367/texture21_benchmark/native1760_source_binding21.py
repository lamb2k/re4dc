"""143 explicit native sources for1760; actual1618 base and142 immutable files."""
import gzip,hashlib,json,struct,zlib
from pathlib import Path
from native_c_source_binding21 import NativeCBinding,proof
MANIFEST_PATH=r'C:\Flycast-Evidence\re4-dreamcast\texture21-benchmark-20261021\append1760-writer-native-c-01\NATIVE-SOURCES-143.json.gz'
MANIFEST_SHA='079bea01414f7d3e04c9bddf4b28d227ad83882a66ecc4138ab4d59b88b072c7'
MEMBER_PATH=r'C:\Flycast-Evidence\re4-dreamcast\texture21-benchmark-20261021\append1760-writer-native-c-01\PARENT-7151-SHA256.bin'
MEMBER_SHA='0e1445bf474a68a059dd81d9ffa240c37b105c24c85f01f931ea5c22ea5782ca'
ROOTS=dict(actual1618=r'C:\Game Dev\Emulators\re4-assets-private\texture-append1618-20261022-v3-native-c',alpha142=r'C:\Flycast-Evidence\re4-dreamcast\texture-rect21-20261021\next142-alpha-batch-01',repeat16=r'C:\Flycast-Evidence\re4-dreamcast\texture-rect21-20261021\alpha-repeat16-batch-01')
PARENT_PATH=r'C:\Flycast-Evidence\re4-dreamcast\texture21-benchmark-20261021\append1760-plan-01\UNIT-SHA256SUMS'
PARENT_SHA='274ee1916fede1ae636f9aa210ea0500f9b33804855347c55ed42f726f9ca79d'
BASE_SHA='d43d1c81ba2e70ab0177c6c97867fd39c95d68a114b727601b3eadd14e6aaf08'
TARGET='1838d97ae07637fa47beed574033e2d4f79595f86fb024ace6e6e7cc752f6477'
def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def require(ok,why):
 if not ok:raise ValueError(why)
class Native1760Binding:
 open=NativeCBinding.open
 def __init__(self,record):
  require(record['schema']=='1760-native-C-143-source-map-v1'and record['roots']==ROOTS and record['parent_input_seal_path']==PARENT_PATH and record['parent_input_seal_sha256']==PARENT_SHA and record['parent_pack_sha256']==BASE_SHA,'fixed143 roots/schema/parent')
  require(record['expected']==dict(pack_sha256=TARGET,pack_bytes=162555904,members=7293,mips_if_selected=1760,index_sectors=57,data_offset=118784),'fixed1760 target identity')
  require(record['parent_member_sha256_binary']==dict(path=MEMBER_PATH,sha256=MEMBER_SHA,bytes=7151*32),'fixed7151 binarySHA map')
  self.record=record;self.by_c={};self.by_key={};seen=set();counts={'actual1618':0,'alpha142':0,'repeat16':0}
  require(len(record['files'])==143,'exact143 native sources')
  for e in record['files']:
   group='actual1618'if e['source_group']=='actual1618'else'repeat16'if e.get('semantic_source')=='repeat16'else'alpha142';root=ROOTS[group]
   proof.require_same_path(e['c_source_root'],root);proof.require_same_path(e['c_source_path'],str(Path(root)/e['relative_path']));proof.require_same_path(e['c_source_path'],e['native_final_path'])
   ident=e['native_identity'];require(set(ident)=={'volume_serial','file_index','link_count','logical_bytes','creation_time'}and all(type(v)is int for v in ident.values())and ident['link_count']==1 and ident['file_index']>0 and ident['logical_bytes']>0 and type(e['last_write_filetime'])is int and e['last_write_filetime']>0,'native143 typed identity/link/mtime')
   key=proof.canonical_c(e['c_source_path']);pair=(ident['volume_serial'],ident['file_index']);require(key not in self.by_c and pair not in seen,'native143 duplicate identity/path');seen.add(pair);self.by_c[key]=e;counts[group]+=1
   require(len(e['sha256'])==64 and all(c in'0123456789abcdef'for c in e['sha256']),'exact fileSHA')
   if group=='actual1618':require(e['key']is None and e['relative_path']=='tex.pak'and e['member_refs']==7151 and ident['logical_bytes']==160159744 and e['sha256']==BASE_SHA,'exact actual1618 source')
   else:
    require(e['source_group']=='final142'and e['member_refs']==1 and e['relative_path']=='textures/'+e['key']+'.re4tex'and e['bytes']==ident['logical_bytes']and e['key']not in self.by_key,'exact142 source contract');self.by_key[e['key']]=e
  require(counts=={'actual1618':1,'alpha142':126,'repeat16':16}and len(self.by_key)==142,'143=1+126+16 scope')
 @classmethod
 def load(cls,plan):
  require(plan.get('native_source_manifest_path')==MANIFEST_PATH and plan.get('native_source_manifest_sha256')==MANIFEST_SHA,'mandatory native143 manifest path/SHA')
  raw=Path(MANIFEST_PATH).read_bytes();require(hashlib.sha256(raw).hexdigest()==MANIFEST_SHA and len(raw)<65536,'fixed native143 manifest bytes');data=gzip.decompress(raw);require(len(data)<524288,'bounded143 metadata');return cls(json.loads(data))
 def preflight(self):
  for e in self.by_c.values():
   actual=proof.verified_file(Path(e['c_source_path']),Path(e['c_source_root']),e['sha256']);require(actual['native_identity']==e['native_identity']and actual['last_write_filetime']==e['last_write_filetime'],'native143 source drift');proof.require_same_path(actual['native_final_path'],e['native_final_path'])
  return len(self.by_c)
 def map_rows(self,rows):
  counts={k:0 for k in self.by_c}
  for r in rows:
   key=proof.canonical_c(r['path']);e=self.by_c.get(key);require(e is not None and r['source']==e['source_group'],'source outside143 contract');proof.require_same_path(r['source_root'],e['c_source_root']);require(0<=r['source_offset']and r['source_offset']+r['bytes']<=e['native_identity']['logical_bytes'],'source143 member bounds')
   if e['source_group']=='final142':require(r['sha256']==e['sha256']and r['bytes']==e['bytes']and r['source_offset']==0 and r['body_crc32']==e['body_crc32']and r['descriptor_hex']==e['descriptor_hex'],'new142 exact member contract')
   counts[key]+=1
  require(len(rows)==7293 and all(counts[k]==e['member_refs']for k,e in self.by_c.items()),'all7293 from143 sources');return rows
 def resolve(self,head,index):
  data=Path(MEMBER_PATH).read_bytes();require(len(data)==7151*32 and hashlib.sha256(data).hexdigest()==MEMBER_SHA,'all7151 exact source SHA map')
  base=next(e for e in self.by_c.values()if e['source_group']=='actual1618');rows={};member_digest=hashlib.sha256()
  with self.open(Path(base['c_source_path']))as f:
   ph=f.read(2048);pi=f.read(56*2048)
  require(ph[:8]==b'RE4PAK1\0'and struct.unpack_from('<5I',ph,8)==(1,7151,2048,116736,zlib.crc32(pi)&0xffffffff)and hashlib.sha256(pi).hexdigest()==self.record['parent_index_sha256'],'actual1618 exact index')
  last=None;oldcursor=116736
  for i in range(7151):
   k0,k1,off,n=struct.unpack_from('<4I',pi,16*i);key='%08x-%08x'%(k0,k1);require((last is None or key>last)and n>0 and off==oldcursor,'actual7151 ordered contiguous extents');last=key;oldcursor+=(n+2047)//2048*2048;h=data[32*i:32*i+32].hex();member_digest.update((key+' '+str(n)+' '+h+'\n').encode());rows[key]=dict(key=key,bytes=n,sha256=h,source='actual1618',path=Path(base['c_source_path']),source_root=Path(base['c_source_root']),source_offset=off)
  require(oldcursor==160159744 and member_digest.hexdigest()==self.record['parent7151_member_identity_digest'],'all7151 source identities')
  for key,e in self.by_key.items():
   require(key not in rows,'immutable142 collision');rows[key]=dict(key=key,bytes=e['bytes'],sha256=e['sha256'],source='final142',path=Path(e['c_source_path']),source_root=Path(e['c_source_root']),source_offset=0,body_crc32=e['body_crc32'],descriptor_hex=e['descriptor_hex'])
  require(len(head)==2048 and len(index)==57*2048 and head[:8]==b'RE4PAK1\0'and struct.unpack_from('<5I',head,8)==(1,7293,2048,118784,zlib.crc32(index)&0xffffffff)and not any(head[28:])and not any(index[7293*16:]),'full new57sector index')
  ordered=[];cursor=118784
  for i in range(7293):
   k0,k1,off,n=struct.unpack_from('<4I',index,16*i);key='%08x-%08x'%(k0,k1);r=rows.pop(key);require(off==cursor and n==r['bytes'],'reindexed7293 source extent');ordered.append({**r,'offset':off});cursor+=(n+2047)//2048*2048
  require(not rows and cursor==162555904 and[r['key']for r in ordered]==sorted(r['key']for r in ordered),'complete7293 reindex');return self.map_rows(ordered)
