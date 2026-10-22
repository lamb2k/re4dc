"""Read-only actual04 validation and new image-admission sidecars. Never writes images."""
from pathlib import Path
import argparse,gzip,hashlib,json,re,struct,time,shutil
SOURCE='63644457a2251a398de174f47be650e1b2b4c791'
E=Path('/mnt/c/Flycast-Evidence/re4-dreamcast/mipmap21-next792-programme-20261022-04')
B=Path('/root/probe/mipmap21-next792-link-20261022-04/out')
OUT=Path('/mnt/c/Flycast-Evidence/re4-dreamcast/mipmap04-stage-admission-root-20261022')
L=Path(__file__).resolve().parent
RAW='b3c1069dc489f66d4ee7428ca396b3ef35bce559dae27de380c0ad555da4b1a0'
ELFH='ee21f7d553d023428e936cfe68d6d5454ea6277ba3e6e28ca19bc7418facf6f9'
START=time.monotonic();CAP=1048576

def require(ok,msg):
 if not ok:raise ValueError(msg)
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load(p):return json.loads(Path(p).read_text())
def win(p):
 s=str(p);require(s.startswith('/mnt/c/'),'sidecar needs canonical C path');return 'C:/'+s[7:]
def guard():
 require(time.monotonic()-START<120,'metadata unit deadline')
 require(shutil.disk_usage('/mnt/c').free>=19394461696+67108864,'floor/source-peer')
 total=131072
 for root in (L,OUT):
  if root.exists():
   for p in root.rglob('*'):
    if p.is_file():
     st=p.stat();total+=max(st.st_size,st.st_blocks*512,((st.st_size+4095)//4096)*4096)
 require(total<CAP,'metadata source aggregate1MiB');return total

def write(name,j):
 guard();p=OUT/name;require(not p.exists(),'refuse metadata overwrite '+str(p));s=(json.dumps(j,indent=2)+'\n').encode();require(guard()+((len(s)+4095)//4096)*4096<CAP,'prospective quota')
 with p.open('xb')as f:f.write(s)
 guard();return dict(path=win(p),sha256=sha(p))
def spec(p):return dict(path=win(p),sha256=sha(p))
def fnv(blob):
 require(len(blob)%4==0,'word-FNV alignment');v=2166136261
 for (w,)in struct.iter_unpack('<I',blob):v=((v^w)*16777619)&0xffffffff
 return v

class Elf:
 def __init__(self,data):
  self.data=data;require(len(data)>=52 and data[:6]==b'\x7fELF\x01\x01','ELF32 little endian');h=struct.unpack_from('<16sHHIIIIIHHHHHH',data);require(h[2]==42 and h[1]in(1,2),'SH-4 object/executable');self.kind=h[1]
  require(h[11]==40 and h[12]>0 and h[6]+h[11]*h[12]<=len(data),'ELF section extent')
  self.sh=[struct.unpack_from('<10I',data,h[6]+i*40)for i in range(h[12])];require(h[13]<len(self.sh),'shstr index');strings=self.section(h[13]);self.names=[self.string(strings,s[0])for s in self.sh];self.sections=dict(zip(self.names,range(len(self.sh))));self.symbols={}
  for s in self.sh:
   if s[1]!=2:continue
   require(s[9]==16 and s[6]<len(self.sh) and s[5]%16==0,'symbol table contract');ss=self.section(s[6]);raw=self.slice(s[4],s[5])
   for off in range(0,len(raw),16):
    n,val,size,info,other,sect=struct.unpack_from('<IIIBBH',raw,off);name=self.string(ss,n)
    if name:self.symbols[name]=(val,size,sect)
  self.ph=[]
  if h[10]:
   require(h[9]==32 and h[5]+h[9]*h[10]<=len(data),'ELF segment extent')
   self.ph=[struct.unpack_from('<8I',data,h[5]+i*32)for i in range(h[10])]
 def slice(self,off,n):require(0<=off<=off+n<=len(self.data),'ELF data extent');return self.data[off:off+n]
 @staticmethod
 def string(s,off):
  require(off<len(s),'ELF string offset');end=s.find(b'\0',off);require(end>=off,'ELF string termination');return s[off:end].decode()
 def section(self,i):
  s=self.sh[i];require(s[1]!=8,'NOBITS has no bytes');return self.slice(s[4],s[5])
 def blob(self,name):
  val,n,i=self.symbols[name];require(0<i<len(self.sh),'defined symbol');s=self.sh[i];off=val-(s[3]if self.kind==2 else 0);require(0<=off<=off+n<=s[5] and s[2]&2 and not(s[2]&1),'immutable allocated symbol');return self.section(i)[off:off+n]
 def raw(self):
  rows=[p for p in self.ph if p[0]==1 and p[4]];require(rows,'PT_LOAD present');lo=min(p[2]for p in rows);hi=max(p[2]+p[4]for p in rows);require(0x8c010000<=lo<hi<=0x8d000000,'Dreamcast RAM span');out=bytearray(hi-lo);covered=set()
  for p in rows:
   require(p[5]>=p[4] and p[2]+p[5]<=0x8d000000,'PT_LOAD BSS bound');out[p[2]-lo:p[2]-lo+p[4]]=self.slice(p[1],p[4])
  return bytes(out)

def overlay(blob,expected_id,address,slot):
 require(len(blob)>=64,'overlay header size');h=struct.unpack_from('<16I',blob);require(h[:2]==(0x4f344552,1) and list(h[14:])==expected_id,'overlay magic/version/newID');require(h[4]==address and len(blob)==64+h[2]+4*h[3]<=slot and h[2]%4==0,'overlay slot/address/size')
 body=blob[64:64+h[2]];rel=blob[64+h[2]:];require(fnv(body)==h[12] and fnv(rel)==h[13],'overlay payload/relocation word-FNV');offsets=[x[0]for x in struct.iter_unpack('<I',rel)];require(offsets==sorted(set(offsets)) and all(o%4==0 and o<h[2]for o in offsets),'overlay relocation offsets');require(all(address<=struct.unpack_from('<I',body,o)[0]<=address+len(body)for o in offsets),'overlay relocation targets');require(all(x<=h[2]for x in h[5:12]),'overlay bounds');return list(h)

def main(independent):
 guard();require(not OUT.exists(),'fresh output only');q=load(E/'qualification.json');require(q['source']==SOURCE and q['status']=='PASS_PRIVATE_ALLOCATED_PROGRAMME_LINK_ONLY','actual unit qualification');require(q['programme']['sha256']==RAW and q['ELF']['sha256']==ELFH,'frozen actual04 identity')
 # Verify the frozen unit seal, without changing or recertifying its past inputs.
 seal=E/'SHA256SUMS.txt';require(sha(seal)=='3c6b4c70d0193c7e1a5000eaa159fe3fd540e32a72b6374e26ba560b5f55da2a','actual04 seal identity')
 for line in seal.read_text().splitlines():
  h,n=line.split('  ',1);p=E/n;require(not Path(n).is_absolute()and'..'not in Path(n).parts and sha(p)==h,'actual04 sealed member '+n)
 pre=load(E/'fresh-unit-tool-prepins.json');post=load(E/'fresh-unit-tool-postpins.json');require(pre['pins']==post['pins'] and post['fresh_pre_post_exact']is True and post['all_actual_trace_steps']==41,'actual04 tool pre/post')
 require(load(E/'pre-input-pins.json')==load(E/'post-input-pins.json'),'actual04 input pre/post');traces=sorted(E.glob('*-trace-contract.json.gz'));require(len(traces)==41,'41 trace contracts')
 for p in traces:
  t=json.loads(gzip.decompress(p.read_bytes()));require(t['actual_returncode']==0 and t['result']['status']=='PASS_EXACT_PREPINNED_TRACE','qualified actual trace '+p.name)
 require(sha(E/'program.bin')==RAW and sha(B/'program.bin')==RAW and sha(E/'re4dc-game.elf')==ELFH and sha(B/'re4dc-game.elf')==ELFH,'both actual output mirrors');elf=Elf((E/'re4dc-game.elf').read_bytes());require(elf.raw()==(E/'program.bin').read_bytes(),'independent PT_LOAD/raw')
 text=elf.section(elf.sections['.text']);iid=[fnv(text[:len(text)//4*4]),len(text)//4*4];require(iid==q['image_ID'],'text image ID');val,n,sec=elf.symbols['_re4dc_image_id'];s=elf.sh[sec];require(list(struct.unpack_from('<2I',elf.section(sec),val-s[3]))==iid,'embedded image ID')
 files=[dict(name='program.bin',Windows_path=win(E/'program.bin'),bytes=(E/'program.bin').stat().st_size,sha256=RAW)];ovs=[]
 for r in q['overlays']:
  p=E/r['name'];blob=p.read_bytes();require(sha(p)==r['sha256']==sha(B/r['name']) and len(blob)==r['bytes'],'overlay C/WSL identity');h=overlay(blob,iid,r['header'][4],r['original_slot_bytes']);require(h==r['header'],'actual header');files.append(dict(name=r['name'],Windows_path=win(p),bytes=len(blob),sha256=sha(p),header=h));ovs.append(r['name'])
 require(len(files)==15 and len(set(ovs))==14,'exact15')
 # Real loaded consumer bytes, not source identity or a macro label alone.
 ui=q['stack_reference']['native_ui']['raw'];up=Path(ui['path']);require(sha(up)==ui['sha256'],'qualified UI object');obj=Elf(up.read_bytes());st=q['stack_reference']['native_static']['raw'];require(sha(st['path'])==st['sha256'],'qualified static object');static=Elf(Path(st['path']).read_bytes());tableproof=[]
 for name,count,width in [('__ZN5re4dc6rect219qualifiedE',792,52),('__ZN5re4dc6rect2110provenance12certificatesE',27,40)]:
  a=elf.blob(name);b=(static if 'provenance' in name else obj).blob(name);require(len(a)==count*width and a==b,'actual linked consumer '+name);tableproof.append(dict(symbol=name,rows=count,stride=width,bytes=len(a),sha256=hashlib.sha256(a).hexdigest()))
 src=Path('/root/probe/codex-mipmap21-next792/port/dreamcast/tools/d367/texture_rect21');rows=[]
 for l in(src/'scoped_representations.inc').read_text().splitlines():
  if not l.startswith('{'):continue
  v=[x for x in re.split(r'[{},\s]+',l)if x];require(len(v)==13,'descriptor source fields');rows.append(struct.pack('<11I2f',*[int(x.rstrip('Uu'),0)for x in v[:11]],*[float(x.rstrip('Ff'))for x in v[11:]]))
 require(b''.join(rows)==elf.blob('__ZN5re4dc6rect219qualifiedE'),'source792 packed values equal actualELF')
 crcpath=Path('/root/re4data/private/texture-consumers21-next792-runner-20261022/future792-CRC-callpath.json');crc=load(crcpath);pkg=crc['future_reused_Package_object'];require(sha(pkg['path'])==pkg['sha256'],'inherited actual Package object');base=json.loads(gzip.decompress((E/'base-link-trace-contract.json.gz').read_bytes()));require(sum(p['pin']['sha256']==pkg['sha256']and p['pin']['resolved']==str(Path(pkg['path']).resolve())for p in base['contract']['inputs'])==1,'actual link consumed Package object')
 canonical=load(Path(crc['pins'][3]['path']));need=('CAST_MIPMAP','TEX_TWIDDLED_MIPMAP','TEX_PAL4_ALPHA','TEX_PAL4_MIPMAP','TEX_PAL8_ALPHA','TEX_PAL8_MIPMAP');require(sha(crc['pins'][3]['path'])==crc['pins'][3]['sha256'],'canonical format contract pin');require(all('-DRE4DC_'+k+'=1'in canonical['inherited_texture_Package_command']and canonical['texture_Package_required_ON_flags'][k]is True and crc['Package_six_format_flags'][k]is True for k in need),'six inherited actual flags');require(crc['Package_RESIDENT']==1 and crc['Package_PAYLOAD_CRC']==0,'CRC policy')
 if independent is None:
  print(json.dumps(dict(status='READ_ONLY_PREFLIGHT_PASS',raw=RAW,ELF=ELFH,overlays=len(ovs),linked_tables=tableproof,actual41_traces=True,admission_written=False)));return
 ind=load(independent);require(ind['source']==SOURCE and ind['ELF_sha256']==ELFH and ind['programme_sha256']==RAW and ind['fullprogram_source_gate']is True and ind['source_or_external_inputs_changed_during_unit']is False and ind['all14_header_payload_relocation_CRC_and_newprogramme_binding_pass']is True,'independent reader proof join')
 OUT.mkdir();proof=write('ROOT-BYTE-PROOF.json',dict(source=SOURCE,raw=RAW,ELF=ELFH,image_ID=iid,all14=ovs,loaded_consumer=tableproof,tool_traces=41,source_object_linked_values_exact=True,independent_reader=spec(independent),scope='Source/object/link and actual byte validation; no target/GPU/performance/release/hardware acceptance'))
 consumer=write('LINKED-CONSUMER.json',dict(source=SOURCE,new_programme_qualified=True,all_consumer_gates_qualified=True,ELF_sha256=ELFH,programme_sha256=RAW,proof=proof,source_format_contract=dict(path='/root/re4data/private/texture-consumers21-next792-runner-20261022/future792-CRC-callpath.json',sha256=sha(crcpath)),scope='All source/object/linked consumer gates only; target filtered appearance and performance remain open'))
 tool=write('TOOL-CLOSURE.json',dict(source=SOURCE,qualified=True,complete_actual_exec_plugin_tool_closure=True,new_unit_pre_post=True,unit='mipmap04',sealed_unit=spec(seal),pre=spec(E/'fresh-unit-tool-prepins.json'),post=spec(E/'fresh-unit-tool-postpins.json'),all41_traces=41))
 iq=spec(independent);qual=write('QUALIFICATION.json',dict(source=SOURCE,full_source_programme_gate=True,source_inputs_immutable=True,ELF_sha256=ELFH,programme_sha256=RAW,all14_new_ELF_bound=True,independent_qualification_sha256=iq['sha256'],mip_PAL_flags_ON={k:True for k in need},actual04=spec(E/'qualification.json'),root_byte_proof=proof))
 manifest=write('PROGRAMME-MANIFEST.json',dict(runtime_source=SOURCE,qualification_sha256=qual['sha256'],programme_sha256=RAW,image_id=iid,ELF=dict(Windows_path=win(E/'re4dc-game.elf'),bytes=(E/'re4dc-game.elf').stat().st_size,sha256=ELFH),files15=files,boot_convention='RAW program.bin staged as /1ST_READ.BIN, preserving reviewed V2 and original M0 raw convention; separate scrambled_boot is not substituted'))
 admission=write('ADMISSION.json',dict(schema='qualified792-programme-stage-admission-v1',qualified=True,source=SOURCE,qualification=qual,independent=iq,consumer=consumer,tool_closure=tool,manifest=manifest,actual_texture_crc_policy=dict(resident=1,payload_crc=0)))
 write('RESOURCE.json',dict(charged_with_reserve=guard(),cap=CAP,no_image_or_guest=True));print(json.dumps(admission))

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--independent',type=Path);a=p.parse_args();main(a.independent)
