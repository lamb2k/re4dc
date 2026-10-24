"""Isolated direct-source bootstrap: scopes are stage or guest, separate grants."""
from pathlib import Path
import hashlib,json,os,sys,types
HERE=Path(__file__).resolve().parent
if not (__debug__ and sys.flags.isolated and sys.flags.no_site and sys.dont_write_bytecode):raise RuntimeError('Requires -I -S -B')
if len(sys.argv)!=3 or sys.argv[1] not in ['stage','guest','pair'] or sys.argv[2] not in ['off','on']:raise SystemExit('launch.py {stage,guest} {off,on}')
scope,arm=sys.argv[1:];grant_scope='guest' if scope=='pair' else scope;seal=HERE/'TOOLCHAIN-SEAL.json'
if os.environ.get('RAIN_QA_'+grant_scope.upper()+'_ALLOCATED')!=hashlib.sha256(seal.read_bytes()).hexdigest():raise RuntimeError('Separate exact root '+scope+' grant required')
pins=json.loads(seal.read_bytes())['members']
for n,p in pins.items():
 b=(HERE/n).read_bytes()
 if len(b)!=p['size'] or hashlib.sha256(b).hexdigest()!=p['sha256']:raise RuntimeError('Kit member changed '+n)
for n in ['common','rain_record','process_group',('future_master' if scope=='stage' else ('observe_pair' if scope=='pair' else 'post_slot'))]:
 p=HERE/(n+'.py');m=types.ModuleType(n);m.__file__=str(p);sys.modules[n]=m;exec(compile(p.read_bytes(),str(p),'exec',dont_inherit=True),m.__dict__)
module=sys.modules['future_master' if scope=='stage' else ('observe_pair' if scope=='pair' else 'post_slot')]
module.main() if scope=='pair' else module.main(arm)
