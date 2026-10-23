"""Exact coverage source/private/virtual dependencies; final programme slots fail closed."""
from pathlib import Path
import hashlib,json,os,re
HERE=Path(__file__).resolve().parent
LANE=HERE.parent
SOURCE='f2405bb06ebaff6e2a7681479d5308ec5d3b988a'
ACTOR_SOURCE='7997bc3312e02e4c6c6849a8b7c7f8a5fd928ac5'
INTEGRATION='0b4beb704902a1dc6b2aace056be344863b4a0c1'
PREDECESSOR=LANE/'package10395'
PREDECESSOR_SEAL_SHA='cb3b1dc9f2e8246626849bb6e89e95bb9afaeb7855fcb5c153cb303b229056cf'
ADAPTER=LANE/'native-runtime10395'
ADAPTER_SHA='066aa234a6a6573fe3b40d7597d8fcb892aa41883e966d15945752161651d8c4'
CENSUS=LANE/'material-census23-run'
CENSUS_SHA='PENDING'
PREPARED=LANE/'package-coverage23'
PREPARATION_SHA='cbc6bbcc0c0a1d71a7e1a5facde388a3c193d9090ffb35a3131c909da0eb5056'
FIXTURE_SHA='6b28db8cdec172110720ab105fd9c3ce68b15f10d4607eb207dc19829d43cbe3'
BASIS_SHA='9bb15f9878843c6fdad1783afa0aef297ce63a4a3be0710302c110a63376c76c'
PAD_SHA='073552789fad65c4057fa83303f10ac18ff9bc00ae48f195762be982c3222ff9'
MEMORY_REFERENCE=LANE.parent/'world-scratch23/memory-wrapper2158r2'
MEMORY_REFERENCE_SHA='a6006a228e9e33b48eb8e2d73fb24a529b1b7e8390e5b0aa57090d8cd513342a'
MEMORY_REVIEW_SHA='1b21b55b9ef87bacee0ac1d96e8fff6c32c5d24479ac58d649c028e4109df23c'
RECOVERY=LANE.parent/'world-scratch23/recovery-native-base'
RECOVERY_SHA='6ac95b80291fbd1ac5ab173f01e96602c68a75d1e4b6aa0d535834c6986bf080'
VIRTUAL_MANIFEST='/root/probe/pvs23-package-20261022-v1/recovery-inverse-native-base-both/virtual-base.json'
VIRTUAL_MANIFEST_SHA='064f01bc58fd8a275b959e3138f051ff9f14702a5b3988fa02039c7989dcad1d'
INVERSE_PLAN_SHA='0931bebdffd6776ebb2b1a287a1a78661e2cf8d6ee306998ce708a3d61fb544b'
RECOVERY_RESULT_SHA='da43f02358615828e2d15e6644850b077427acd41e263bbb424ee05dc2fb0e1f'
ORIGINAL_ISO_SHA='1baf232710c6360bc11415f6ec199ef794672cc7fdfa2310d7b2b2f84a2b08d5'
ORIGINAL_ISO_BYTES=1024653312
ACTOR_ISO='/mnt/c/Flycast-Evidence/re4-dreamcast/pvs23-20261022/actor23-10395a10-on-q01/base/track03.iso'
ACTOR_ISO_SHA='ce034ff75d5c6eb125a5036b5c55afa1805de1beac75711cd41b73f366d854ad'
ACTOR_ISO_BYTES=1028911104
PRIVATE_ROOT='/mnt/c/Game Dev/Emulators/codex-lanes/actor-visibility23/coverage23/private-successor-final'
BUILD_ROOT='/root/probe/lanes/actor-visibility23-coverage-integration'
BUILD_PRIVATE_ROOT=BUILD_ROOT+'/certificate'
BUILD_READBACK_SHA='3b6d907eda7c1df2fee8455b6696a7a62200da900e7e4f93754f4539dbb8828d'
BUILD_PREPARATION_SHA='5956a55db20fd21138af8d2fca91fd364da28b43e9373f68cbfc148d4ab9b78b'
BUILD_ALLOCATION_SHA='0ec6baa7a07075e6abbf7b17789796e7c3812ca5a798f238f0e608b7baf15627'
OLD_PRIVATE_READBACK='/root/probe/lanes/actor-visibility23-integration/PRIVATE-INPUTS-READBACK.json'
OLD_PRIVATE_READBACK_SHA='d90d716218572c23f1f7cb135f7575e1d26c04fbc1c62aac7e1acb590de95257'
HEADER_SHA='f9512e2395118fee167cc01032742f38a353b6776b29f2343bbd4808e2a006e9'
COVERAGE_SEAL=LANE/'coverage23/SOURCE-AND-SUCCESSOR-SEAL.json'
COVERAGE_SEAL_SHA='88074289fd127d294d12555519fc0078db0fe282fd212e3ae06c7ff6b4c8f82c'

