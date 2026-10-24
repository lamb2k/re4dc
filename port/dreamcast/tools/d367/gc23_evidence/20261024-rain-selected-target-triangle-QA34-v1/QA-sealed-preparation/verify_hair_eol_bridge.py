"""Exact invertible historical EOL bridge; does not alter a private header."""
from pathlib import Path
import hashlib,json
HERE=Path(__file__).resolve().parent
HEADER=Path('/root/probe/lanes-20261011/pl08/assets/arm-a/ps2leon_hair_runs.h')
REPORT=HEADER.with_name('report.json')
CURRENT='c63bce3f7c963374060a35bf9944786e2579e21702d989fd154aceb8cb862884'
HISTORIC='d91affd750a5b9ca8ec38a4720448e83c7290df09e6dfea5856ecaf6741c7a63'
def sha(b):return hashlib.sha256(b).hexdigest()
def verify(current,expected):
 if len(current)!=22446 or sha(current)!=CURRENT or b'\r' in current:raise ValueError('Noncanonical current LF header')
 if expected!=HISTORIC:raise ValueError('Wrong historical report binding')
 historic=current.replace(b'\n',b'\r\n')
 if len(historic)!=22769 or sha(historic)!=expected or historic.replace(b'\r\n',b'\n')!=current:raise ValueError('Historical EOL preimage mismatch')
 return historic

def main():
 current=HEADER.read_bytes();report=json.loads(REPORT.read_text());historic=verify(current,report['headers'][HEADER.name]);census=json.loads((HERE/'DEPENDENCY-CENSUS.json').read_text());item=census['unrecorded_externals'][str(HEADER)];assert item['identity']==dict(bytes=len(current),sha256=CURRENT)
 consumers=item['consumers'];assert {x['arm'] for x in consumers}=={'QA-baseline','QA-off','QA-on','normal-off','normal-on'}
 controls=[]
 for name,data,expected in [('changed-array',current.replace(b'0,100,128',b'1,100,128',1),HISTORIC),('inserted-space',current+b' ',HISTORIC),('missing-final-newline',current[:-1],HISTORIC),('existing-CR',b'\r'+current,HISTORIC),('wrong-report',current,'0'*64),('CRLF-as-current',historic,HISTORIC)]:
  try:verify(data,expected)
  except ValueError as e:controls.append(dict(name=name,refused=True,reason=str(e)))
  else:raise AssertionError('Bridge admitted altered source '+name)
 copy=Path('/mnt/c/Game Dev/Emulators/re4-assets-private/ps2leon-pl08-20261011/arm-a/ps2leon_hair_runs.h');assert copy.read_bytes()==current
 result=dict(status='EXACT_INVERTIBLE_EOL_BRIDGE_SOURCE_FACTS_ROOT_REVIEW_PENDING',scope='Existing historical report hash has an exact CRLF preimage of current LF bytes; this is supplemental asset identity, never a retroactive original QA prehash',current=dict(path=str(HEADER),bytes=len(current),sha256=CURRENT,no_CR=True,LF_count=current.count(b'\n')),historical_report=dict(path=str(REPORT),bytes=REPORT.stat().st_size,sha256=sha(REPORT.read_bytes()),member=HEADER.name,expected_sha256=report['headers'][HEADER.name]),reconstructed_historical=dict(bytes=len(historic),sha256=sha(historic),transform='Insert exactly one CR before every current LF',reverse='Replace every reconstructed CRLF with LF',invertible=True,all_other_bytes_identical=True),named_NTFS_asset_copy=dict(path=str(copy),bytes=copy.stat().st_size,sha256=sha(copy.read_bytes())),all5_actual_consumers=consumers,mutation_controls=controls,original_census_sha256=sha((HERE/'DEPENDENCY-CENSUS.json').read_bytes()),original_HOLD_preserved=True,correction='Earlier inference that current0CRLF ruled out an EOL explanation was premature. Current LF -> historical CRLF exactly matches the report. The initial census raw hash mismatch remains true and unchanged.',tool_sha256=sha(Path(__file__).read_bytes()),SDK_run=False,asset_modified=False,stage_run=False)
 with (HERE/'HAIR-EOL-BRIDGE.json').open('x') as f:json.dump(result,f,indent=1);f.write('\n')
 print(json.dumps(dict(current=CURRENT,reconstructed=sha(historic),controls=len(controls),all5_consumers=len(consumers))))
if __name__=='__main__':main()
