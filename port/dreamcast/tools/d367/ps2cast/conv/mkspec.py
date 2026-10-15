import json, sys, os
W = '/root/probe/lanes-20261014/ps2cast/work/conv'
D = {
 'trap-em2a-00': ('em2a', '0x2a', [0], 'src/em2a/em2a.cpp em2a_R0_Init type 0: modelInit(ARC 4, ARC 5)'),
 'trap-em2a-02': ('em2a', '0x2a', [2], 'src/em2a/em2a.cpp em2a_R0_Init type 2: modelInit(ARC 8, ARC 9)'),
 'bat-em29-00': ('em29', '0x29', [], 'src/em29/em29.cpp em29_R0_Init: modelInit(ARC 4, ARC 5)'),
 'crawler-em2e-00': ('em2e', '0x2e', [0], 'src/em2e/em2e.cpp em2e_R0_Init type 0: modelInit(ARC 4, ARC 5)'),
 'crawler-em2e-01': ('em2e', '0x2e', [1], 'src/em2e/em2e.cpp em2e_R0_Init type 1: modelInit(ARC 4, ARC 6)'),
 'fish-em27-00': ('em27', '0x27', [0, 1], 'src/em27/em27.cpp em27_R0_Init: modelInit(ARC 4, ARC 5)'),
 'snake-em24-00': ('em24', '0x24', [], 'src/em24/em24.cpp em24_R0_Init: modelInit(ARC 5, ARC 6)'),
 'boat-pl0f-00': ('pl0f', '0x0f', [], 'src/pl0f/pl0f.cpp pl0f_R0_Init: modelInit(ARC 5, ARC 6)'),
}
MASK = {'bat-em29-00': 'mask-bat-em29-00', 'fish-em27-00': 'mask-fish-em27-00'}
# GX-only stages the DC source path never draws either (trans.cpp bumpSetup / specularSetup2 reach the GX stubs);
# each needs the runtime's per-id allowance (as RE4DC_NMR_DROP_BUMP em2f, RE4DC_NMR_CROW em23) before it can admit
DROPS = {'fish-em27-00': ['bump'], 'snake-em24-00': ['bump'], 'boat-pl0f-00': ['bump', 'alt-specular']}
def desc(n):
    a, mid, t, mod = D[n]
    d = dict(name=n, archive=a, model_id=mid, source_types=t, module=mod)
    if n in MASK: d['mask_runs'] = {'0': W + '/' + MASK[n]}
    if n in DROPS: d['source_drops'] = DROPS[n]
    return d

rooms = {'106': ['trap-em2a-00', 'trap-em2a-02', 'bat-em29-00', 'crawler-em2e-00', 'crawler-em2e-01'],
         '107': ['trap-em2a-00', 'fish-em27-00'], '10a': ['trap-em2a-02', 'snake-em24-00'], '11a': ['snake-em24-00']}
spec = dict(registry='ps2-ch1-cast', about='lane ps2cast2 (2026-10-14): the chapter-1 non-Ganado actors (traps em2a, bat em29, crawler em2e, fish em27, snake em24, boat pl0f) from their PS2 meshes (ps2_cast.py regcast). Render only.',
            cast_dir=W + '/regcast-ch1', revision_overlay='ps2-overlay', level='conservative', archive_audit='source/archive-audit.json',
            lighting='lit presets (normals kept); the runtime decides flat vs source lighting', descriptors=[desc(n) for n in D],
            room_packages={r: dict(descriptors=v, evidence='CH1 audit models-by-room.md') for r, v in rooms.items()})
json.dump(spec, open(sys.argv[1] + '/ps2-ch1-cast.json', 'w'), indent=1)
