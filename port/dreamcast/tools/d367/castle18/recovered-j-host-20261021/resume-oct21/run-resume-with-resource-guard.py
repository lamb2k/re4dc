from pathlib import Path
import sys,json,hashlib,shutil,subprocess
L=Path(r'C:\Game Dev\Emulators\codex-lanes\castle18');D=Path(r'C:\Flycast-Evidence\re4-dreamcast\castle18-20261018\Test21\recovered-j-content-20261021');n=int(sys.argv[1]);assert 155<=n<=999;cap=D/f'route-walk{n}';assert not cap.exists();assert shutil.disk_usage(D).free>=18*1024**3+128*1024**2,'Root launch floor18GiB+128MiB'
receipt=json.loads((L/f'recovered-j-arm{n}-preparation.json').read_text());driver=L/f'run-recovered-j-route-walk{n}.py';controller=L/receipt['controller'];assert hashlib.sha256(driver.read_bytes()).hexdigest()==receipt['driver_sha256'];assert hashlib.sha256(controller.read_bytes()).hexdigest()==receipt['controller_sha256']
watch=subprocess.Popen([sys.executable,str(L/'guard-resume-guest-resources.py'),str(cap)],creationflags=subprocess.CREATE_NO_WINDOW)
try:subprocess.run(['wsl.exe','-d','Ubuntu-24.04','-u','root','--','bash',f'/mnt/c/Game Dev/Emulators/codex-lanes/castle18/run-recovered-j-route-walk{n}.sh'],check=True)
finally:
 try:watch.wait(timeout=3)
 except subprocess.TimeoutExpired:watch.terminate();watch.wait(timeout=3)
