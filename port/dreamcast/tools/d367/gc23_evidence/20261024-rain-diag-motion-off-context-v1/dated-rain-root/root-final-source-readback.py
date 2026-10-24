from pathlib import Path
import json,hashlib,subprocess,datetime
root=Path('/mnt/c/Game Dev/Emulators/codex-lanes/rain-diag24')
review=root/'review'; manifest=json.loads((review/'MANIFEST.json').read_text())
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
assert sha(review/'MANIFEST.json')=='f11c0ad62ae97c4efd0349b0ca32cecd7d44da0d325dc467dce54d533007e4f8'
for row in manifest['files']:
 p=review/row['path'];assert p.stat().st_size==row['bytes'] and sha(p)==row['sha256'],str(p)
repo='/root/work/lanes/rain-diag24';head='da413ff058f88fa136375ecff629610fc59c0e51';runtime='fdb5ed4212fc78823f625ab75b78cc237cfd181a'
def git(*args):return subprocess.check_output(['git','-C',repo,*args])
assert git('rev-parse','HEAD').decode().strip()==head and not git('status','--porcelain').strip()
assert git('diff','--name-only',runtime,head).decode().splitlines()==['port/dreamcast/tools/d367/rain_diag24/HOST-CONTROLS.json','port/dreamcast/tools/d367/rain_diag24/SOURCE-HOST-RECEIPT.json']
paths=['src/game/filter06.cpp','src/game/espgen44.cpp','port/dreamcast/game/effects30.mk']
pins={p:hashlib.sha256(git('show',head+':'+p)).hexdigest() for p in paths}
r={'status':'ROOT_RAIN_FINAL_SOURCE_REVIEW_RECEIPT_READBACK_PASS','utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'source':head,'runtime':runtime,'review_files_verified':len(manifest['files']),'review_manifest_sha256':sha(review/'MANIFEST.json'),'runtime_pins':pins,'root_review':'Read exact five-live-key repair and final diagnostic/Make/dispatcher source. Existing native call, source rain and original old-night semantics preserved by bounded source/host controls. Source-only CLEAR, no target cache/opcode/stack/programme/heap/guest or look acceptance.','integration_preview_tree':'e0e692656194343054a83ae0787bed66475f568d','SDK_or_guest':False}
out=root/'ROOT-FINAL-SOURCE-READBACK.json';assert not out.exists();out.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({'review_members':len(manifest['files']),'receipt_sha256':sha(out)}))
