from pathlib import Path
p=Path(r'C:\Game Dev\Emulators\codex-lanes\rr-safe-cycle23')
admit=(p/'root-admit-boot-20261024.py').read_text()
admit=admit.replace("b=root/'boot-cand-fb254e82-v2'", "b=Path(r'\\\\wsl.localhost\\Ubuntu-24.04\\root\\probe\\rr-safe-boot-fb254e82-v3')")
admit=admit.replace('bounded-console-boot-v2','bounded-console-boot-v3')
admit=admit.replace('370ad23576222fb750ca3e2a5261e4008e08a780c3aea488e225114dd8c09402','981d6f49363e4bb569ebcb6cef36b7c09f39ee9808b003fd6c0e5c9cc4099f0a')
admit=admit.replace('//wsl.localhost/Ubuntu-24.04/mnt/c/Game Dev/Emulators/codex-lanes/rr-safe-cycle23/boot-cand-fb254e82-v2/ROOT-REVIEWED.json','//wsl.localhost/Ubuntu-24.04/root/probe/rr-safe-boot-fb254e82-v3/ROOT-REVIEWED.json')
admit=admit.replace('/mnt/c/Game Dev/Emulators/codex-lanes/rr-safe-cycle23/boot-cand-fb254e82-v2/ROOT-BOOT-ROOT-LEASE.json','/root/probe/rr-safe-boot-fb254e82-v3/ROOT-BOOT-ROOT-LEASE.json')
assert 'boot-cand-fb254e82-v2' not in admit and 'bounded-console-boot-v2' not in admit
(p/'root-admit-boot-v3-20261024.py').write_text(admit,newline='\n')
run=(p/'root-execute-boot-20261024.py').read_text()
run=run.replace('/mnt/c/Game Dev/Emulators/codex-lanes/rr-safe-cycle23/boot-cand-fb254e82-v2','/root/probe/rr-safe-boot-fb254e82-v3').replace('bounded-console-boot-v2','bounded-console-boot-v3')
assert 'boot-cand-fb254e82-v2' not in run
(p/'root-execute-boot-v3-20261024.py').write_text(run,newline='\n')
compile(admit,'root-admit-boot-v3-20261024.py','exec');compile(run,'root-execute-boot-v3-20261024.py','exec')
print('Prepared root V3 source only; no admission or execution.')