def sha(p):
 with Path(p).open('rb')as f:return hashlib.file_digest(f,'sha256').hexdigest()
def local(value):
 s=str(value).replace('\\','/')
 if os.name=='nt':
  if s.startswith(('/root/','/opt/')):return Path('\\\\wsl.localhost\\Ubuntu-24.04'+s.replace('/','\\'))
  if s.startswith('/mnt/c/'):return Path('C:/'+s[7:])
 else:
  if re.match('(?i)^C:/',s):s='/mnt/c/'+s[3:]
  for prefix in('//wsl.localhost/Ubuntu-24.04/','//wsl$/Ubuntu-24.04/'):
   if s.lower().startswith(prefix.lower()):s='/'+s[len(prefix):]
 return Path(s)

def require_final_bindings(a):
 import sys
 sys.path.insert(0,str(CENSUS))
 from bindings import verify_bound
 from material_identity import require_bound_receipt
 binding=verify_bound({})
 if a.arm!='on' or a.source!=SOURCE or a.adapter_seal_sha256!=CENSUS_SHA or sha(CENSUS/'SOURCE-SEAL.json')!=CENSUS_SHA:raise ValueError('exact material census ON source/seal required')
 for field in ('programme','ownership_audit','kos_receipt','module_roster'):
  require_bound_receipt(dict(path=getattr(a,field),sha256=getattr(a,field+'_sha256')),binding[field],local)
 return binding

def validate_census_data(fixtures,raw,basis,pad,pad_basis):
 if set(fixtures)!={'r119-census'}:raise ValueError('sole exact census case required')
 row=fixtures['r119-census']
 expected={'path','sha256','basis_path','basis_sha256','pad_path','pad_sha256','pad_basis_path','pad_basis_sha256'}
 if set(row)!=expected:raise ValueError('exact census fixture fields required')
 if(local(row['path']),local(row['pad_path']))!=(CENSUS/'fixtures/r119-census.txt',CENSUS/'fixtures/r119-movie-pad.txt'):raise ValueError('exact census local fixtures required')
 if local(row['basis_path'])!=LANE.parent/'backface-sh4zam/claude-scripts/scenes/g8.txt'or local(row['pad_basis_path'])!=local('/mnt/c/Flycast-Evidence/re4-dreamcast/boss18-20261018/warps/r119-skip-intro-pad-6400.txt'):raise ValueError('exact retained census fixture bases required')
 if(row['sha256'],row['basis_sha256'],row['pad_sha256'],row['pad_basis_sha256'])!=(FIXTURE_SHA,BASIS_SHA,PAD_SHA,PAD_SHA):raise ValueError('census fixture pins differ')
 digest=lambda data:hashlib.sha256(data).hexdigest()
 if digest(basis)!=BASIS_SHA or raw!=basis+b'goto 300 112950 2298.247 19750 3.14159265\r\nlate 0x20 539 0x119\r\n'or digest(raw)!=FIXTURE_SHA:raise ValueError('exact g8 prefix/goto/late no-hold census bytes required')
 if pad!=pad_basis or digest(pad)!=PAD_SHA:raise ValueError('byte-exact original normal movie input required')
 return fixtures

