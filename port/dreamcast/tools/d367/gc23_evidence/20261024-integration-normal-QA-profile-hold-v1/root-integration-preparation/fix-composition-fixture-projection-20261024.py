from pathlib import Path
import json,datetime
root=Path('/root/work/lanes/codex-composition-int24');p=root/'port/dreamcast/tools/d367/composition_int24/test_compose_integrated.py'
e=Path('/mnt/c/Game Dev/Emulators/codex-lanes/composition-int24');e.mkdir(exist_ok=True)
prior=e/'failed-fixture-v1.py';assert not prior.exists();prior.write_bytes(p.read_bytes())
(e/'FAILED-FIXTURE-v1.json').write_text(json.dumps({'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'tool_chunk':'2442a8','exit_code':1,'tests':7,'failures':12,'cause':'Extracted model_direct_account now contains GC accounting macros whose actual disabled definitions were omitted from the host fixture. Compile errors, not game runtime failure or accepted semantic-mutant detection.','evidence_limits':'Original tool output was truncated; this is a compact failure receipt plus exact failed fixture, not a complete compiler log.'},indent=2)+'\n')
s=p.read_text();anchor="  return r'''\n#include <cassert>";assert s.count(anchor)==1
new="  # Project actual source Gate0 definitions; do not invent a model_handle or substitute providers.\n  disabled_model_macros='\\n'.join(re.findall(r'^#define RE4DC_GCA_MODEL_(?:ACCEPT\\(\\)|TEXTURE\\(\\.\\.\\.\\)) \\(\\(void\\)0\\)$',ui,re.M))+'\\n'\n  assert len(disabled_model_macros.splitlines())==2\n  return disabled_model_macros+r'''\n#include <cassert>"
s=s.replace(anchor,new);p.write_text(s)
