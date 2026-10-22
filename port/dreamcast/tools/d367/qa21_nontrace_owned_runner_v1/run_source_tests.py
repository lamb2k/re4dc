"""Only injected-API/AST tests; no WindowsApi constructor, native query or guest."""
import datetime
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import platform
import sys
import unittest

P=Path(__file__).parent
if len(sys.argv)!=2 or sys.argv[1] not in ('receipt-linux.json','receipt-windows.json'):
    raise RuntimeError('explicit source-test receipt only')
spec=importlib.util.spec_from_file_location('owned_runner_tests',P/'test_owned_runner.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
stream=io.StringIO();result=unittest.TextTestRunner(stream=stream,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromModule(module))
pins={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(P.iterdir()) if p.suffix=='.py'}
receipt={'scope':'SOURCE-ONLY injected API/AST qualification; no native query/image/preflight/guest','utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
         'python':sys.version,'platform':platform.platform(),'tests':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'successful':result.wasSuccessful(),
         'source_sha256':pins,'output':stream.getvalue(),'runtime_adopted':False}
path=P/sys.argv[1]
with path.open('x',encoding='utf-8') as f:json.dump(receipt,f,indent=2)
print(json.dumps({k:receipt[k] for k in ('scope','platform','tests','failures','errors','successful')}))
if not result.wasSuccessful():raise SystemExit(1)