def census_fixture_contract(pin):
 path=CENSUS/'fixtures.json';pin(dict(path=str(path),sha256=sha(path)))
 fixtures=json.loads(path.read_text())
 if set(fixtures)!={'r119-census'}:raise ValueError('sole exact census case required')
 row=fixtures['r119-census']
 raw=pin(dict(path=row['path'],sha256=row['sha256'])).read_bytes()
 basis=pin(dict(path=row['basis_path'],sha256=row['basis_sha256'])).read_bytes()
 pad=pin(dict(path=row['pad_path'],sha256=row['pad_sha256'])).read_bytes()
 pad_basis=pin(dict(path=row['pad_basis_path'],sha256=row['pad_basis_sha256'])).read_bytes()
 return path,validate_census_data(fixtures,raw,basis,pad,pad_basis)

def normalized_actual_private(private,pin):
 from material_private import normalized_actual_private as actual
 return actual(private,pin)

def verify_source_dependencies():
 records={}
 def pin(path,digest):
  if sha(path)!=digest:raise ValueError('source dependency changed: '+str(path))
  records[str(path)]=digest
 pin(ADAPTER/'SOURCE-SEAL.json',ADAPTER_SHA)
 pin(LANE/'package-coverage-census23/contracts.py','0b40b840d8a6012545555e37450251dc1dcfc9c230143b4d950174cf3b50e734')
 if CENSUS_SHA=='PENDING':raise ValueError('PENDING final census source seal')
 pin(CENSUS/'SOURCE-SEAL.json',CENSUS_SHA)
 census=json.loads((CENSUS/'SOURCE-SEAL.json').read_text())
 for name,row in census['files'].items():
  name=name.replace('\\','/')
  if Path(name).is_absolute()or '..'in Path(name).parts:raise ValueError('unsafe census sealed member')
  path=CENSUS/name
  if path.stat().st_size!=row['bytes']:raise ValueError('census source member extent differs')
  pin(path,row['sha256'])
 census_fixture_contract(lambda row:(pin(local(row['path']),row['sha256']),local(row['path']))[1])
 pin(PREPARED/'PREPARATION-SEAL.json',PREPARATION_SHA)
 for name,row in json.loads((PREPARED/'PREPARATION-SEAL.json').read_text())['files'].items():pin(PREPARED/name,row['sha256'])
 pin(PREDECESSOR/'PACKAGE-SOURCE-SEAL.json',PREDECESSOR_SEAL_SHA)
 pin(MEMORY_REFERENCE/'SOURCE-SEAL.json',MEMORY_REFERENCE_SHA);pin(MEMORY_REFERENCE/'REVIEW-CLEAR.json',MEMORY_REVIEW_SHA)
 for root,name in((ADAPTER,'SOURCE-SEAL.json'),(MEMORY_REFERENCE,'SOURCE-SEAL.json'),(PREDECESSOR,'PACKAGE-SOURCE-SEAL.json')):
  seal=json.loads((root/name).read_text())
  for name,row in seal['files'].items():
   path=root/name
   if path.stat().st_size!=row['bytes']:raise ValueError('source dependency extent changed')
   pin(path,row['sha256'])
 pin(COVERAGE_SEAL,COVERAGE_SEAL_SHA);coverage=json.loads(COVERAGE_SEAL.read_text())
 if coverage['source_commit']!='bea2d402ba06d41fb7b39946b5a9431a72f5b52a':raise ValueError('coverage source lineage differs')
 for row in coverage['source_files'].values():pin(local(row['path']),row['sha256'])
 for name,row in coverage['private_files'].items():pin(local(PRIVATE_ROOT)/name,row['sha256'])
 from recovery_binding import require_recovery
 require_recovery()
 from virtual_base import verify_metadata
 _,virtual=verify_metadata();records.update(virtual)
 return records

def require_review(path,pin):
 if not path or not pin:raise ValueError('exact independent actor package source review required')
 p=local(path)
 if sha(p)!=pin:raise ValueError('package source review changed')
 review=json.loads(p.read_text());seal=HERE/'SOURCE-SEAL.json'
 if not seal.is_file()or review.get('status')!='CLEAR'or review.get('actor_package_source_seal_sha256')!=sha(seal):raise ValueError('review must bind exact sealed final actor package source')
 for name,row in json.loads(seal.read_text())['files'].items():
  if sha(HERE/name)!=row['sha256']:raise ValueError('sealed package source changed')
 return review
