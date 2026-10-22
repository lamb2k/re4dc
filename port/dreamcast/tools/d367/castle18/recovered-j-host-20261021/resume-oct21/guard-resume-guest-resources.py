from pathlib import Path
import sys,time,json,shutil
L=Path(r'C:\Game Dev\Emulators\codex-lanes\castle18');D=Path(r'C:\Flycast-Evidence\re4-dreamcast\castle18-20261018\Test21\recovered-j-content-20261021');cap=Path(sys.argv[1]).resolve();assert cap.parent==D and cap.name.startswith('route-walk')
deadline=time.monotonic()+80;rows=[];closed=False
while time.monotonic()<deadline:
 if (cap/'run-result.json').exists():break
 if not (cap/'owned-process.json').exists():time.sleep(.1);continue
 free=shutil.disk_usage(D).free;logical=sum(p.stat().st_size for p in cap.rglob('*')if p.is_file());rows.append(dict(monotonic=time.monotonic(),free=free,cap_logical_bytes=logical))
 if free<18*1024**3+64*1024**2 or logical>60*1024**2:
  reason='Owned resource guard: runtime C floor18GiB+64MiB or capture growth60MiB reached; preserve emulator snapshot and stop only exact owned SDL process.'
  source=(L/'test21-close-i-capacity.py').read_text();old="p=Path(r'C:\\Flycast-Evidence\\re4-dreamcast\\castle18-20261018\\Test21\\current-i-route-walk05')";assert source.count(old)==1
  source=source.replace(old,'p=cap').replace('owned-capacity-wm-close.json','owned-resource-wm-close.json').replace('Global Flycast count exceeded four while main was active. Only exact owned SDL window received WM_CLOSE; production snapshot preserved by emulator.',reason)
  exec(compile(source,'<existing exact owned close helper>','exec'),{'cap':cap});closed=True;break
 time.sleep(.5)
if cap.exists():(cap/'owned-resource-guard.json').write_text(json.dumps(dict(scope='External monitor only; no keys or gameplay memory writes. Exact PID/path/start/window checked WM_CLOSE only if resource boundary crosses.',runtime_floor=18*1024**3+64*1024**2,capture_cap=60*1024**2,closed=closed,samples=rows),indent=2)+'\n')
