import pathlib,zipfile,hashlib,json,shutil
src=pathlib.Path(r'\\wsl.localhost\Ubuntu-24.04\root\work\lanes\stat-bytes23-console-scratch\zip\RE4DC-QA-Test23-2a14662d-20261023-GDEMU.zip')
dst=pathlib.Path(r'C:\Game Dev\Emulators\RE4DC-QA23-StatBytes-2a14662d')
assert not dst.exists(),dst
assert shutil.disk_usage(dst.parent).free>=24*1024**3
dst.mkdir()
with zipfile.ZipFile(src) as z:
    assert all('..' not in pathlib.PurePosixPath(n).parts and not n.startswith('/') for n in z.namelist())
    z.extractall(dst)
for line in (dst/'SHA256SUMS.txt').read_text().splitlines():
    h,n=line.split(None,1);p=dst/n.strip();actual=hashlib.sha256(p.read_bytes()).hexdigest();assert actual==h,(p,actual,h)
readme='''Private QA: Stat byte-order audit, 23 October 2026

Source: 2a14662d4b025031cd93f64eed6a5d8159d473b7, based on integration 933936ea.
Switches: STAT_ROUTINE_BYTES=1, STAT_DIAG=1, QA_MENU=1, PC_SAMPLER=0.
QA programme raw SHA256: bfb586d0fc8034ef6c4a1b385e93a837eec6d0addecce157e49f9eef91fcf4bc.
This is a private correctness test disc. Production recipes remain unchanged.

Use the gdemu folder as a disc. No SD card copy has been made.
Boot the QA menu and choose these presets:
- R10B LAKE PATH, BOAT START: approach and board the boat normally. While Leon is in boat routine 0F, the HUD must show the harpoon, with no handgun ammunition digits. Leave the boat and check ordinary weapon ammunition returns. Check the VMU ammunition display too.
- R101 VILLAGE SQUARE (FIGHT START): move, aim, fire and reload; continue through the bell and radio sequence. Controls and encounter progression should remain normal.
- R11E EL GIGANTE (FIGHT): fight normally. The corrected enemy routine setter must not strand the boss in a wrong action. Source coverage is established; this is a prospective console check.
- R11F ENTRY: play the Mendez encounter and leave through the ordinary window and door after the fight. Full bounded host exit qualification is still being completed.
- Where a scoped weapon is available, check that its marker works. Check Ashley following and interaction during chapter 2.

Verified so far on source2a production gate images (STAT_DIAG=0): OFF main and all14 overlays match current integration; H2 OFF/ON340/340 and restored1, heap_before93920 each; both48KiB KOS modes pass (headroom6112/6176); GDEMU seed1 passes; census/TEXCHK/character gates pass27/27 rooms; bell2857matched decision ticks have zero player/enemy position drift. Mendez matched prefix covers both damage/death forms and full s02/s10/s11, but is NOT a full exit pass.
QA disc lint loader/standard and zip integrity pass. QA boot, menu warp and H2 probes ran; their final checks are recorded separately before delivery acceptance.
Boat before/after screenshots have matching authenticated boat routine bytes; poses differ. No whole-picture identity is claimed for the intentional HUD correction.

Source/host, linked programme, Flycast, full release and physical console acceptance are different. No fresh full-release or physical Dreamcast acceptance is claimed. Later enemies/rooms absent from this disc and the disabled trap dog are source-reviewed only.
Report the disc source2a14662d, preset, what happened and a photo if something fails.
'''
(dst/'STEPS.txt').write_text(readme,encoding='utf-8')
(dst/'README.txt').write_text(readme,encoding='utf-8')
ident={'source':'2a14662d4b025031cd93f64eed6a5d8159d473b7','base':'933936ea7f45ba81c09277a780ed00111407aa23','qa_raw_sha256':'bfb586d0fc8034ef6c4a1b385e93a837eec6d0addecce157e49f9eef91fcf4bc','qa_zip_source':str(src),'qa_zip_sha256':hashlib.sha256(src.read_bytes()).hexdigest(),'status':'STAGED_PENDING_FINAL_QUALIFICATION','production_recipe_changed':False,'copied_to_sd':False,'files':{str(p.relative_to(dst)):hashlib.sha256(p.read_bytes()).hexdigest() for p in (dst/'gdemu').iterdir() if p.is_file()}}
(dst/'IDENTITY.json').write_text(json.dumps(ident,indent=2)+'\n')
print(json.dumps({'staged':str(dst),'verified_tracks':len(ident['files']),'status':ident['status']}))