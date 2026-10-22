from pathlib import Path
import json,hashlib,shutil
L=Path(__file__).parent;sha=lambda p:hashlib.file_digest(p.open('rb'),'sha256').hexdigest()
dest=Path(r'\\wsl.localhost\Ubuntu-24.04\root\probe\codex-castle18\port\dreamcast\tools\d367\castle18\controlled-script-events-20261021\controlled023-original-AEV16-source')
j=dict(scope='Source launch entry only, no actual root allocation.',shell=dict(path=str(L/'run-controlled-ch32-escape023.sh'),sha256=sha(L/'run-controlled-ch32-escape023.sh')),root_argv=['wsl.exe','-d','Ubuntu-24.04','-u','root','--','bash','/mnt/c/Game Dev/Emulators/codex-lanes/castle18/run-controlled-ch32-escape023.sh','--execute-allocated023'],required_allocation_path=str(L/'ESCAPE023-ROOT-ALLOCATION.json'),allocation_exists=(L/'ESCAPE023-ROOT-ALLOCATION.json').exists(),source_handback=dict(path=str(L/'ESCAPE023-SOURCE-QUALIFIED-HANDBACK.json'),sha256=sha(L/'ESCAPE023-SOURCE-QUALIFIED-HANDBACK.json')),review=dict(path=str(L.parent/'castle-controls21/review-source023-final-delta.json'),sha256=sha(L.parent/'castle-controls21/review-source023-final-delta.json')),source_unit_growth=dict(files_and_mirror_before_git=193808,maximum_including_git_mirror_metadata_bytes=1048576,no_guest_programme_image_build_bytes=0))
assert j['allocation_exists']is False
p=L/'ESCAPE023-LAUNCH-ENTRY.json';assert not p.exists();p.write_text(json.dumps(j,indent=2)+'\n',newline='\n');shutil.copyfile(p,dest/p.name)
for name in ['seal-controlled023-source-handoff.py','seal-controlled023-launch-entry.py']:shutil.copyfile(L/name,dest/name)
print(json.dumps(dict(launch_entry=sha(p),shell=j['shell']['sha256'],no_actual_allocation=True)))
