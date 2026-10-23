"""Current receipt join, requiring independent final pins before preparation."""
from pathlib import Path
import json,re
from binding_helpers import checked_json,native_path,pin
from policy import FINAL_SOURCE,INTEGRATION
from validate_bindings import current_programme,ownership_contract
from material_identity import require_bound_receipt
P=Path(__file__).resolve().parent
NORMALIZATION_SHA='4b92505d6ba41438829f3af1e1bf8286c1e824c27dd756f6f96203c64ed6c5a7'
PROGRAMME_SHA='41beee7f50af4ff50c49b03a7cfa53d794086646322c5ebe7a85ffc7805a883d'
def pending_safe_binding():
 b=json.loads((P/'BINDINGS.json').read_bytes())
 if b.get('source')!=FINAL_SOURCE or b.get('runtime_admitted') is not False or b.get('stage')!='PENDING_ACTUAL_FRESH_STAGE':raise ValueError('exact unadmitted source binding required')
 for name in ('programme','ownership_audit','kos_receipt','module_roster','normalization_source_seal','normalization_review'):
  row=b[name]
  if not isinstance(row.get('path'),str) or row['path']=='PENDING' or not re.fullmatch('[0-9a-f]{64}',row.get('sha256','')):raise ValueError('PENDING external exact binding: '+name)
 if b['programme']['sha256']!=PROGRAMME_SHA or b['normalization_source_seal']['sha256']!=NORMALIZATION_SHA:raise ValueError('exact f240 programme/normalization binding differs')
 return b
def verify_bound(inputs):
 b=pending_safe_binding();pin(P/'BINDINGS.json',inputs);root=P.parent/'native-normalize-f240r1'
 require_bound_receipt(b['normalization_source_seal'],dict(path=str(root/'SOURCE-SEAL.json'),sha256=NORMALIZATION_SHA),native_path)
 seal=checked_json(b['normalization_source_seal']['path'],NORMALIZATION_SHA,inputs)
 if seal.get('source')!=FINAL_SOURCE or seal.get('runtime_admitted') is not False:raise ValueError('normalization source/runtime identity differs')
 for name,row in seal['files'].items():
  path=root.parent/name
  if not path.resolve().is_relative_to(root.resolve()):raise ValueError('source seal escape')
  actual=pin(path,inputs,row['sha256'])
  if actual.stat().st_size!=row['bytes']:raise ValueError('normalization file extent differs')
 review=checked_json(b['normalization_review']['path'],b['normalization_review']['sha256'],inputs)
 if review.get('status')!='CLEAR' or review.get('normalization_source_seal_sha256')!=NORMALIZATION_SHA:raise ValueError('independent exact normalization review required')
 require_bound_receipt(b['programme'],dict(path=str(root/'bound/on/programme.json'),sha256=PROGRAMME_SHA),native_path)
 refs=dict(integration=INTEGRATION,programme_receipt=b['programme']['path'],programme_receipt_sha256=PROGRAMME_SHA,**{key:b[key] for key in ('ownership_audit','kos_receipt','module_roster')})
 programme,_=current_programme(refs,FINAL_SOURCE,inputs);ownership_contract(refs,programme,FINAL_SOURCE,inputs)
 if programme['arm']!='on' or programme['original_receipts']['coverage_source_review']['full_masks']!=[0xd80,0xd80]:raise ValueError('only exact existing full-coverage ON programme')
 return b
