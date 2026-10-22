"""Run focused fake source controls and save their exact tested source pins."""
import datetime,hashlib,importlib.util,io,json,pathlib,platform,sys,unittest
p=pathlib.Path(__file__).parent
spec=importlib.util.spec_from_file_location('focused_changed_paths',p/'test_changed_paths.py');tests=importlib.util.module_from_spec(spec);spec.loader.exec_module(tests)
stream=io.StringIO();result=unittest.TextTestRunner(stream=stream,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromModule(tests))
receipt={'scope':'focused source/fake API controls only; no native query/process/image/input','platform':platform.platform(),'python':sys.version,'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'tests_run':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'passed':result.wasSuccessful(),'tested_python_sources':{str(x.relative_to(p)).replace('\\','/'):{'bytes':x.stat().st_size,'sha256':hashlib.sha256(x.read_bytes()).hexdigest()} for x in sorted(p.rglob('*.py'))},'output':stream.getvalue()}
(p/('receipt-windows.json' if sys.platform=='win32' else 'receipt-linux.json')).write_text(json.dumps(receipt,indent=2)+'\n')
print(stream.getvalue());sys.exit(0 if result.wasSuccessful() else 1)
