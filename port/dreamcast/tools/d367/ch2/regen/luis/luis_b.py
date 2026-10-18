"""luis_b.py STEP: replay of Codex 2026-10-13 Luis chain, step B (Windows Python).
gun:    finish_luis_gun.py (18:45): validation, pc.finish, pc.regcast -> regcast-luis-gun, luis-gun-registry-spec.json
mask:   ps2_luis_mask.py (orientation tree) -> models/luis-actor-v2/diffuse-alpha-v2 (22:31)
cand:   prepare_luis_candidate.py (19:33, v1 cast layout) + prepare_candidate.py (22:31, v2) -> candidate-v2"""
import hashlib, json, shutil, struct, subprocess, sys
from pathlib import Path
U = '//wsl.localhost/Ubuntu-24.04'
L = Path(U + '/root/probe/lanes-20261017r/ch2regen')
r = L / 'luis'
G = L / 't-luisg/port/dreamcast/tools'
O = L / 't-luiso/port/dreamcast/tools'
sha = lambda b: hashlib.sha256(b).hexdigest()
wsl = lambda p: str(p).replace('\\', '/').replace(U, '')
step = sys.argv[1]
if step == 'gun':
    sys.path.insert(0, str(G)); import ps2_cast as pc
    out = r / 'models/luis-gun-v1'; val = json.loads((out / 'validation.json').read_text())
    bindings = json.loads((out / 'source-bindings.json').read_text()); report = json.loads((out / 'native/native-report.json').read_text())
    pc.PRESETS['luis-gun'] = dict(archive='pl14', sections=[(14, 'gun')], tpl=15, rooms=['r11c'], types=[0], category='registry', model_id=11, lit=True)
    val['preset'] = 'luis-gun'; val['sections'] = [{'bones': 7, 'gc_palettes': bindings[0]['palettes'], 'ps2_palettes': report['chunks'][0]['palettes']}]
    val['inputs'] = {'gc': {'cache': str(r / 'luis-inputs/pl14.drs'), 'sha256': '2b5b554d45a67f12612474a9ed0a1bbeb7cf5882d16a7c67ce7ff25018676f27'}}
    (out / 'validation.json').write_text(json.dumps(val, indent=2)); pc.finish(out); pc.regcast(r / 'regcast-luis-gun', 'ps2-overlay', [out])
    spec = {'registry': 'ps2-r11c-luis-gun', 'about': 'Independent complete PS2 Luis gun; original GC seven-bone identity. Runtime object ownership still requires target capture.', 'cast_dir': pc.to_wsl(r / 'regcast-luis-gun'), 'revision_overlay': 'ps2-overlay', 'level': 'conservative', 'archive_audit': 'source/archive-audit.json', 'descriptors': [{'name': 'luis-gun', 'archive': 'pl14', 'model_id': '0x0b', 'source_types': [0], 'module': 'src/pl14/pl14.cpp cSubLuis::equipWeapon createsBack(0x0b), GC ARC0xe/TPL0xf, parent owner part10'}], 'room_packages': {'11c': {'descriptors': ['luis-gun'], 'evidence': 'PS2 ARC0xb/TPL0xc; seven identical PS2/GC bones, all857triangles'}}}
    (r / 'luis-gun-registry-spec.json').write_text(json.dumps(spec, indent=2)); print('gun regcast ok')
elif step == 'mask':
    m = r / 'models/luis-actor-v2'
    subprocess.check_call([sys.executable, str(O / 'ps2_luis_mask.py'), str(m), str(r / 'luis-inputs/pl14.dat'), str(m / 'native-proof-v2/runtime/castmodel_runtime.h'), str(m / 'diffuse-alpha-v2')])
elif step == 'cand':
    # v1 cast layout (prepare_luis_candidate.py) with the v2 model; then the v2 overrides (prepare_candidate.py)
    out = r / 'candidate-v2'; out.mkdir(exist_ok=False)
    cast = out / 'cast'; d = cast / 'luis-actor'; rev = d / 'ps2-v1'; rev.mkdir(parents=True); model = r / 'models/luis-actor-v2'
    header = model / 'native-proof-v2/runtime/castmodel_runtime.h'; shutil.copy2(header, rev / 'castmodel_runtime.h')
    for name in ('source.json', 'source-bindings.json'): shutil.copy2(model / name, d / name)
    src = json.loads((d / 'source.json').read_text()); src['source_model_id'] = 4; (d / 'source.json').write_text(json.dumps(src))
    (d / 'manifest.json').write_text(json.dumps(dict(name='luis-actor', revision='ps2-v1')))
    key = json.loads((model / 'validation.json').read_text())['texture']['key']; pkg = model / 'colour-vq-v2' / (key + '.re4tex'); b = pkg.read_bytes()
    toff = struct.unpack_from('<I', b, 24)[0]; name, w, h, fmt, off, size, flags, payload, extra = struct.unpack_from('<64s8I', b, toff)
    assert payload == 2 and fmt == 0 and (w, h) == (512, 512)
    tex = dict(key=key, package=wsl(pkg), package_sha256=sha(b), format='VQ RGB565', rectangle=[0, 0, w, h], vram_bytes=size)
    level = dict(runtime_header='luis-actor/ps2-v1/castmodel_runtime.h', header_sha256=sha(header.read_bytes()))
    entry = dict(name='luis-actor', revision='ps2-v1', previous_revision=None, rooms=['r11c'], category='registry', levels=dict(conservative=level), texture_packages={str(i): tex for i in range(6)}, position_shift=4, status='PS2 character TPL interlace orientation corrected; full source geometry and weights unchanged; runtime review pending')
    (rev / 'revision-manifest.json').write_text(json.dumps(entry)); (cast / 'ps2-overlay/integration-bundle').mkdir(parents=True); (cast / 'source').mkdir()
    gun = r / 'regcast-luis-gun'; shutil.copytree(gun / 'luis-gun', cast / 'luis-gun'); entries = [entry] + json.loads((gun / 'ps2-overlay/integration-bundle/catalog.json').read_text())
    (cast / 'ps2-overlay/integration-bundle/catalog.json').write_text(json.dumps(entries)); revs = json.loads((gun / 'source/candidate-revisions.json').read_text()); revs['luis-actor'] = dict(revision='ps2-v1')
    (cast / 'source/candidate-revisions.json').write_text(json.dumps(revs)); shutil.copy2(gun / 'source/archive-audit.json', cast / 'source/archive-audit.json')
    spec = dict(registry='ps2-r11c-luis-body-gun', about='Luis character TPL orientation correction, unchanged source geometry, weights and motion ownership', cast_dir=wsl(cast), revision_overlay='ps2-overlay', level='conservative', archive_audit='source/archive-audit.json',
                descriptors=[dict(name='luis-actor', archive='pl14', model_id='0x04', source_types=[0], source_drops=['bump'], source_coverage_manifest=wsl(model / 'coverage-manifest.json'), mask_runs={'3': wsl(model / 'diffuse-alpha-v2')})] + json.loads((r / 'luis-gun-registry-spec.json').read_text())['descriptors'],
                room_packages={'11c': dict(descriptors=['luis-actor', 'luis-gun'], evidence='Full4197PS2body+857gun triangles; six GC body infos retained, head/face shared draw; source diffuse-alpha format reference and measured ARGB4444 conversion. Runtime/visual pending.')})
    (out / 'spec.json').write_text(json.dumps(spec, indent=2)); print('candidate-v2', tex['key'], tex['package_sha256'][:16])
