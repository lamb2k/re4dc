from pathlib import Path
L=Path(r'C:\Game Dev\Emulators\codex-lanes\castle18');p=L/'run-resume-41inner-47absolute-resource-guard.py';assert not p.exists();s=(L/'run-resume-with-resource-guard-v2.py').read_text().replace('18*1024**3+128*1024**2','18*1024**3+328*1024**2').replace('Root launch floor18GiB+128MiB','Root launch18GiB+128MiB plus200MiB peer envelope; capture included').replace('guard-resume-guest-resources.py','guard-resume-41inner-47absolute-resources.py').replace('live18GiB+64MiB disk/60MiB capture guard','live18GiB+64MiB disk/60MiB capture and41sinner/47.5sabsolute guards')
s=s.replace('try:watch.wait(timeout=3)','try:watch.wait(timeout=6)')
compile(s,str(p),'exec');p.write_text(s)
for n in ['guard-resume-41inner-47absolute-resources.py',p.name]:compile((L/n).read_text(),n,'exec')
print('New runner/watcher compile; no guest')
