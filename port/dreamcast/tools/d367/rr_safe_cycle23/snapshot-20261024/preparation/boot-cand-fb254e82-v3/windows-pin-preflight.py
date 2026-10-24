"""Read-only actual Windows input-pin preflight. Never imports/executes adapter."""
import datetime,hashlib,json,pathlib,sys,time
config=pathlib.Path(sys.argv[1]);output=pathlib.Path(sys.argv[2])
assert sys.platform=='win32'
assert not output.exists()
def sha(p):
 h=hashlib.sha256()
 with pathlib.Path(p).open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
cfg=json.loads(config.read_text())
assert cfg['status']=='ROOT-REVIEW-PENDING' and not cfg['execution_authorized']
assert cfg['adapter_source_commit']=='34a5c48bfe22c3d9718810166407048a906b8bcc'
assert cfg['admission']['maximum_new_c_bytes']==3221225472
assert len(cfg['input_pins'])==49
assert all(not p.replace('\\','/').startswith('//wsl.localhost/Ubuntu-24.04/mnt/c/') for p in cfg['input_pins'])
before=sha(config);start=time.monotonic();rows=[]
for index,(name,expected) in enumerate(cfg['input_pins'].items(),1):
 row=dict(path=name,expected_sha256=expected)
 try:
  p=pathlib.Path(name);row.update(actual_sha256=sha(p),bytes=p.stat().st_size)
  row['status']='PASS' if row['actual_sha256']==expected else 'HASH_MISMATCH'
 except Exception as ex:row.update(status='READ_REFUSED',error=repr(ex))
 rows.append(row);print('%02d/49 %s %s'%(index,row['status'],name),flush=True)
cap=next(iter(cfg['expected_runs']))
lease='//wsl.localhost/Ubuntu-24.04'+cfg['lease_path']
assert not pathlib.Path(cap).exists() and not pathlib.Path(lease).exists()
assert sha(config)==before
report=dict(status='PASS_READ_ONLY_WINDOWS_ALL49' if all(r['status']=='PASS' for r in rows) else 'FAIL_READ_ONLY_WINDOWS_PINS',
 checked_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),actual_python=sys.executable,actual_python_sha256=sha(sys.executable),
 preflight_source_sha256=sha(__file__),runtime_config=str(config),config_sha256=before,rows=rows,count=len(rows),elapsed_s=time.monotonic()-start,
 guest_launched=False,adapter_imported_or_executed=False,lease_created=False,resource_census=False,runtime_qualified=False)
with output.open('x') as f:json.dump(report,f,indent=2);f.write('\n')
print(json.dumps({k:report[k] for k in ('status','count','elapsed_s','config_sha256')}),flush=True)
raise SystemExit(0 if report['status']=='PASS_READ_ONLY_WINDOWS_ALL49' else 1)