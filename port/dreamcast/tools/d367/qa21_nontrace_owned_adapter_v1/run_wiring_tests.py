"""Focused source-only actual wiring tests; no native process/filesystem APIs."""
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
if len(sys.argv)!=2 or sys.argv[1] not in ('receipt-linux.json','receipt-windows.json'):raise RuntimeError('explicit source receipt only')
spec=importlib.util.spec_from_file_location('wiring_tests',P/'test_wiring.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
stream=io.StringIO();result=unittest.TextTestRunner(stream=stream,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromModule(module))
pins={str(p.relative_to(P)).replace('\\','/'):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(P.rglob('*.py'))}
row={'scope':'SOURCE-only actual wiring/core/pipe/seed/collector tests with injected APIs, no native query/realimage/state/preflight/guest','utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'python':sys.version,'platform':platform.platform(),'tests':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'successful':result.wasSuccessful(),'source_sha256':pins,'output':stream.getvalue(),'runtime_adopted':False}
with (P/sys.argv[1]).open('x',encoding='utf-8') as f:json.dump(row,f,indent=2)
print(json.dumps({k:row[k] for k in ('scope','platform','tests','failures','errors','successful')}))
if not result.wasSuccessful():raise SystemExit(1)
