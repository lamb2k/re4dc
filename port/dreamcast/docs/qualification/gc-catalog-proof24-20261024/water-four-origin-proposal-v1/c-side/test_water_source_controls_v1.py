#!/usr/bin/env python3
"""RAM-only entry-boundary and full-identity controls for the four stored outputs."""
import hashlib,importlib.util,json,struct,sys
from pathlib import Path
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
sp=importlib.util.spec_from_file_location('water',HERE/'check_water_targets_v2.py');W=importlib.util.module_from_spec(sp);sp.loader.exec_module(W);A=W.A
checkpath=HERE/'run-02/CHECKS.json';assert A.sha(checkpath.read_bytes())=='382e3639a609ec38932e571e76d566fec78015f0d1b4ff2ac26eee88e7a47af8';c=json.loads(checkpath.read_bytes());assert c['matched_identities']==4
core=Path('/root/re4data/private/worldfx-20261018/ps2/Core.dat').read_bytes();assert A.sha(core)==c['source_members']['Core.dat']['member']['sha256'];n=struct.unpack_from('<I',core)[0];offs=struct.unpack_from('<%dI'%n,core,16)
def eff(entry):
 assert core[16+4*n+4*entry:20+4*n+4*entry].rstrip(b'\0')==b'EFF';return core[offs[entry]:offs[entry+1] if entry+1<n else len(core)]
def ids(e):
 assert struct.unpack_from('<I',e)[0]==11;o=struct.unpack_from('<I',e,4)[0];count=struct.unpack_from('<I',e,o)[0];assert 0<count<4096;return [struct.unpack_from('<H',e,o+4+8*i)[0] for i in range(count)]
wrong=eff(25);correct=eff(1);assert 0x1d in ids(wrong) and 0x1d in ids(correct)
controls={'actual_duplicate_ID_in_EFF1_and25':True,'wrong_EFF25_full_SHA_rejected':A.sha(wrong)!=c['source_members']['Core.dat']['eff_sha256'],'changed_original_member_byte_rejected':A.sha(bytes([core[0]^1])+core[1:])!=c['source_members']['Core.dat']['member']['sha256']}
with Path(c['results'][0]['selected']['path']).open('rb') as fp:
 for r in c['results']:
  s=r['selected'];blob=A.read_at(fp,s['offset'],s['bytes']);assert A.sha(blob)==s['full_payload_sha256']==r['sha256']
  bad=bytearray(blob);bad[-1]^=1;assert A.sha(bad)!=r['sha256'];controls[r['id']+'_tail_mutation_rejected']=True
  assert A.sha(b'wrong-key'+blob)!=A.sha(r['id'].encode()+blob);controls[r['id']+'_wrong_key_rejected']=True
  if r['variant']=='composed_mip':
   controls['base_only_hash_cannot_qualify_current_mip']=r['base_sha256']!=r['sha256'] and r['base_bytes']<r['bytes']
  if r['variant']=='lossless_vq':
   bad=bytearray(blob);bad[144]^=1;assert A.sha(bad)!=r['sha256'];controls['VQ_codebook_mutation_rejected']=True
   controls['PAL4_base_cannot_qualify_current_VQ']=r['base_sha256']!=r['sha256'] and r['base_bytes']>r['bytes']
assert all(controls.values())
record={'schema':1,'status':'PASS','controls':controls,'count':len(controls),'wrong_duplicate':{'member':'Core.dat','entry':25,'same_texture_ID':'0x1d','EFF_bytes':len(wrong),'EFF_sha256':A.sha(wrong),'expected_EFF_entry':1,'expected_EFF_sha256':A.sha(correct)},'assets_RAM_only':True,'asset_files_written':0,'live_Entry_or_EST_recipe_proved':False,'helper':A.pin(Path(__file__))};out=HERE/'SOURCE-CONTROLS.json';assert not out.exists();out.write_bytes(A.enc(record));print(json.dumps(record,indent=2))
