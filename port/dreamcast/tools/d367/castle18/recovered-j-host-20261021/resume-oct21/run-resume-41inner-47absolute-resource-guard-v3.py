from pathlib import Path
import sys,json,hashlib,shutil,subprocess,datetime
L=Path(r'C:\Game Dev\Emulators\codex-lanes\castle18');D=Path(r'C:\Flycast-Evidence\re4-dreamcast\castle18-20261018\Test21\recovered-j-content-20261021');n=int(sys.argv[1]);assert 169<=n<=999;cap=D/f'route-walk{n}';assert not cap.exists();assert shutil.disk_usage(D).free>=18*1024**3+328*1024**2,'Root launch18GiB+128MiB plus200MiB peer envelope; capture included'
receipt=json.loads((L/f'recovered-j-arm{n}-preparation.json').read_text());driver=L/f'run-recovered-j-route-walk{n}.py';controller=L/receipt['controller'];assert hashlib.sha256(driver.read_bytes()).hexdigest()==receipt['driver_sha256'];assert hashlib.sha256(controller.read_bytes()).hexdigest()==receipt['controller_sha256']
def status(activity):
 p=L/'STATUS.md';lines=p.read_text().splitlines();stamp=datetime.datetime.now().astimezone().isoformat(timespec='seconds')
 for i,line in enumerate(lines):
  if line.startswith('Doing now:'):lines[i]='Doing now: '+activity
  elif line.startswith('Updated:'):lines[i]=f"Updated: {stamp}. Run{n}; exact starting source{receipt['source_frame']}, health{receipt['health']}. Completion identity is audited after the guest exits."
 p.write_text('\n'.join(lines)+'\n')
status(f'Run{n} is active with exact-state normal controls and the live18GiB+64MiB disk/60MiB capture and41sinner/47.5sabsolute guards.')
watch=subprocess.Popen([sys.executable,str(L/'guard-resume-41inner-47absolute-resources-v3.py'),str(cap)],creationflags=subprocess.CREATE_NO_WINDOW)
try:
 subprocess.run(['wsl.exe','-d','Ubuntu-24.04','-u','root','--','bash',f'/mnt/c/Game Dev/Emulators/codex-lanes/castle18/run-recovered-j-route-walk{n}.sh'],check=True)
finally:
 watch.wait(timeout=85)
 guarded=json.loads((cap/'owned-resource-guard.json').read_text());assert guarded['process_exited'],'Guard has not verified owned process exit; do not claim closed'
 status(f'No guest is active; exact resource watcher verified run{n} process exit. Inspect its checkpoint, screenshots and guard receipt before continuing.')
 assert watch.returncode==0,('Guard failed closed; inspect preserved checkpoint',watch.returncode)
