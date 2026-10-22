"""Windows readonly actual-child paths/preflight/strictparent/checkpoint, no backend/job/guest."""
import datetime,hashlib,importlib.util,json,pathlib,shutil
P=pathlib.Path('//wsl.localhost/Ubuntu-24.04/root/probe/codex-qa21-death-repair/port/dreamcast/tools/d367/qa21_nontrace_return_door_v2')
OUT=pathlib.Path(__file__).parent
spec=importlib.util.spec_from_file_location('child_readonly_outer',P/'outer-driver.py');o=importlib.util.module_from_spec(spec);spec.loader.exec_module(o)
profile=json.loads((P/'guest-profile-v2.json').read_text());manifest=json.loads((P/'source-manifest.json').read_text());tools=o.hash_file(P/'source-manifest.json');assert tools=='e25ba6a875a64d42fa44a1553e1d55b8f4055c404837e95af2fa23f54b5ead37'
psha=o.hash_file(P/'guest-profile-v2.json');seed=pathlib.Path(profile['evidence_root'])/'cold-shoot01'
checks=[]
def guard():
 free=shutil.disk_usage('C:/').free;checks.append(free)
 if free<profile['limits']['disk_runtime']:raise RuntimeError('readonly runtime floor')
for name,row in manifest['files'].items():
 f=o.no_alias(P/name);assert f.stat().st_size==row['bytes'];assert o.hash_file(f,guard)==row['sha256'],name
assert o.hash_file(P/'exact-log-symbols.json')==manifest['files']['exact-log-symbols.json']['sha256']
a=o.parse_args(['--profile',str(P/'guest-profile-v2.json'),'--profile-sha256',psha,'--tools-sha256',tools,'--mode','return-door01','--seed',str(seed)])
i=o.load('child_readonly_inner',P/'inner-adapter.py');i.validate_role(profile,a.mode,a.seed);o.validate_seed(profile,a.mode,a.seed,psha)
try:o.validate_seed(profile,a.mode,a.seed,'different-child-profile')
except RuntimeError:changed_profile_refused=True
else:raise AssertionError('different profile ancestry bypass')
records=o.preflight(profile,guard)
c=o.load('readonly_checkpoint',profile['retained_dependencies']['checkpoint.py']['path'])
disc_identity={'files':{n:r['sha256'] for n,r in profile['disc']['files'].items()},'program_sha256':o.PROGRAM,'elf_sha256':o.ELF}
verified=c.verify(seed,profile['elf_path'],profile['observer']['binding'],profile['observer']['layout'],disc_identity,pathlib.Path(profile['template']['path'])/'flycast.exe')
# The unchanged verifier returns the exact checkpoint receipt; compare source audit.
assert verified['audit']['state_sha256']=='e81e572fefa7a94771ecde68c1d38456e4a51d62d3b3641ecd52de0db51b0c75'
assert verified['audit']['frame']==533 and verified['audit']['room']==0x103
assert o.hash_file(P/'source-manifest.json')==tools
for name,row in manifest['files'].items():assert o.hash_file(o.no_alias(P/name),guard)==row['sha256'],name
assert not (seed.parent/'return-door01').exists() and not (seed.parent/'return-door01-control').exists()
row={'scope':'actual childv2 path/hash expressions + full preflight + strictparent + retainedcheckpoint verify READONLY only; no backend/job/output/guest','utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'pass':True,'profile_sha256':psha,'tools_sha256':tools,'checked_manifest_files':len(manifest['files']),'actual_absolute_readonly_files':sum(pathlib.Path(n).is_absolute() for n in manifest['files']),'local_log_metadata_sha256':o.hash_file(P/'exact-log-symbols.json'),'source_disc':records,'parent_checkpoint_sha256':o.hash_file(seed/'checkpoint.json'),'audit':verified['audit'],'changed_profile_refused':changed_profile_refused,'no_parent_mutation':True,'guard_samples':len(checks),'minimum_C_snapshot':min(checks),'snapshot_not_allocation':True,'door_outputs_absent':True,'guest_allocated':False}
f=OUT/'readonly-preflight.json';assert not f.exists();f.write_bytes((json.dumps(row,indent=2)+'\n').encode());print(json.dumps({'receipt':str(f),'sha256':o.hash_file(f),'guard_samples':len(checks),'min_C':min(checks)}))
