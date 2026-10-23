"""Read current private source proof only; no actual programme normalization."""
from pathlib import Path
import hashlib,json
from binding_helpers import native_path
from policy import SOURCE_HEAD,EVIDENCE_ROOT
P=Path(__file__).resolve().parent
PRIVATE_SEAL=P.parent/'coverage23/SOURCE-AND-SUCCESSOR-SEAL.json'
PRIVATE_SEAL_SHA='88074289fd127d294d12555519fc0078db0fe282fd212e3ae06c7ff6b4c8f82c'
REVIEW=P.parent/'review/COVERAGE23-GENERATOR-REVIEW.md'
REVIEW_SHA='5167cfa609b435da5dcb3286a7b4ce6f94a7b02eee11e2424082b62565d0d83e'
HEADER_SHA='f9512e2395118fee167cc01032742f38a353b6776b29f2343bbd4808e2a006e9'
def digest(data):return hashlib.sha256(data).hexdigest()

def private_readback(read=lambda p:native_path(p).read_bytes()):
 records=[]
 def checked(path,pin,size=None):
  data=read(path)
  if digest(data)!=pin or(size is not None and len(data)!=size):raise ValueError('current private source/review input differs: '+str(path))
  records.append(dict(path=str(path),bytes=len(data),sha256=pin));return data
 seal=json.loads(checked(PRIVATE_SEAL,PRIVATE_SEAL_SHA));checked(REVIEW,REVIEW_SHA)
 if seal['source_commit']!=SOURCE_HEAD or seal['origin_verified_commit']!=SOURCE_HEAD or seal['required_masks']!=['0xd80','0xd80']or seal['source_runtime_edits']is not False:raise ValueError('reviewed generator-only correction identity differs')
 for name,row in seal['private_files'].items():checked(Path(seal['private_successor'])/name,row['sha256'],row['bytes'])
 for row in seal['source_files'].values():checked(Path(row['path']),row['sha256'],row['bytes'])
 for key in('verification','host_results','private_verifier'):
  row=seal[key];checked(Path(row['path']),row['sha256'])
 return dict(status='EXACT_REVIEWED_PRIVATE_SOURCE_ONLY',source_head=SOURCE_HEAD,private_header_sha256=HEADER_SHA,required_full_masks=[0xd80,0xd80],records=records,actual_programme='PENDING',runtime_acceptance=False)
