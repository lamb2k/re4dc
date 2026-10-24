"""V2 preflight refusal for unauthenticated native sparse backing; never opens a process."""
import argparse,hashlib,json,pathlib,re,sys
SOURCE='49ad20f9932d638ddb7becf5db6f86b92e0a76a2'
LEGACY_RECEIPT='d7026d14e8a096469eac12aed583767ce135b8ef3b0ab8a10c78c00428354835'
class UnsupportedNativeBacking(ValueError):pass
class InvalidBackingProof(ValueError):pass
def sha(b):return hashlib.sha256(b).hexdigest()
def exact_knobs(text):
 out={}
 for name in ('ENEMY_DEMAND','OBJECT_DEMAND'):
  found=re.findall(r'^'+name+r'=(.*)$',text,re.M)
  if len(found)!=1 or found[0] not in ('0','1'):raise InvalidBackingProof('missing/ambiguous '+name)
  out[name]=int(found[0])
 return out
def backing_verdict(knobs):
 return {'source':SOURCE,'status':'UNSUPPORTED_NATIVE_BACKING','observer_runtime_supported':False,'strict_pixel_qualified':False,'manager_backing':{'EmMgr':{'demand':knobs['ENEMY_DEMAND'],'contract':'native sparse Pool64/slot table and two-slot cEm pages','authenticated_sparse_reader':False},'ObjMgr':{'demand':knobs['OBJECT_DEMAND'],'contract':'native sparse Pool64/slot table and eight-slot cObj pages','authenticated_sparse_reader':False}},'reason':'V1 contiguous pArray+n*stride ownership is invalid for current native sparse backing. V2 implements no sparse ownership reader and refuses before process access. This is unsupported observation, not game corruption.','completed_state_limit':'Completed actor/viewport/upload-owner pixel binding remains unsupported; no watchdog/framebuffer observation upgrades this claim.'}
def require_supported_backing(profile_text):
 knobs=exact_knobs(profile_text)
 # No caller-supplied fallback to contiguous indexing or an Em2-only policy.
 # A flags0/different recipe also needs a separately authenticated implementation.
 raise UnsupportedNativeBacking(json.dumps(backing_verdict(knobs),sort_keys=True))
def authenticate(proof,profile,parts,legacy):
 if proof['source']!=SOURCE:raise InvalidBackingProof('source mismatch')
 for key,value in [('profile_sha256',profile),('parts_source_sha256',parts),('legacy_receipt_sha256',legacy)]:
  if sha(value)!=proof[key]:raise InvalidBackingProof('pin mismatch '+key)
 if sha(legacy)!=LEGACY_RECEIPT:raise InvalidBackingProof('sealed V1 receipt changed')
 required=['template<> constexpr bool demand<cObj> = RE4DC_OBJECT_DEMAND;','template<> constexpr bool demand<cEm> = RE4DC_ENEMY_DEMAND;','T** slots() { return (T**)(this + 1); }','m->pArray=(T*)p;register_pool(m);','return sparse(m)?pool(m)->slots()[no]:(T*)((u8*)m->pArray+m->size*no);','const u32 first=i&~7U, count=nArray-first<8?nArray-first:8;','const u32 first=i&~1U, count=nArray-first<2?nArray-first:2;']
 text=parts.decode()
 if any(s not in text for s in required):raise InvalidBackingProof('actual sparse source contract changed')
 return exact_knobs(profile.decode())
def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--proof',required=True);ap.add_argument('--profile',required=True);ap.add_argument('--parts-source',required=True);ap.add_argument('--legacy-receipt',required=True);ap.add_argument('--refusal-output',required=True);a=ap.parse_args()
 proof=json.loads(pathlib.Path(a.proof).read_text());profile=pathlib.Path(a.profile).read_bytes();parts=pathlib.Path(a.parts_source).read_bytes();legacy=pathlib.Path(a.legacy_receipt).read_bytes()
 knobs=authenticate(proof,profile,parts,legacy);out=pathlib.Path(a.refusal_output)
 if out.exists():raise InvalidBackingProof('existing refusal output refused')
 result=backing_verdict(knobs);result.update(proof_sha256=sha(pathlib.Path(a.proof).read_bytes()),legacy_receipt_sha256=sha(legacy),process_opened=False,guest_started=False)
 out.write_text(json.dumps(result,indent=2)+'\n');print(result['status']);return 3
if __name__=='__main__':sys.exit(main())