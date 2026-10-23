"""Exact external recovery review. Never restores or accesses an image itself."""
from pathlib import Path
import hashlib,json,re
P=Path(__file__).resolve().parent
def require_recovery():
 row=json.loads((P/'RECOVERY-BINDING.json').read_bytes())
 for name in ('result','review'):
  item=row[name]
  if item.get('path')=='PENDING' or not re.fullmatch('[0-9a-f]{64}',item.get('sha256','')):raise ValueError('PENDING exact ce034 recovery '+name)
  path=Path(item['path'])
  if hashlib.sha256(path.read_bytes()).hexdigest()!=item['sha256']:raise ValueError('recovery receipt changed')
 result=json.loads(Path(row['result']['path']).read_bytes());review=json.loads(Path(row['review']['path']).read_bytes())
 if result.get('status')!='EXACT_CE034_RECOVERED' or result.get('recovered_sha256')!='ce034ff75d5c6eb125a5036b5c55afa1805de1beac75711cd41b73f366d854ad':raise ValueError('exact ce034 recovery result required')
 if review.get('status')!='CLEAR' or review.get('recovery_result_sha256')!=row['result']['sha256']:raise ValueError('independent exact ce034 recovery review required')
 return row
