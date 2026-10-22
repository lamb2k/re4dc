from pathlib import Path
import hashlib
L=Path(r'C:\Game Dev\Emulators\codex-lanes\castle18');p=L/'owned-window-recovered-j-r201-South-escape-bell-quiet-combat-v17-still.py';assert not p.exists();s=(L/'owned-window-recovered-j-r201-South-escape-bell-quiet-combat-v16-still.py').read_text()
needle="owner=json.loads((cap/'owned-process.json').read_text());"
s=s.replace(needle,needle+"process_age_at_anchor=time.time()-(owner['start_filetime']/10000000-11644473600);process_monotonic_anchor=time.monotonic();process_age=lambda:process_age_at_anchor+time.monotonic()-process_monotonic_anchor;",1)
needle="assert a.dwLowDateTime+(a.dwHighDateTime<<32)==owner['start_filetime']"
assert s.count(needle)==1
s=s.replace(needle,needle+"\n  if active and process_age()>=40.5:\n   assert hwnd and u.IsWindow(hwnd)\n   for name in sorted(active):\n    vk,scan=mapkeys[name][:2];ext=mapkeys[name][2]if len(mapkeys[name])>2 else 0;assert u.PostMessageW(hwnd,0x101,vk,1|(scan<<16)|(ext<<24)|0xc0000000)\n   active.clear();events.append({'all_owned_keys_released_before41s':process_age()});raise TimeoutError('Owned40.5s inner margin reached; no input beyond41s')",1)
s=s.replace("if wanted:assert time.time()-(owner['start_filetime']/10000000-11644473600)<41", "if wanted:assert process_age()<40.5",1)
s=s.replace("  assert 0x8c000000<=a and a+n<=0x8d000000;", "  if active:check()\n  assert 0x8c000000<=a and a+n<=0x8d000000;",1)
s=s.replace('while time.monotonic()-started<41:', 'while process_age()<40.5:').replace('while time.monotonic()-guest_started<33:', 'while process_age()<33:')
s=s.replace("time.time()-(owner['start_filetime']/10000000-11644473600)<23",'process_age()<23').replace("time.time()-(owner['start_filetime']/10000000-11644473600)<25",'process_age()<25')
compile(s,str(p),'exec');p.write_text(s);print(p.name,hashlib.sha256(p.read_bytes()).hexdigest())
