"""Pure independent continuation readback. No SDK or Make calls."""
from pathlib import Path
import ast,hashlib,json
from prepare_continuation import semantic_check,verify,sha
P=Path(__file__).resolve().parent
c=json.loads((P/'CONTINUATION.json').read_text());plan=json.loads((P.parent/'full-link-prep/PREPARATION.json').read_text())
assert c['source']==plan['source'] and semantic_check(c['off'])
assert c['no_execution']==dict(SDK=0,Make_queries=0,links=0,compiles=0)
assert sha(Path(plan['root'])/'receipt.json')==c['original_failed_receipt_sha256']
assert sha(P.parent/'full-link-prep/run_full_pair.py')==c['original_runner_sha256']
assert sha(P.parent/'full-link-prep/PREPARATION.json')==c['preparation_sha256']
verify(c['off_preservation_pins']);verify(plan['input_pins']);verify(plan['original_old_full_manifest'])
for arm in ('off','on'):
 verify({str(Path(plan['root'])/arm/'source'/n):r for n,r in plan['source_manifest'].items()})
s=(P/'continue_full_pair.py').read_text();a=ast.parse(s)
loops=[x for x in ast.walk(a) if isinstance(x,ast.For) and isinstance(x.target,ast.Name) and x.target.id=='name']
assert len(loops)==1 and ast.literal_eval(loops[0].iter)==['on']
assert 'def save():result.write_text' in s and "result=Path(contract['result'])" in s
assert "'arms':{'off':contract['off']}" in s
assert "if out.exists() or scratch.exists():" in s
assert "assert len(compiled_motion)==1" in s
assert "assert '-DRE4DC_GC_ASSET_MOTION_UNKNOWN=1' in compiled_motion[0]" in s
assert "objects[index-1].endswith('/gc_asset_audio.o') and objects[index+1].endswith('/mtx.o')" in s
assert not (Path(plan['root'])/'on/out').exists() and not Path(c['result']).exists()
print(json.dumps(dict(status='PURE_READBACK_PASS_NO_EXECUTION',OFF_preserved_files=len(c['off_preservation_pins']),OFF_main=c['off']['raw_sha256'],OFF_all14=True,OFF_empty_helper=True,negative_controls=c['negative_controls'],ON_only=True,failed_receipt=c['original_failed_receipt_sha256']),indent=2))
