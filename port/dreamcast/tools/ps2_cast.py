#!/usr/bin/env python3
"""PS2 character converter (lane ps2cast): a PS2 RE4 character appearance (the em archive's model BINs and
TPL on the PS2 disc) -> the external cast's pack layout that tools/cast_bundle.py (the cl lane's bundle
maker) and coarse_ganado_cast.cpp consume. No runtime code changes; derived assets are private.

The game keeps the GameCube skeleton and motions, so the PS2 mesh is bound to the GC skeleton exactly: every
section's PS2 bone table must equal the GC BIN's (bone id == GC part attach id, parent, rest translation
within --bone-tol mm); PS2 weight bone ids are then GC part indices (identity map, checked per bone). The
appearance's signatures stay the GC source infos' (the runtime identifies the game's loaded GC model by them
and draws the converted mesh in its place).

Stage 1, `convert` (Windows Python: numpy, PIL):
  inputs/        emXX.dat from the PS2 disc (ISO9660 -> BIO4DAT.AFS) and emXX.drs from the GC debug disc,
                 sha256-recorded
  source.json    GC skeleton (rest = capture = accumulated part translations) + GC section infos
  mesh.json      re4dc-approved-render-mesh-1 (the cast's Blender exchange schema): PS2 positions (mm),
                 PS2 weights on GC bone indices, per corner PS2 normal and atlas UV, section = source info
  atlas.png      the appearance TPL's images (PS2 4/8-bit CLUT, GS-unswizzled by ps2_tpl_decode.py, the
                 decoder validated pixel-exact against JADERLINK) in 256 x 256 cells of one power-of-two atlas
  native/        character-prototype pack_coarse_actor.pack() output (GX triangle lists, arrays, report)
                 + host-fixture.bin for the cast agent's host check
  source-bindings.json, manifest.json (cast layout; levels filled by stage 2)
  validation.json skeleton / weights / winding / normals / rest and posed surface distance to the GC mesh
Stage 2, `native` (WSL; ps2_cast_native.sh): host check (check-dynamic, the unchanged native_actor_fast.cpp
converter), fastpath build_blob.py (strips) + verify_blob.py + patch_header.py -> runtime header; pvrtex VQ
+ vq_export.py --pack-existing -> <key>.re4tex. Stage 3, `castdir`: assembles a cast dir for cast_bundle.py.

usage:
  ps2_cast.py convert <preset> <out dir> [--ps2-iso P] [--gc-iso G] [--poses pose-samples.json]
  ps2_cast.py finish <out dir>              (after stage 2: fills manifest levels from fit-report / header)
  ps2_cast.py castdir <cast dir> <out dir>...   (writes/extends a cast dir for cast_bundle.py)
  ps2_cast.py list                          (presets)
Env: RE4_CAST_PROTO (character-prototype-20260925, pack_coarse_actor.py), RE4_WORLD_AGENT (ps2_tpl_decode.py).
"""
import argparse, hashlib, importlib.util, json, math, os, re, shutil, struct, sys, zlib
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path[:0] = [str(HERE), str(REPO / 'tools')]
import numpy as np  # noqa: E402
from PIL import Image  # noqa: E402
import ps2_bin as pb  # noqa: E402
import convert_character as cc  # noqa: E402
import drs  # noqa: E402
from motion import modelbin  # noqa: E402

PRIV = Path(os.environ.get('RE4_PRIVATE', 'C:/Game Dev/Emulators/re4-assets-private'))
PROTO = Path(os.environ.get('RE4_CAST_PROTO', PRIV / 'character-prototype-20260925'))
WA = Path(os.environ.get('RE4_WORLD_AGENT', PRIV / 'world-agent-20260926'))
PS2_ISO = 'C:/Game Dev/Emulators/re4_helpers/Resident Evil 4 (USA)/Resident Evil 4 (USA).iso'
GC_ISO = 'C:/Game Dev/Emulators/Resident Evil 4 Debug (Disc 1)/Resident Evil 4 Debug (Disc 1).iso'
ROLES = ['body', 'head', 'right-hand', 'left-hand']
CELL = 256


def _ganado(archive, base, rooms, types, hands=(0x1c0, 0x1c5)):
    return dict(archive=archive, sections=[(base, 'body'), (base + 2, 'head'), (hands[0], 'right-hand'), (hands[1], 'left-hand')],
                tpl=base + 1, rooms=rooms, types=types, category='human')


def _ganado_stump(archive, base, rooms, types):
    """em10HeadSet's lost-head variant of a _ganado appearance: the head section is mot[3] = base + 3 (the stump)."""
    d = _ganado(archive, base, rooms, types)
    d['sections'][1] = (base + 3, 'head')
    return d


# arc numbers (PL_ARC = entry index + 4), from the source's Em15Set / Em12Set tables (cast recover_cast.py)
PRESETS = {
    'ganado-em15-00': _ganado('em15', 0x1bc, ['r101'], [0x00]),
    'ganado-em15-0b': _ganado('em15', 0x1c9, ['r101'], [0x0b]),
    'ganado-em15-03': _ganado('em15', 0x1dc, ['r101'], [0x03]),
    'ganado-em15-04': _ganado('em15', 0x1e0, ['r101'], [0x04]),
    'ganado-em12-01': dict(archive='em12', sections=[(0x1d8, 'body'), (0x1da, 'head'), (0x1c0, 'right-hand'), (0x1c5, 'left-hand')],
                           tpl=0x1d9, rooms=['r100', 'r103'], types=[1], category='human'),
    # not in the external cast (ps2_cast_inventory.py): Em17Set / Em16Set type 0xc, Em13Set type 6 (own hands)
    # model_id: the registry descriptor's enemy id (regcast; lane ps2cast-2 draws em17 type 0xc through a registry pack)
    'ganado-em17-0c': dict(_ganado('em17', 0x1cd, ['r108', 'r118', 'r111', 'r113', 'r11d'], [0x0c]), model_id=0x17),
    'ganado-em13-06': dict(archive='em13', sections=[(0x1e7, 'body'), (0x1e9, 'head'), (0x1f4, 'right-hand'), (0x1f8, 'left-hand')],
                           tpl=0x1e8, rooms=['r104', 'r11c', 'r10f'], types=[6], category='human'),
    # em10HeadSet's type-3 lost-head source variant. Keep all four source roles
    # while converting so its PS2 image0 uses exactly the normal app2 atlas.
    'ganado-em13-03-stump': dict(archive='em13',
        sections=[(476, 'body'), (479, 'head'), (448, 'right-hand'), (453, 'left-hand')],
        tpl=477, rooms=['r11c'], types=[3], category='human'),
    # lane stump17 (10-17, CAST-GC): the same lost-head variant (mot[3] = the head BIN + 1, em12/13/15/16/17 _set.cpp) of
    # the other four cast appearances, so ACTOR_GANADO_PS2_STUMP covers every appearance. The stump BINs are identical
    # in every archive that carries them (castgc17 stump_facts: 475 em12/13/17, 447 em12/13/15/17, 483 em12/13/15/16,
    # 460 em15/16); the body / hands keep each appearance's normal sections, so the atlas is the appearance's own.
    'ganado-em12-01-stump': dict(archive='em12', sections=[(0x1d8, 'body'), (0x1db, 'head'), (0x1c0, 'right-hand'), (0x1c5, 'left-hand')],
                                 tpl=0x1d9, rooms=['r100', 'r103'], types=[1], category='human', subset_bones=True),
    'ganado-em15-00-stump': _ganado_stump('em15', 0x1bc, ['r101'], [0x00]),
    'ganado-em15-04-stump': _ganado_stump('em15', 0x1e0, ['r101'], [0x04]),
    'ganado-em15-0b-stump': _ganado_stump('em15', 0x1c9, ['r101'], [0x0b]),
    # lane stump17 (10-17, CAST-GC): the other hand poses em10HandSet selects (mot[7] / mot[12] = 0x1c1 / 0x1c6, type 1:
    # the back-hold / bomb-hold grabs; mot[8] / mot[13] = 0x1c2 / 0x1c7, type 2: the alert routine), converted per
    # appearance with that appearance's body / head, so each lands in the appearance's normal atlas.
    'ganado-em12-01-h1': dict(archive='em12', sections=[(0x1d8, 'body'), (0x1da, 'head'), (0x1c1, 'right-hand'), (0x1c6, 'left-hand')], tpl=0x1d9, rooms=['r100', 'r103'], types=[1], category='human'),
    'ganado-em12-01-h2': dict(archive='em12', sections=[(0x1d8, 'body'), (0x1da, 'head'), (0x1c2, 'right-hand'), (0x1c7, 'left-hand')], tpl=0x1d9, rooms=['r100', 'r103'], types=[1], category='human'),
    'ganado-em15-00-h1': _ganado('em15', 0x1bc, ['r101'], [0x00], hands=(0x1c1, 0x1c6)),
    'ganado-em15-00-h2': _ganado('em15', 0x1bc, ['r101'], [0x00], hands=(0x1c2, 0x1c7)),
    'ganado-em15-03-h1': _ganado('em15', 0x1dc, ['r101'], [0x03], hands=(0x1c1, 0x1c6)),
    'ganado-em15-03-h2': _ganado('em15', 0x1dc, ['r101'], [0x03], hands=(0x1c2, 0x1c7)),
    'ganado-em15-04-h1': _ganado('em15', 0x1e0, ['r101'], [0x04], hands=(0x1c1, 0x1c6)),
    'ganado-em15-04-h2': _ganado('em15', 0x1e0, ['r101'], [0x04], hands=(0x1c2, 0x1c7)),
    'ganado-em15-0b-h1': _ganado('em15', 0x1c9, ['r101'], [0x0b], hands=(0x1c1, 0x1c6)),
    'ganado-em15-0b-h2': _ganado('em15', 0x1c9, ['r101'], [0x0b], hands=(0x1c2, 0x1c7)),
    # lane purge-cast24 (10-24, GC purge): the grip hands em10HandSet selects for a held weapon / torch (mot[9] /
    # mot[14] = 0x1c3 / 0x1c8, BIN 451 / 456: r108 r118 r11a), which drew the GameCube geometry (ganado_extra).
    'ganado-em12-01-h3': dict(archive='em12', sections=[(0x1d8, 'body'), (0x1da, 'head'), (0x1c3, 'right-hand'), (0x1c8, 'left-hand')], tpl=0x1d9, rooms=['r108', 'r118', 'r11a'], types=[1], category='human'),
    'ganado-em15-00-h3': _ganado('em15', 0x1bc, ['r108', 'r118', 'r11a'], [0x00], hands=(0x1c3, 0x1c8)),
    'ganado-em15-03-h3': _ganado('em15', 0x1dc, ['r108', 'r118', 'r11a'], [0x03], hands=(0x1c3, 0x1c8)),
    'ganado-em15-04-h3': _ganado('em15', 0x1e0, ['r108', 'r118', 'r11a'], [0x04], hands=(0x1c3, 0x1c8)),
    'ganado-em15-0b-h3': _ganado('em15', 0x1c9, ['r108', 'r118', 'r11a'], [0x0b], hands=(0x1c3, 0x1c8)),
    # non-Ganado models for NATIVE_MODEL_REGISTRY packs (ps2_cast.py regcast; lane ps2cast-all): src/em2b em2b.cpp
    # type 0 (TYPE_A) modelInit(ARC 5, ARC 7) + ModInfoMgr.create(ARC 6, ARC 7): body + head, one 64-bone skeleton
    'gigante-em2b-00': dict(archive='em2b', sections=[(5, 'body'), (6, 'head')], tpl=7, rooms=['r119'], types=[0],
                            category='boss', model_id=0x2b, shift=2),
    # lane cast16 (2026-10-16): em2b's other model types (em2b.cpp em2bModelInit): TYPE_B 1 = BIN 8 + head 9, TPL 0xA;
    # TYPE_C 2 = BIN 0xB + head 0xC, TPL 0xD (the r11e giant, chapter 2-3 fork B); type 3 = BIN 0xE + head 0xF, TPL 0x10.
    'gigante-em2b-01': dict(archive='em2b', sections=[(8, 'body'), (9, 'head')], tpl=0xa, rooms=['r224'], types=[1],
                            category='boss', model_id=0x2b, shift=2),
    'gigante-em2b-02': dict(archive='em2b', sections=[(0xb, 'body'), (0xc, 'head')], tpl=0xd, rooms=['r11e'], types=[2],
                            category='boss', model_id=0x2b, shift=2),
    'gigante-em2b-03': dict(archive='em2b', sections=[(0xe, 'body'), (0xf, 'head')], tpl=0x10, rooms=['r224'], types=[3],
                            category='boss', model_id=0x2b, shift=2),
    # src/em2f em2f.cpp type 0 (the r10b Del Lago fight): modelInit(ARC 4, ARC 5); type 1 (ARC 6 / 7) is the same
    # model on GC and PS2 (no geometry change), so only type 0 converts (lane ps2cast-2)
    'dellago-em2f-00': dict(archive='em2f', sections=[(4, 'body')], tpl=5, rooms=['r10b'], types=[0],
                            category='boss', model_id=0x2f, shift=2),
    # lane ps2cast-4 (PS2_ANIMALS): the stage-1 animals, the cast's registry descriptors (stage1-animals.json) re-pointed
    # at the PS2 meshes. Same BIN / TPL arcs as the cast's source-bindings (type 0 TPL ARC 5, type 1 ARC 6; the crow's
    # body BIN 5 + wing BIN 6 (folded) or 7 (spread), TPL 8: em23SetWing). The crow's PS2 wing BINs carry reduced bone
    # tables (subset_bones).
    'dog-00': dict(archive='em21', sections=[(4, 'body')], tpl=5, rooms=['r103', 'r119'], types=[0], category='animal', model_id=0x21),
    'dog-01': dict(archive='em21', sections=[(4, 'body')], tpl=6, rooms=['r100', 'r103'], types=[1], category='animal', model_id=0x21),
    'cow-00': dict(archive='em26', sections=[(4, 'body')], tpl=5, rooms=['r101', 'r103'], types=[0], category='animal', model_id=0x26),
    'cow-01': dict(archive='em26', sections=[(4, 'body')], tpl=6, rooms=['r103'], types=[1], category='animal', model_id=0x26),
    'chicken-00': dict(archive='em28', sections=[(4, 'body')], tpl=5, rooms=['r101', 'r103'], types=[0], category='animal', model_id=0x28),
    'chicken-01': dict(archive='em28', sections=[(4, 'body')], tpl=6, rooms=['r101', 'r103'], types=[1], category='animal', model_id=0x28),
    'crow-folded': dict(archive='em23', sections=[(5, 'body'), (6, 'folded-wings')], tpl=8, rooms=['r100', 'r105', 'r108', 'r109'],
                        types=[], category='animal', model_id=0x23, subset_bones=True),
    'crow-spread': dict(archive='em23', sections=[(5, 'body'), (7, 'spread-wings')], tpl=8, rooms=['r100', 'r105', 'r108', 'r109'],
                        types=[], category='animal', model_id=0x23, subset_bones=True),
    # lane ps2cast-4 (PS2_WOLF): the parasite dog (Colmillos) em22, src/em22 em22_R0_Init modelInit(ARC 4, ARC 5): one
    # 42-bone body BIN (the back parasites are cObj16 objects, ARC 0x39 / 0x47, not part of this model)
    'wolf-em22-00': dict(archive='em22', sections=[(4, 'body')], tpl=5, rooms=['r11b', 'r118'], types=[0], category='animal', model_id=0x22, lit=True),
    # CH23: exact source info selections (em10ModelInit / Em13Set / em10_R1_Trade).
    # The 61-bone merchant uses three TPLs and seven infos, including the hidden
    # goods info. Open/closed coat changes the cloth BIN; both retain base hands.
    'merchant13-c0': dict(archive='em13', sections=[(0x1e7, 'body'), (0x1f0, 'robe'), (0x1ee, 'cloth'),
                            (0x1ef, 'goods'), (0x1e9, 'head'), (0x1f4, 'right-hand'), (0x1f8, 'left-hand')],
                         tpl=0x1e8, section_tpls={0x1f0: 0x1f1, 0x1ee: 0x1f1, 0x1e9: 0x1ea},
                         rooms=['r10f'], types=[6], category='registry', model_id=0x13, lit=True),
    'merchant13-o0': dict(archive='em13', sections=[(0x1e7, 'body'), (0x1f0, 'robe'), (0x1ed, 'cloth'),
                            (0x1ef, 'goods'), (0x1e9, 'head'), (0x1f4, 'right-hand'), (0x1f8, 'left-hand')],
                         tpl=0x1e8, section_tpls={0x1f0: 0x1f1, 0x1ed: 0x1f1, 0x1e9: 0x1ea},
                         rooms=['r10f'], types=[6], category='registry', model_id=0x13, lit=True),
    # Standalone merchant em18 uses a different archive and source info order.
    # em18_R0_Init appends robe, head, both hands, cloth, then hidden goods.
    # lane ps2cast 2026-10-14: Ashley (pl11, r117 ...). Converted by ps2_ashley.py (141 GC joints, draw slots, PS2 cloth
    # weights moved onto the GC cloth links); this entry only carries the finish / regcast metadata.
    'ashley11': dict(archive='pl11', sections=[(4, 'body'), (7, 'head'), (6, 'hair'), (9, 'extra9'), (0xA, 'extraA'),
                                               (0xC, 'right-hand'), (0xF, 'left-hand')],
                     tpl=5, section_tpls={7: 0xB, 6: 8}, rooms=['r117'], types=[], category='registry', model_id=3,
                     converter='ps2_ashley.py'),
    'ashley11-h1': dict(archive='pl11', sections=[(4, 'body'), (7, 'head'), (6, 'hair'), (9, 'extra9'), (0xA, 'extraA'),
                                                  (0xD, 'right-hand'), (0x10, 'left-hand')],
                        tpl=5, section_tpls={7: 0xB, 6: 8}, rooms=['r117'], types=[], category='registry', model_id=3,
                        converter='ps2_ashley.py --hands 1'),
    'ashley11-h3': dict(archive='pl11', sections=[(4, 'body'), (7, 'head'), (6, 'hair'), (9, 'extra9'), (0xA, 'extraA'),
                                                  (0xE, 'right-hand'), (0xF, 'left-hand')],
                        tpl=5, section_tpls={7: 0xB, 6: 8}, rooms=['r117'], types=[], category='registry', model_id=3,
                        converter='ps2_ashley.py --hands 3'),
    'merchant18-c0': dict(archive='em18', sections=[(5, 'body'), (14, 'robe'), (7, 'head'),
                            (18, 'right-hand'), (19, 'left-hand'), (12, 'cloth'), (13, 'goods')],
                         tpl=6, section_tpls={14: 15, 7: 8, 12: 15},
                         rooms=['r10d', 'r112'], types=[], category='registry', model_id=0x18, lit=True),
    'merchant18-o0': dict(archive='em18', sections=[(5, 'body'), (14, 'robe'), (7, 'head'),
                            (18, 'right-hand'), (19, 'left-hand'), (11, 'cloth'), (13, 'goods')],
                         tpl=6, section_tpls={14: 15, 7: 8, 11: 15},
                         rooms=['r10d', 'r112'], types=[], category='registry', model_id=0x18, lit=True),
    # em3b_R0_Init: cart type 2 (r11d) and truck type 0 (r200).
    'cart-em3b-02': dict(archive='em3b', sections=[(0xb, 'body')], tpl=0xc, rooms=['r11d'], types=[2],
                         category='registry', model_id=0x3b, lit=True, repeat_uvs=True),
    'truck-em3b-00': dict(archive='em3b', sections=[(4, 'body')], tpl=5, rooms=['r200'], types=[0],
                          category='registry', model_id=0x3b, lit=True, shift=3),
    # em35_R0_Init: whole body + extra, divided upper body, and separated legs.
    # All use the original GC skeleton/animation; the PS2 bone tables match it.
    'mendez35-full': dict(archive='em35', sections=[(4, 'body'), (6, 'extra')], tpl=5, rooms=['r11f'], types=[0],
                          category='boss', model_id=0x35, shift=2, lit=True),
    'mendez35-upper': dict(archive='em35', sections=[(7, 'body')], tpl=5, rooms=['r11f'], types=[1],
                           category='boss', model_id=0x35, shift=2, lit=True),
    'mendez35-legs': dict(archive='em35', sections=[(8, 'body')], tpl=5, rooms=['r11f'], types=[2],
                          category='boss', model_id=0x35, lit=True),
    # lane ps2cast2 (2026-10-14): the chapter-1 non-Ganado actors still drawn from the GC source (CH1 audit fix 5).
    # Each is one modelInit(BIN, TPL) of its module's R0 init; lit (normals kept) like the source path draws them.
    # em2a_R0_Init: type 0 bear trap modelInit(ARC 4, ARC 5), type 1 (6, 7), type 2 (8, 9) (types 1 / 2 scale
    # parts 1 / 2 pos.z by hp at init: the wire / bomb models)
    'trap-em2a-00': dict(archive='em2a', sections=[(4, 'body')], tpl=5, rooms=['r100', 'r105', 'r106', 'r107', 'r10a', 'r111', 'r113'],
                         types=[0], category='registry', model_id=0x2a, lit=True),
    'trap-em2a-02': dict(archive='em2a', sections=[(8, 'body')], tpl=9, rooms=['r100', 'r105', 'r106', 'r107', 'r10a', 'r111', 'r113'],
                         types=[2], category='registry', model_id=0x2a, lit=True, shift=2),   # 4.2 m long: GC shift 2
    # em29_R0_Init: the bat, modelInit(ARC 4, ARC 5); 7 PS2 corners sit one texel past a GX_REPEAT image edge
    'bat-em29-00': dict(archive='em29', sections=[(4, 'body')], tpl=5, rooms=['r106', 'r10e'], types=[],
                        category='registry', model_id=0x29, lit=True, uv_edge_texels=1),
    # em2e_R0_Init: the wall crawler, type 0 modelInit(ARC 4, ARC 5), type 1 (ARC 4, ARC 6)
    'crawler-em2e-00': dict(archive='em2e', sections=[(4, 'body')], tpl=5, rooms=['r106'], types=[0],
                            category='registry', model_id=0x2e, lit=True),
    'crawler-em2e-01': dict(archive='em2e', sections=[(4, 'body')], tpl=6, rooms=['r106'], types=[1],
                            category='registry', model_id=0x2e, lit=True),
    # em27_R0_Init: the lake fish, modelInit(ARC 4, ARC 5) for every type (type 1 only scales x3)
    'fish-em27-00': dict(archive='em27', sections=[(4, 'body')], tpl=5, rooms=['r107', 'r10b', 'r11b', 'r10e'], types=[0, 1],
                         category='registry', model_id=0x27, lit=True),
    # em24_R0_Init: the snake, modelInit(ARC 5, ARC 6) (ARC 0x19 + 0x1A..0x1C are the dropped item models, SetWeapon)
    'snake-em24-00': dict(archive='em24', sections=[(5, 'body')], tpl=6, rooms=['r10a', 'r108', 'r11a'], types=[],
                          category='registry', model_id=0x24, lit=True),
    # pl0f_R0_Init: the boat, modelInit(ARC 5, ARC 6) for every type / set
    'boat-pl0f-00': dict(archive='pl0f', sections=[(5, 'body')], tpl=6, rooms=['r10b', 'r11b', 'r10e'], types=[],
                         category='registry', model_id=0x0f, lit=True, shift=3),   # 2.7 m: positions beyond +-2048 mm
    # em3b_R0_Init (lane ps2cast 2026-10-15): the r118 mine cart, types 1 / 2 modelInit(ARC 0xB, ARC 0xC) (type 0 is the
    # truck, ARC 4 / 5: Codex CH23 truck-em3b-00)
    'cart-em3b-01': dict(archive='em3b', sections=[(0xb, 'body')], tpl=0xc, rooms=['r118'], types=[1, 2],
                         category='registry', model_id=0x3b, lit=True, repeat_uvs=True),
    # Em11Set type 7 + em10ModelInit: body BIN mot[1] 0x1FC / TPL mot[0] 0x1FD, head (em10HeadSet) BIN mot[2] 0x1FE /
    # TPL mot[5] 0x201, relaxed hands (em10HandSet type 0) BIN mot[6] 0x204 and mot[11] 0x208, both with TPL mot[0]
    'zealot-em11-07': dict(archive='em11', sections=[(0x1fc, 'body'), (0x1fe, 'head'), (0x204, 'right-hand'), (0x208, 'left-hand')],
                           tpl=0x1fd, section_tpls={0x1fe: 0x201}, rooms=['r117'], types=[7], category='registry',
                           model_id=0x11, lit=True, subset_bones=True),
    # NATIVE_MODEL_REGISTRY_POOL (lane ps2cast 2026-10-15): Em17Set type 0xc's whole section pool (body mot[1] 0x1CD /
    # TPL mot[0] 0x1CE; head mot[2] 0x1CF and hit head mot[3] 0x1D0 with TPL mot[5] 0x1CE; em10HandSet right mot[6..10]
    # 0x1C0..0x1C4 and left mot[11..14] 0x1C5..0x1C8, TPL mot[0]; em10SetAccesory whood mot[23] 0x1D3 with TPL mot[24]
    # 0x1D4 (flag 0x400000) or mot[25] 0x1D5 (flag 0x40000)). Caps / glasses are separate Obj12 objects.
    'ganado-em17-0cp': dict(archive='em17', sections=[
        (0x1cd, 'body'), (0x1cf, 'head'), (0x1d0, 'head-hit'),
        (0x1c0, 'right-hand'), (0x1c1, 'right-open'), (0x1c2, 'right-point'), (0x1c3, 'right-grip'), (0x1c4, 'right-scythe'),
        (0x1c5, 'left-hand'), (0x1c6, 'left-open'), (0x1c7, 'left-point'), (0x1c8, 'left-grip'),
        (0x1d3, 'whood', 0x1d4), (0x1d3, 'whood-b', 0x1d5)],
        tpl=0x1ce, rooms=['r108', 'r113', 'r118'], types=[12], category='registry', model_id=0x17, lit=True,
        subset_bones=True),
    # NATIVE_MODEL_REGISTRY_POOL (lane cast16 2026-10-16): Em16Set type 11 (r11d). Its body / head / hands / TPL equal
    # em15 type 11 (native_appearance_alias.py: 13 entries identical), but its em10SackSet sack (mot[21] 0x1D1 with TPL
    # mot[22] 0x1D2) and whood (mot[23] 0x1D3 with TPL mot[24] 0x1D4 / mot[25] 0x1D5) are em16's own entries, so the
    # alias table holds it out ('accessory-differs') and the actor drew GC. As a pool it binds every section it shows.
    'ganado-em16-0bp': dict(archive='em16', sections=[
        (0x1c9, 'body'), (0x1cb, 'head'), (0x1cc, 'head-hit'),
        (0x1c0, 'right-hand'), (0x1c1, 'right-open'), (0x1c2, 'right-point'), (0x1c3, 'right-grip'), (0x1c4, 'right-scythe'),
        (0x1c5, 'left-hand'), (0x1c6, 'left-open'), (0x1c7, 'left-point'), (0x1c8, 'left-grip'),
        (0x1d1, 'sack', 0x1d2), (0x1d3, 'whood', 0x1d4), (0x1d3, 'whood-b', 0x1d5)],
        tpl=0x1ca, rooms=['r11d'], types=[11], category='registry', model_id=0x16, lit=True, subset_bones=True),
    # NATIVE_MODEL_REGISTRY_POOL (lane ps2cast 2026-10-15): the type 7 zealot's whole section pool, so every spawn's
    # source infos bind (em10ModelInit order: body, em10HeadSet head mot[2] / hit heads mot[3] / mot[4] with TPL mot[5];
    # em10HandSet right mot[6..9] and left mot[11..15], TPL mot[0]; em10SetAccesory hoods mot[26] / mot[27] with TPL
    # mot[0] and accessories mot[28..39] in BIN / TPL pairs). Not listed: the subArc TPL 0x220 accessory and the
    # Wep_type 12 subArc hand (the actor then keeps its source path).
    'zealot-em11-07p': dict(archive='em11', sections=[
        (0x1fc, 'body'), (0x1fe, 'head'), (0x1ff, 'head-hit'), (0x200, 'head-hit2'),
        (0x204, 'right-hand'), (0x205, 'right-open'), (0x206, 'right-point'), (0x207, 'right-grip'),
        (0x208, 'left-hand'), (0x209, 'left-open'), (0x20a, 'left-point'), (0x20b, 'left-grip'), (0x20c, 'left-grip2'),
        (0x202, 'hood'), (0x203, 'hood-up'),
        (0x20d, 'acc0'), (0x20f, 'acc1'), (0x211, 'acc2'), (0x213, 'acc3'), (0x215, 'acc4'), (0x217, 'acc5')],
        tpl=0x1fd, section_tpls={0x1fe: 0x201, 0x1ff: 0x201, 0x200: 0x201, 0x20d: 0x20e, 0x20f: 0x210, 0x211: 0x212,
                                 0x213: 0x214, 0x215: 0x216, 0x217: 0x218},
        rooms=['r117'], types=[7], category='registry', model_id=0x11, lit=True, subset_bones=True),
}


# lane cast16 (2026-10-16): the castle Zealot modules (em14 / em19 / em1a / em1b: em10.cpp + <em>_set.cpp) use em11's
# type 7 section layout (the same ARC numbers, own archives). Types 8 / 9 change the TPL / body / head rows, type 10
# (em1b) is bodyless-head (mot[2..5] = 0). Each is a NATIVE_MODEL_REGISTRY_POOL preset like zealot-em11-07p.
def _zealot_pool(archive, typ, rooms):
    base = PRESETS['zealot-em11-07p']
    body, tpl, head, htpl = {7: (0x1fc, 0x1fd, 0x1fe, 0x201), 8: (0x1fc, 0x21a, 0x21b, 0x21c),
                             9: (0x21d, 0x21e, 0x21f, 0x201), 10: (0x221, 0x222, None, None)}[typ]
    secs = [(body, 'body')]
    if head is not None:
        secs += [(head, 'head'), (0x1ff, 'head-hit'), (0x200, 'head-hit2')]
    secs += [x for x in base['sections'] if x[1] not in ('body', 'head', 'head-hit', 'head-hit2')]
    st = {k: v for k, v in base['section_tpls'].items() if k not in (0x1fe, 0x1ff, 0x200)}
    if head is not None:
        st.update({head: htpl, 0x1ff: htpl, 0x200: htpl})
    return dict(archive=archive, sections=secs, tpl=tpl, section_tpls=st, rooms=rooms, types=[typ],
                category='registry', model_id=int(archive[2:], 16), lit=True, subset_bones=True)


for _a, _types, _rooms in (('em14', (7, 8, 9), ['r20f']), ('em19', (7, 8, 9), ['r20d']),
                           ('em1a', (7, 8, 9), ['r209']), ('em1b', (7, 8, 10), ['r201', 'r20c'])):
    for _t in _types:
        PRESETS[f'zealot-{_a}-{_t:02x}p'] = _zealot_pool(_a, _t, _rooms)
# Em14Set type 6 (r20f; not a Ganado: Ganado stays 0): body mot[1] 0x1E7 / TPL mot[0] 0x1E8, head mot[2..4] 0x1E9 with
# TPL mot[5] 0x1EA, mot[16] 0x1F0 with mot[17] 0x1F1, right hands mot[6..9] 0x1F4..0x1F7, left mot[11..14] 0x1F8..0x1FB,
# mot[18..20] 0x1ED..0x1EF.
# lane cast16 (2026-10-16): the stage-3 soldiers (em1d / em1e / em1f; em10.cpp class 2) as NATIVE_MODEL_REGISTRY_POOL
# presets: lane ps2cast-st3's per-type (body, head) pairs (95f47e7d) plus every section the source can attach, so a
# soldier's variable info list binds (ps2cast-st3: "runtime admission needs a variable-info soldier plan"). Em1?Set:
# body mot[1] / TPL mot[0] (0x22F / 0x230 or 0x247 / 0x248), head mot[2] / TPL mot[5], hit head mot[3] = mot[4] 0x233
# (TPL mot[5]), right hands mot[6..9] 0x234..0x237, left mot[11..15] 0x238..0x23C (TPL mot[0]).
def _soldier_pool(archive, body, head, rooms, types):
    return dict(archive=archive, sections=[(body, 'body'), (head, 'head'), (0x233, 'head-hit'),
                (0x234, 'right-hand'), (0x235, 'right-open'), (0x236, 'right-point'), (0x237, 'right-grip'),
                (0x238, 'left-hand'), (0x239, 'left-open'), (0x23a, 'left-point'), (0x23b, 'left-grip'), (0x23c, 'left-grip2'),
                # em10.cpp EM10_ACC_PARTS (flag bits, types 14..24): hoods / helmets 0x23D / 0x23F / 0x241 (pHood) and
                # 0x243 / 0x245 (pAccesory[2]). Their PS2 BINs carry the whole body bone table while the GC sections list
                # only their parts (ps2_body_table_sections). 0x24F (pAccesory[3]) is a different PS2 mesh: not listed.
                (0x23d, 'hood-a'), (0x23f, 'hood-b'), (0x241, 'hood-c'), (0x243, 'acc2-a'), (0x245, 'acc2-b')],
                tpl=body + 1, section_tpls={head: head + 1, 0x233: head + 1, 0x23d: 0x23e, 0x23f: 0x240, 0x241: 0x242,
                                            0x243: 0x244}, rooms=rooms, types=types, category='registry',
                model_id=int(archive[2:], 16), lit=True, subset_bones=True, ps2_body_table_sections=True)


for _n, _a, _b, _h, _r, _t in (
        ('em1d-0e', 'em1d', 0x22f, 0x231, ['r300', 'r320', 'r327'], 14), ('em1d-12', 'em1d', 0x247, 0x231, ['r320', 'r327'], 18),
        ('em1d-0f', 'em1d', 0x22f, 0x249, ['r300', 'r320', 'r327'], 15), ('em1d-13', 'em1d', 0x247, 0x249, ['r320', 'r327'], 19),
        ('em1d-10', 'em1d', 0x22f, 0x24b, ['r300', 'r320', 'r327'], 16), ('em1d-14', 'em1d', 0x247, 0x24b, ['r320', 'r327'], 20),
        ('em1d-11', 'em1d', 0x22f, 0x24d, ['r300', 'r320', 'r327'], 17), ('em1d-15', 'em1d', 0x247, 0x24d, ['r320', 'r327'], 21),
        ('em1e-0e', 'em1e', 0x22f, 0x231, ['r301', 'r305', 'r30e', 'r316', 'r31d'], 14),
        ('em1e-0f', 'em1e', 0x22f, 0x249, ['r301', 'r30e', 'r316', 'r31d'], 15),
        ('em1e-17', 'em1e', 0x247, 0x24d, ['r301', 'r305', 'r30e', 'r316'], 23),
        ('em1e-19', 'em1e', 0x247, 0x24b, ['r301', 'r303', 'r305', 'r30e', 'r316'], 25),
        ('em1f-0e', 'em1f', 0x22f, 0x231, ['r304', 'r30b', 'r30c', 'r30f', 'r311', 'r321', 'r334'], 14),
        ('em1f-0f', 'em1f', 0x22f, 0x249, ['r304', 'r30b', 'r30c', 'r30f', 'r311', 'r321', 'r330', 'r334'], 15),
        ('em1f-10', 'em1f', 0x22f, 0x24b, ['r304', 'r30b', 'r30c', 'r30f', 'r311', 'r321', 'r330', 'r334'], 16),
        ('em1f-18', 'em1f', 0x247, 0x24d, ['r304', 'r30c', 'r311', 'r330'], 24)):
    PRESETS['soldr-%sp' % _n] = _soldier_pool(_a, _b, _h, _r, [_t])
# em1f's 0x247 body rests part 9 (attach 31) elsewhere than hit head 0x233 does: type 24 keeps its own head only.
# The GC stump 0x233 (em10HeadSet no 1: ModInfoMgr.create(mot[3], mot[5])) indexes textures past these heads' TPLs
# (model_registry: 'colour texture index outside the TPL'), so the source pair is not identifiable: no stump section.
for _n in ('em1f-18', 'em1d-11', 'em1d-15', 'em1e-0f'):
    _s = PRESETS['soldr-%sp' % _n]
    _s['sections'] = [x for x in _s['sections'] if x[0] != 0x233]; _s['section_tpls'].pop(0x233)
# Body 0x247 types: 0x245 under the type's body TPL indexes past it (em1e types 23 / 25), and em1f type 24's hoods /
# accessories rest elsewhere than its body bones (convert asserts); those sections keep their source path.
for _n, _drop in (('em1e-17', (0x245,)), ('em1e-19', (0x245,)), ('em1f-18', (0x23d, 0x23f, 0x241, 0x243, 0x245))):
    _s = PRESETS['soldr-%sp' % _n]
    _s['sections'] = [x for x in _s['sections'] if x[0] not in _drop]
    for _b in _drop:
        _s['section_tpls'].pop(_b, None)
# em1d rooms r320 / r327 load all eight soldier types (bodies 0x22F / 0x247 x four heads). One pool per body carries the
# four heads (own TPLs), the stump under each head TPL it fits (not 0x24E), the hands under that body's TPL and the
# hoods / accessories (NMRBIN, r327: a 0x247 soldier shows hands 0x237 / 0x238 with TPL 0x248, hood 0x23D, 0x243).
for _body, _types in ((0x22f, (14, 15, 16, 17)), (0x247, (18, 19, 20, 21))):
    _s = _soldier_pool('em1d', _body, 0x231, ['r320', 'r327'], list(_types))
    _heads = [(0x249, 'head-b'), (0x24b, 'head-c'), (0x24d, 'head-d')]
    _s['sections'][2:2] = [(h, r, h + 1) for h, r in _heads] + [(0x233, 'stump-b', 0x24a), (0x233, 'stump-c', 0x24c)]
    PRESETS['soldr-1d-%xp' % _body] = _s
PRESETS['soldr-em1d-02'] = dict(archive='em1d', sections=[(0x22b, 'body')], tpl=0x22c, rooms=['r300', 'r320', 'r327'],
                                  types=[2], category='registry', model_id=0x1d, lit=True)
# lane cast16 (2026-10-16, chapter 4 castle): pool presets generated from the decompiled <em>_set.cpp motion tables
# (case labels sharing a block share the table). Sections follow em10.cpp's creates: em10ModelInit body mot[1] / TPL
# mot[0]; em10HeadSet mot[2] / mot[3] / mot[4] with TPL mot[5]; em10HandSet mot[6..15] with TPL mot[0]; em10SackSet
# mot[21] / mot[22]; whood mot[23] with mot[24] / mot[25]; em10SetAccesory hoods mot[26] / mot[27] (TPL mot[0]) and
# accessories (28, 29) (30, 31) (32, 33) (34, 35) (36, 37) (38, 39) (38, 40). subArc entries are not listed (the actor
# then keeps its source path).
def _set_tables(archive):
    import re
    path = Path(__file__).resolve().parents[3] / 'src' / archive / f'{archive}_set.cpp'
    out = {}; cur = None
    for line in path.read_text(encoding='utf-8').splitlines():
        m = re.match(r'\s*case\s+(0x[0-9a-fA-F]+|\d+)\s*:', line)
        if m:
            if cur is not None and cur['done']:
                cur = None
            if cur is None:
                cur = {'mot': {}, 'done': False}
            out[int(m.group(1), 0)] = cur['mot']
            continue
        m = re.search(r'mot\[(\d+)\]\s*=\s*ARC\((0x[0-9A-Fa-f]+)\)', line)
        if m and cur is not None:
            cur['mot'][int(m.group(1))] = int(m.group(2), 16)
        if cur is not None and re.search(r'\bbreak;|\breturn\b', line):
            cur['done'] = True
    return {t: m for t, m in out.items() if m}


def _set_pool(archive, typ, rooms, drop=()):
    mot = _set_tables(archive)[typ]; g = mot.get
    secs, seen = [], set()
    def add(b, role, t):
        if b is None or t is None or b in drop or (b, t) in seen:
            return
        seen.add((b, t)); secs.append((b, role, t))
    add(g(1), 'body', g(0))
    for k, role in ((2, 'head'), (3, 'head-hit'), (4, 'head-hit2')):
        add(g(k), role, g(5))
    for k in range(6, 16):
        add(g(k), 'hand%d' % k, g(0))
    add(g(21), 'sack', g(22)); add(g(23), 'whood', g(24)); add(g(23), 'whood-b', g(25))
    add(g(26), 'hood', g(0)); add(g(27), 'hood-up', g(0))
    # (38, 40), the mot[38] variant with its second TPL, is not listed: its masked texture would make a fifth actor
    # material (ACTOR_MATERIALS 4); that variant keeps its source path.
    for b, t in ((28, 29), (30, 31), (32, 33), (34, 35), (36, 37), (38, 39)):
        add(g(b), 'acc%d' % b, g(t))
    return dict(archive=archive, sections=secs, tpl=g(0), rooms=rooms, types=[typ], category='registry',
                model_id=int(archive[2:], 16), lit=True, subset_bones=True)


# Sections whose GC part rests elsewhere than the type's body bone (convert asserts): em1c types 10 / 13 (own bodies
# 0x221 / 0x223): hoods 0x202 / 0x203 and accessories 0x20D..0x217; em13 type 6 (robed): hands 0x1F5 0x1F6 0x1F9..0x1FB.
# em15 type 11's head rests 2.02 mm off its body bone: convert it with --bone-tol 2.1 (render approximation).
_SET_POOL_DROPS = {('em1c', 10): (0x202, 0x203, 0x20d, 0x20f, 0x211, 0x213, 0x215, 0x217),
                   ('em1c', 13): (0x202, 0x203, 0x20d, 0x20f, 0x211, 0x213, 0x215, 0x217),
                   ('em1b', 10): (0x202, 0x203, 0x20d, 0x20f, 0x211, 0x213, 0x215, 0x217),
                   ('em13', 6): (0x1f5, 0x1f6, 0x1f9, 0x1fa, 0x1fb)}
for _a, _types, _rooms, _kind in (('em11', (8, 9), ['r212', 'r217', 'r222', 'r226'], 'zealot'),
                                  ('em1c', (9, 10, 13), ['r218'], 'zealot'),
                                  ('em1b', (10,), ['r201', 'r20c'], 'zealot'),
                                  ('em13', (0, 1, 3, 6), ['r225'], 'ganado'),
                                  ('em15', (0, 3, 4, 11), ['r21b'], 'ganado'),
                                  ('em16', (3, 4), ['r223'], 'ganado')):
    for _t in _types:
        PRESETS['%s-%s-%02xg' % (_kind, _a, _t)] = _set_pool(_a, _t, _rooms, _SET_POOL_DROPS.get((_a, _t), ()))
# lane cast16 (2026-10-16, chapter 4 castle): armour and Novistador. em25.cpp em25_R0_Init modelInit(ARC 4, ARC 5) for
# every type; em3c.cpp em3cModelInit types 0 / 1 body ARC 5 / TPL 6, types 2 / 3 body ARC 9 / TPL 0xA, plus
# ModInfoMgr.create(ARC 7 or 0xB, ARC 8); em2d.cpp type 4 modelInit(ARC 0xD, ARC 0xE).
PRESETS['armor-em25-00'] = dict(archive='em25', sections=[(4, 'body')], tpl=5, rooms=['r214', 'r217', 'r228'],
                                types=[0, 9], category='registry', model_id=0x25, lit=True)
PRESETS['armor-em3c-00'] = dict(archive='em3c', sections=[(5, 'body'), (7, 'extra', 8)], tpl=6, rooms=['r216'],
                                types=[0, 1], category='registry', model_id=0x3c, lit=True, subset_bones=True, uv_edge_texels=12)
PRESETS['armor-em3c-02'] = dict(archive='em3c', sections=[(9, 'body'), (0xb, 'extra', 8)], tpl=0xa, rooms=['r216'],
                                types=[2, 3], category='registry', model_id=0x3c, lit=True, subset_bones=True, uv_edge_texels=12, shift=3)
# castle18 r205 (2026-10-18): em2d_R0_Init selects each type's own body/TPL. Type 0 has an identical
# 91-part PS2/GC skeleton; type 2 has 91 PS2 bones / 57 GC parts, with every weighted bone in the shared set.
# The existing converter checks every shared parent/rest translation and rejects any PS2-only weight.
PRESETS['novis-em2d-00'] = dict(archive='em2d', sections=[(5, 'body')], tpl=6, rooms=['r205'],
                                types=[0], category='registry', model_id=0x2d, lit=True, shift=3)
PRESETS['novis-em2d-02'] = dict(archive='em2d', sections=[(9, 'body')], tpl=0xa, rooms=['r205'],
                                types=[2], category='registry', model_id=0x2d, lit=True, ps2_superset_bones=True, shift=3)
PRESETS['novis-em2d-04'] = dict(archive='em2d', sections=[(0xd, 'body')], tpl=0xe, rooms=['r213', 'r21d'],
                                types=[4], category='registry', model_id=0x2d, lit=True, ps2_superset_bones=True, shift=3)
# em10.cpp: the robe ModInfoMgr.create(mot[16], mot[17]); the second info create(mot[19] or mot[18], mot[17]); the
# third create(mot[20], mot[0]).
PRESETS['zealot-em14-06p'] = dict(archive='em14', sections=[
    (0x1e7, 'body'), (0x1e9, 'head'), (0x1f0, 'extra'),
    (0x1f4, 'right-hand'), (0x1f8, 'left-hand'), (0x1ed, 'acc0'), (0x1ee, 'acc1'), (0x1ef, 'acc2')],
    tpl=0x1e8, section_tpls={0x1e9: 0x1ea, 0x1f0: 0x1f1, 0x1ed: 0x1f1, 0x1ee: 0x1f1}, rooms=['r20f'], types=[6], category='registry',
    model_id=0x14, lit=True, subset_bones=True)


# lane cast16 (2026-10-16): chapter 4 rooms reuse these existing conversions (CH4-FOUNDATIONS cast list).
PRESETS['zealot-em11-07p']['rooms'] = PRESETS['zealot-em11-07p']['rooms'] + ['r212', 'r226']
for _n in ('merchant18-c0', 'merchant18-o0'):
    PRESETS[_n]['rooms'] = PRESETS[_n]['rooms'] + ['r220', 'r229', 'r22a']
PRESETS['bat-em29-00']['rooms'] = PRESETS['bat-em29-00']['rooms'] + ['r229']
for _t in (6, 7, 8, 9):
    PRESETS['zealot-em14-%02xp' % _t]['rooms'] = PRESETS['zealot-em14-%02xp' % _t]['rooms'] + ['r211', 'r214', 'r227']
PRESETS['zealot-em1a-09p']['rooms'] = PRESETS['zealot-em1a-09p']['rooms'] + ['r214']


# Em1eSet type 6 (r305 / r31d NMRBIN: the robed class-0 type, em10.cpp robe infos): zealot-em14-06p's entries on em1e.
PRESETS['soldr-em1e-06p'] = dict(PRESETS['zealot-em14-06p'], archive='em1e', rooms=['r305', 'r31d'], model_id=0x1e)

# Type 9 Zealots with em10SetAccesory flag 2 (lane ch4found16 95584fc1, CH4-FOUNDATIONS round 5): BIN 0x211 + subArc TPL
# 0x220, which the pool presets omit. r211 / r214 / r218 / r227.
for _n, _q in (('zealot-em14-09p', 'zealot-em14-09q'), ('zealot-em1c-09g', 'zealot-em1c-09h')):
    PRESETS[_q] = dict(PRESETS[_n], sections=PRESETS[_n]['sections'] + [(0x211, 'acc2-b', 0x220)],
                       rooms=[r for r in PRESETS[_n]['rooms'] if r in ('r211', 'r214', 'r218', 'r227')])
# r218's type 9 Zealots also wear em10SetAccesory's mot[38] variant with its second TPL (BIN 0x217 + TPL 0x219, mot[40];
# NMRBIN r218 kill rig: 21d 21f 204 208 20f|210 217|219). _set_pool leaves (38, 40) out for the descriptor-wide material
# count; an actor carries one of the two 0x217 colours, so its own count stays within ACTOR_MATERIALS 4 (model_registry.py
# counts a pool per actor). Added to zealot-em1c-09h only (the em14 / em1a / em11 type 9 pools have not shown it).
PRESETS['zealot-em1c-09h']['sections'] = PRESETS['zealot-em1c-09h']['sections'] + [(0x217, 'acc38-b', 0x219)]
# castle18 (2026-10-18): source type 7/8 alternate accessory selections observed in r208/r209 and r226.
# em10SetAccesory flag 2 selects BIN mot[32] with subArc TPL 0x220; flag 0x4000 selects mot[38]/mot[40].
# Keep both original selections and the complete source section pool. The registry already counts alternative
# TPLs of one BIN once, since the source attaches only one accessory for each slot; no material limit changes.
PRESETS['zealot-em1a-07q'] = dict(PRESETS['zealot-em1a-07p'],
    sections=PRESETS['zealot-em1a-07p']['sections'] + [(0x211, 'acc2-b', 0x220), (0x217, 'acc5-b', 0x219)],
    rooms=['r208', 'r209'])
PRESETS['zealot-em1a-08q'] = dict(PRESETS['zealot-em1a-08p'],
    sections=PRESETS['zealot-em1a-08p']['sections'] + [(0x211, 'acc2-b', 0x220), (0x217, 'acc5-b', 0x219)],
    rooms=['r208', 'r209'])
PRESETS['zealot-em11-08h'] = dict(PRESETS['zealot-em11-08g'],
    sections=PRESETS['zealot-em11-08g']['sections'] + [(0x211, 'acc32-b', 0x220)], rooms=['r226'])
# em3cModelInit attaches a weapon after body and chainmail: C/D for types 0/2, E/F for types 1/3.
# Separate complete descriptors preserve those original BIN/TPL identities and the game's unchanged 1.2 scale.
for _typ, _body, _weapon in ((0, '00', 0xc), (1, '00', 0xe), (2, '02', 0xc), (3, '02', 0xe)):
    _base = PRESETS['armor-em3c-' + _body]
    PRESETS['armor-em3c-%02xw' % _typ] = dict(_base,
        sections=_base['sections'] + [(_weapon, 'weapon', _weapon + 1)], types=[_typ])

# lane cast16 (2026-10-17): r315's one enemy row (emleon07.esl row 11) is em1e type 6.
PRESETS['soldr-em1e-06p']['rooms'] = PRESETS['soldr-em1e-06p']['rooms'] + ['r315']
# lane cast16 (2026-10-17, island bosses): em36.cpp em36_R0_Init types 0 / 1 (and the default, type 7 in r326)
# modelInit(ARC 4, ARC 0x13 / 0x14), types 2 / 3 modelInit(ARC 0x15, ARC 0x24); em36PartsSet attaches limbs 0..6
# (torso, head, arms, legs, the death variant), each intact (`on` 0) or lost (`on` 1): types 0 / 1 ARC 5..0x12,
# types 2 / 3 ARC 0x16..0x23, every one with the type's TPL (ModInfoMgr.create(bin, tpl)).
def _em36(body, limb, tpl, types, rooms):
    secs = [(body, 'body')]
    for k in range(7):
        secs += [(limb + 2 * k, 'limb%d' % k), (limb + 2 * k + 1, 'limb%d-b' % k)]
    return dict(archive='em36', sections=secs, tpl=tpl, rooms=rooms, types=types, category='registry', model_id=0x36, lit=True, shift=2)
PRESETS['regen-em36-00'] = _em36(4, 5, 0x13, [0, 7], ['r306', 'r307', 'r308', 'r30d', 'r326'])
PRESETS['regen-em36-01'] = _em36(4, 5, 0x14, [1], ['r306', 'r30d'])
PRESETS['regen-em36-02'] = dict(_em36(0x15, 0x16, 0x24, [2, 3], ['r309', 'r310']), subset_bones=True, ps2_body_table_sections=True)  # limb0-b: GC 59 parts, PS2 the 60-bone body table
# em39.cpp (Krauser, r31c) type 1 modelInit(ARC 0x15, ARC 0x17) + ModInfoMgr.create (5, 0x10), (6, 0x18), (7, 0x12), the knife
# (9, 0x10), em39HandSet right hands 0xA..0xD and left hands 0xE / 0xF (TPL 0x14), em39DieModelSet (0x21, 0x22); type 2
# modelInit(ARC 0x1A, ARC 0x1D) + (5, 0x10), (6, 0x1E), (0x1B, 0x1F), (0x1C, 0x20), the knife, right hands only.
# NOT CONVERTED (cast16 10-17): `convert` refuses both Krauser presets - the PS2 em39 skeleton is not the GC one (body
# bone positions differ by up to 16.7 mm for type 1, 55.7 mm for type 2), so the PS2 mesh needs a retarget (a look decision).
_EM39_HANDS = [(0xa, 'right-hand', 0x14), (0xb, 'right-hand-b', 0x14), (0xc, 'right-hand-c', 0x14), (0xd, 'right-hand-d', 0x14)]
PRESETS['krauser-em39-01'] = dict(archive='em39', sections=[(0x15, 'body'), (5, 'acc0', 0x10), (6, 'acc1', 0x18), (7, 'acc2', 0x12),
                                  (9, 'knife', 0x10)] + _EM39_HANDS + [(0xe, 'left-hand', 0x14), (0xf, 'left-hand-b', 0x14),
                                  (0x21, 'death', 0x22)], tpl=0x17, rooms=['r31c'], types=[1], category='registry', model_id=0x39, lit=True)
PRESETS['krauser-em39-02'] = dict(archive='em39', sections=[(0x1a, 'body'), (5, 'acc0', 0x10), (6, 'acc1', 0x1e), (0x1b, 'acc2', 0x1f),
                                  (0x1c, 'acc3', 0x20), (9, 'knife', 0x10)] + _EM39_HANDS + [(0x21, 'death', 0x22)],
                                  tpl=0x1d, rooms=['r31c'], types=[2], category='registry', model_id=0x39, lit=True)
# em3a.cpp (the r31c gunship) types 0 / 1 modelInit(ARC 5, ARC 6), type 2 modelInit(ARC 0xB, ARC 0xC).
PRESETS['gunship-em3a-00'] = dict(archive='em3a', sections=[(5, 'body')], tpl=6, rooms=['r31c'], types=[0, 1], category='registry',
                                  model_id=0x3a, lit=True)
PRESETS['gunship-em3a-02'] = dict(archive='em3a', sections=[(0xb, 'body')], tpl=0xc, rooms=['r31c'], types=[2], category='registry',
                                  model_id=0x3a, lit=True)
# em32.cpp (U-3, r31b) modelInit(ARC 4, ARC 5) + ModInfoMgr.create(ARC 6, ARC 5) and the texture-blended skin (ARC 7, ARC 5).
PRESETS['u3-em32-00'] = dict(archive='em32', sections=[(4, 'body'), (6, 'extra'), (7, 'skin')], tpl=5, rooms=['r31b'], types=[0],
                             category='registry', model_id=0x32, lit=True, ps2_superset_bones=True, shift=2)
# em3d.cpp (r320) modelInit(ARC 5, ARC 6). Converts (shift 1), but no room package yet: its body has three GC masked materials
# (colours 1 / 3 / 20, masks 2 / 4 / 21): ps2_mask_runs.py --multi-mask bakes all three into one mask run (lane geodrop17;
# r320 package spec model-registry/ps2-ch5-r320.json, model_registry.py --roles5 --role-tex23: its TPL 6 has 23 images).
PRESETS['heli-em3d-00'] = dict(archive='em3d', sections=[(5, 'body')], tpl=6, rooms=['r320'], types=[0], category='registry',
                               model_id=0x3d, lit=True, shift=1)


def section_specs(spec):
    """Source BIN/role/TPL selections; old single-TPL presets keep their order."""
    overrides = spec.get('section_tpls', {})
    bins = {x[0] for x in spec['sections']}
    if set(overrides) - bins:
        raise ValueError('section_tpls names a BIN outside the selected sections')
    # a section may name its own TPL as a third element (the same BIN under two TPLs: em10SetAccesory's whood colours)
    return [(x[0], x[1], x[2] if len(x) > 2 else overrides.get(x[0], spec['tpl'])) for x in spec['sections']]


def tpl_wrap_modes(data, image):
    """Read the original GC TPL's wrap modes before normalizing repeated UVs."""
    if len(data) < 12:
        raise ValueError('truncated source TPL header')
    magic, count, table = struct.unpack_from('>3I', data)
    if magic != 0x20af30 or image < 0 or image >= count or table + count * 8 > len(data):
        raise ValueError('invalid source TPL image')
    offset = struct.unpack_from('>I', data, table + image * 8)[0]
    if offset < 12 or offset + 20 > len(data):
        raise ValueError('truncated source TPL sampler')
    return struct.unpack_from('>2I', data, offset + 12)


def repeat_triangle_uv(uvs, wrap):
    """Shift each complete triangle by integer texture periods; never wrap corners.

    This preserves interpolation and sample phase for GX_REPEAT. A triangle
    crossing a period edge cannot be represented inside one atlas cell and is
    refused. Existing presets do not request this transform.
    """
    result = [list(uv) for uv in uvs]
    for axis in range(2):
        lo, hi = min(uv[axis] for uv in uvs), max(uv[axis] for uv in uvs)
        if 0 <= lo and hi <= 256:
            continue
        if wrap[axis] != 1:
            raise ValueError('UV normalization needs GX_REPEAT on the shifted axis')
        shift = -(lo // 256) * 256
        if lo + shift < 0 or hi + shift > 256:
            raise ValueError('repeated UV triangle crosses an atlas cell boundary')
        for uv in result:
            uv[axis] += shift
    return result


def sha(b):
    return hashlib.sha256(b).hexdigest()


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, str(path))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


# ------------------------------------------------------------------------------------------ inputs


# disc extracts are rebuildable: cached on ext4 (lane evidence), not in the private store
INPUTS = Path(os.environ.get('PS2CAST_INPUTS', '//wsl.localhost/Ubuntu-24.04/root/probe/lanes/ps2cast/inputs'))


def inputs(archive, out, ps2_iso, gc_iso):
    d = INPUTS
    d.mkdir(parents=True, exist_ok=True)
    p, g = d / f'{archive}.dat', d / f'{archive}.drs'
    if not p.exists():
        p.write_bytes(pb.afs_read(ps2_iso, f'{archive}.dat'))
    if not g.exists():
        sys.path.insert(0, str(HERE))
        from assetpipe.rooms import GcIso
        g.write_bytes(GcIso(gc_iso).read(f'em/{archive}.drs'))
    pd, gd = p.read_bytes(), g.read_bytes()
    rec = dict(ps2=dict(iso=str(ps2_iso), afs_entry=f'{archive}.dat', bytes=len(pd), sha256=sha(pd), cache=str(p)),
               gc=dict(iso=str(gc_iso), file=f'em/{archive}.drs', bytes=len(gd), sha256=sha(gd), cache=str(g)))
    ps2 = {i: (t, b) for i, t, b in pb.dat_entries(pd)}
    gc = drs.Drs(gd)
    return ps2, gc, rec


def gc_entry(gc, arc, tag):
    t, b = gc.entries[arc - 4]
    assert drs.tag_name(t) == tag, (hex(arc), t, tag)
    return b


def ps2_entry(ps2, arc, tag):
    t, b = ps2[arc - 4]
    assert t == tag, (hex(arc), t, tag)
    return b


# ------------------------------------------------------------------------------------------ GC side


def gc_skeleton(bin_bytes):
    mdl = modelbin.parse(bin_bytes)
    try:
        mdl.check_tree()
    except ValueError:
        # the stage-3 soldier bodies list some parents after their children (em1d BIN 0x22F: part 8 -> parent 27);
        # the rest pose is the same accumulation, resolved parent first (acyclic checked)
        return _gc_skeleton_any_order(mdl)
    bones = []
    for p in mdl.parts:
        m = np.eye(4)
        m[:3, 3] = p.pos
        if p.parent >= 0:
            m = np.asarray(bones[p.parent]['rest']) @ m
        bones.append(dict(id=p.no, parent=p.parent, attach=p.attach, translation=list(p.pos), rest=m.tolist(), capture=m.tolist()))
    return bones


def _gc_skeleton_any_order(mdl):
    # a section BIN with a partial skeleton (stage-3 soldier heads: 12 parts, attach ids 0-4 / 27-33) names its
    # parents by attach id (the body's part number), so parts are resolved by attach
    parts = {p.attach: p for p in mdl.parts}
    assert len(parts) == len(mdl.parts), 'GC section parts share an attach id'
    rest = {}

    def resolve(a, depth=0):
        if a in rest:
            return rest[a]
        assert depth <= len(parts) and a in parts, ('GC part parent not in the section', a)
        p = parts[a]
        m = np.eye(4)
        m[:3, 3] = p.pos
        if p.parent >= 0:
            m = resolve(p.parent, depth + 1) @ m
        rest[a] = m
        return m
    return [dict(id=p.no, parent=p.parent, attach=p.attach, translation=list(p.pos), rest=resolve(p.attach).tolist(),
                 capture=resolve(p.attach).tolist()) for p in mdl.parts]


def gc_mesh(bin_bytes):
    positions, pal, ws, norm, normpal, ds, dn, nc, uv, indices, batches, bindings, *_ = cc.parse_geometry(bin_bytes)
    weights = []
    for ids, pct in ws:
        rates, total = [], 0.0
        for k, b in enumerate(ids):
            f = pct[k] * .01 if k < len(ids) - 1 else 1 - total
            rates.append((b, f)); total += f
        weights.append(rates)
    tris = [[ds[j] for j in indices[k:k + 3]] for k in range(0, len(indices), 3)]
    nrm = [np.asarray(norm[dn[j]], float) for j in range(len(dn))]
    corner_normals = [[nrm[j] / (np.linalg.norm(nrm[j]) or 1) for j in indices[k:k + 3]] for k in range(0, len(indices), 3)]
    return dict(positions=np.asarray(positions, float), weights=[weights[p] for p in pal], triangles=np.asarray(tris, int),
                corner_normals=corner_normals, palettes=len(ws), normals=len(norm))


def gc_signature(d):
    """source_bindings.py's signature of a GC BIN: counts + FNV-1a of the first 64 bytes of the vertex
    array converted to little-endian s16 (what coarse_ganado_cast.cpp fingerprints on the loaded model)."""
    vo = struct.unpack_from('>I', d, 0x30)[0]
    raw = b''.join(struct.pack('<4h', *struct.unpack_from('>4h', d, vo + k)) for k in range(0, 64, 8))
    fnv = 2166136261
    for x in raw:
        fnv = ((fnv ^ x) * 16777619) & 0xffffffff
    mdl = modelbin.parse(d)
    return dict(part_bindings=[dict(id=p.no, parent=p.parent, attach=p.attach, translation=list(p.pos)) for p in mdl.parts],
                positions=struct.unpack_from('>H', d, 0x38)[0], normals=struct.unpack_from('>H', d, 0x3a)[0],
                palettes=d[0x18], parts=d[0x19], shift=d[0x28], flags=hex(struct.unpack_from('>I', d, 0x20)[0]),
                shape_offset=struct.unpack_from('>I', d, 0x2c)[0], source_vertex_fnv64_le=f'{fnv:08x}', bin_sha256=sha(d))


# ------------------------------------------------------------------------------------------ geometry checks


def closest_on_triangles(p, a, b, c):
    """closest points on triangles (a, b, c: (..., 3)) to points p (..., 3) (Ericson, vectorised)."""
    ab, ac, ap = b - a, c - a, p - a
    d1, d2 = (ab * ap).sum(-1), (ac * ap).sum(-1)
    bp = p - b
    d3, d4 = (ab * bp).sum(-1), (ac * bp).sum(-1)
    cp = p - c
    d5, d6 = (ab * cp).sum(-1), (ac * cp).sum(-1)
    va, vb, vc = d3 * d6 - d5 * d4, d5 * d2 - d1 * d6, d1 * d4 - d3 * d2
    den = np.where(np.abs(va + vb + vc) < 1e-20, 1e-20, va + vb + vc)
    v, w = vb / den, vc / den
    res = a + ab * v[..., None] + ac * w[..., None]
    with np.errstate(divide='ignore', invalid='ignore'):
        # edge regions
        cond = (vc <= 0) & (d1 >= 0) & (d3 <= 0)
        t = np.clip(np.nan_to_num(d1 / (d1 - d3)), 0, 1); res = np.where(cond[..., None], a + ab * t[..., None], res)
        cond = (vb <= 0) & (d2 >= 0) & (d6 <= 0)
        t = np.clip(np.nan_to_num(d2 / (d2 - d6)), 0, 1); res = np.where(cond[..., None], a + ac * t[..., None], res)
        cond = (va <= 0) & ((d4 - d3) >= 0) & ((d5 - d6) >= 0)
        t = np.clip(np.nan_to_num((d4 - d3) / ((d4 - d3) + (d5 - d6))), 0, 1); res = np.where(cond[..., None], b + (c - b) * t[..., None], res)
    # vertex regions
    res = np.where(((d1 <= 0) & (d2 <= 0))[..., None], a, res)
    res = np.where(((d3 >= 0) & (d4 <= d3))[..., None], b, res)
    res = np.where(((d6 >= 0) & (d5 <= d6))[..., None], c, res)
    return res


def surface_distance(points, verts, tris, cand=None, k=24):
    """distance from each point to the triangle mesh (verts, tris); cand = candidate triangle ids per point
    (default: the k nearest by centroid)."""
    A, B, C = verts[tris[:, 0]], verts[tris[:, 1]], verts[tris[:, 2]]
    if cand is None:
        cen = (A + B + C) / 3
        dd = ((points[:, None, :] - cen[None]) ** 2).sum(-1)
        cand = np.argsort(dd, axis=1)[:, :k]
    q = closest_on_triangles(points[:, None, :], A[cand], B[cand], C[cand])
    return np.sqrt(((q - points[:, None, :]) ** 2).sum(-1)).min(1), cand


def skin(verts, weights, mats):
    out = np.zeros_like(verts)
    h = np.c_[verts, np.ones(len(verts))]
    for i, w in enumerate(weights):
        m = sum(v * mats[b] for b, v in w)
        out[i] = (m @ h[i])[:3]
    return out


def winding_agreement(verts, tris, corner_normals):
    a, b, c = verts[tris[:, 0]], verts[tris[:, 1]], verts[tris[:, 2]]
    fn = np.cross(b - a, c - a)
    vn = np.asarray([sum(n) for n in corner_normals])
    s = (fn * vn).sum(1)
    return float((s > 0).mean())


# ------------------------------------------------------------------------------------------ convert


def gutter_texture(rgba, width, height, uv_bounds, wrap):
    """Extend source texels for unchanged raw UVs in an atlas (optional).

    GC wrap 0 clamps and wrap 1 repeats. A one-texel filtering margin plus
    the complete authored UV excursion keeps interpolation inside this image.
    Unsupported samplers fail rather than approximating their edge behavior.
    """
    if width <= 0 or height <= 0 or len(wrap) != 2 or any(w not in (0, 1) for w in wrap):
        raise ValueError('atlas gutters require positive dimensions and GX_CLAMP/GX_REPEAT')
    lo, hi = uv_bounds
    if len(lo) != 2 or len(hi) != 2 or any(not math.isfinite(x) for x in (*lo, *hi)) or any(a > b for a, b in zip(lo, hi)):
        raise ValueError('invalid atlas gutter UV bounds')
    left = max(1, math.ceil(-lo[0] * width / 256.0) + 1)
    top = max(1, math.ceil(-lo[1] * height / 256.0) + 1)
    right = max(1, math.ceil((hi[0] - 256) * width / 256.0) + 1)
    bottom = max(1, math.ceil((hi[1] - 256) * height / 256.0) + 1)
    if width + left + right > 2048 or height + top + bottom > 2048:
        raise ValueError('atlas gutter image exceeds 2048')
    image = np.frombuffer(rgba, dtype=np.uint8).reshape(height, width, 4)
    image = np.pad(image, ((top, bottom), (0, 0), (0, 0)), mode='wrap' if wrap[1] else 'edge')
    image = np.pad(image, ((0, 0), (left, right), (0, 0)), mode='wrap' if wrap[0] else 'edge')
    return image.tobytes(), (left, top, right, bottom)


def convert(preset, out, ps2_iso=PS2_ISO, gc_iso=GC_ISO, poses=None, bone_tol=0.001):
    spec = PRESETS[preset]
    if spec.get('converter'):
        raise SystemExit(f'{preset} is converted by {spec["converter"]}, not ps2_cast.py convert')
    out.mkdir(parents=True, exist_ok=True)
    ps2, gc, rec = inputs(spec['archive'], out, ps2_iso, gc_iso)
    ptd = load_module('ps2_tpl_decode', WA / 'from-main/ps2-trees/tools/ps2_tpl_decode.py')
    val = dict(preset=preset, inputs=rec, sections=[])
    # GC skeleton from the body BIN; every section (PS2 and GC) must carry the same one
    gbody = gc_entry(gc, spec['sections'][0][0], 'BIN')
    bones = gc_skeleton(gbody)
    assert all(b['attach'] == b['id'] for b in bones), 'GC body parts with attach != index'
    id_to_index = {b['attach']: b['id'] for b in bones}
    rest = np.asarray([b['rest'] for b in bones])
    # Texture atlas: every section keeps its own source TPL identity. Image
    # indices from different TPLs occupy distinct atlas slots. Single-TPL
    # presets retain their original indices, metadata, and output bytes.
    selections = section_specs(spec)
    tpl_arcs = list(dict.fromkeys(tpl_arc for _, _, tpl_arc in selections))
    images, tpl_bases, tpl_records = [], {}, []
    for tpl_arc in tpl_arcs:
        tpl = ps2_entry(ps2, tpl_arc, 'TPL')
        tp = ptd.parse_tpl(tpl)
        tpl_bases[tpl_arc] = len(images)
        tpl_records.append(dict(arc=hex(tpl_arc), bytes=len(tpl), sha256=sha(tpl)))
        for h in tp['entries']:
            w, ht, rgba, st = ptd.decode(tpl, h)
            images.append(dict(index=len(images), width=w, height=ht, rgba=bytes(rgba), format=ptd.describe(h)['format'],
                               alpha_raw=sorted(st['alpha_raw_hist'])))
    sections, used = [], []
    for si, (arc, role, tpl_arc) in enumerate(selections):
        assert spec['category'] != 'human' or role == ROLES[si]
        pbin = ps2_entry(ps2, arc, 'BIN')
        gbin = gc_entry(gc, arc, 'BIN')
        m = pb.parse_bin(pbin)
        gsk = gc_skeleton(gbin)
        # skeleton identity: PS2 (id, parent, translation) == GC (attach, parent, translation)
        if len(gsk) != len(bones):
            # a partial GC section skeleton (stage-3 soldier head / hands: the parts they weight, by attach id):
            # each part must be the body bone of its attach id (parent, translation; a section root has parent -1);
            # PS2 ids are attach ids too
            # (em11 type 7 hands: 41 parts on the 37-bone body, two hand roots repeated by attach id)
            assert spec.get('subset_bones'), (role, len(gsk), len(bones))
            by_attach = {}
            for g in gsk:
                by_attach.setdefault(g['attach'], g)
            for g in gsk:
                b = bones[id_to_index[g['attach']]]
                # a section root (parent -1) carries the body bone's rest position (model space)
                want = b['translation'] if g['parent'] >= 0 else [r[3] for r in b['rest'][:3]]
                assert g['parent'] in (b['parent'], -1) and max(abs(x - y) for x, y in zip(g['translation'], want)) <= bone_tol,                     (role, 'GC section part', g['id'], 'attach', g['attach'], 'differs from the body bone', g['translation'], want)
            if (spec.get('ps2_body_table_sections') and len(m.bones) >= len(gsk)
                    and not set(pb_['id'] for pb_ in m.bones) <= set(by_attach)):
                # lane cast16 (island soldier accessories 0x23D..0x245): the PS2 section carries the whole body bone
                # table while the GC section lists only the parts it uses. Bind it as a body-table section: PS2 bones
                # equal the body bones (checked below as a full skeleton), and every PS2-weighted bone must be a part
                # of the GC section (the runtime section has those parts).
                weighted = {b for _, cs in pb.triangles(m) for c in cs for b, v in c['w'] if v > 0}
                assert weighted <= set(by_attach), (role, 'PS2 weights outside the GC section parts', sorted(weighted - set(by_attach)))
                # the weighted PS2 bones are checked against the body bones of the same id (a PS2 body table may be
                # longer than this body's: em1e / em1f body 0x247 has 34 bones, the accessory tables 37)
                assert all(b < len(bones) for b in weighted), (role, 'PS2 weights beyond the body skeleton')
                pairs = [(pb_, bones[pb_['id']]) for pb_ in m.bones if pb_['id'] in weighted]
                id_parent = all((pb_['id'], pb_['parent']) == (b['attach'], b['parent']) for pb_, b in pairs)
                dt = max(max(abs(x - y) for x, y in zip(pb_['pos'], b['translation'])) for pb_, b in pairs)
                dt_body = 0.0
                val.setdefault('ps2_body_table_sections', []).append(role)
                assert id_parent and dt <= bone_tol, (role, id_parent, dt)
                gsk = bones  # the pairing below then runs on the body table
                m.bones = [pb_ for pb_ in m.bones if pb_['id'] < len(bones)]
            else:
                assert set(pb_['id'] for pb_ in m.bones) <= set(by_attach), (role, 'PS2 bones outside the GC section attach ids')
            # a PS2 bone takes the GC part of its id with the same parent (a repeated hand root: parent -1)
            cands = {}
            for g in gsk:
                cands.setdefault(g['attach'], []).append(g)
            pairs = [(pb_, dict(next((g for g in cands[pb_['id']] if g['parent'] == pb_['parent']), cands[pb_['id']][0]),
                                attach=pb_['id'])) for pb_ in m.bones]
            id_parent = all((pb_['id'], pb_['parent']) == (g['attach'], g['parent']) for pb_, g in pairs)
            dt = max(max(abs(x - y) for x, y in zip(pb_['pos'], g['translation'])) for pb_, g in pairs)
            dt_body = 0.0
        elif len(m.bones) == len(gsk):
            pairs = list(zip(m.bones, gsk))
        elif spec.get('ps2_superset_bones') and len(m.bones) > len(gsk):
            # lane cast16 (em2d type 4): the PS2 skeleton extends the GC one (91 vs 57 bones). The shared ids must be the
            # GC parts (parent, rest translation); a vertex weighted to a PS2-only bone fails below (id_to_index).
            pairs = [(pb_, gsk[pb_['id']]) for pb_ in m.bones if pb_['id'] < len(gsk)]
            val.setdefault('ps2_superset_bones', {})[role] = [len(m.bones), len(gsk)]
        else:
            # a reduced PS2 bone table (lane ps2cast-4: the crow's wing BINs carry only the bones they weight): each
            # PS2 bone is matched to the GC part of the same id (GC attach == index), parent and rest translation
            # checked per bone; weight ids are GC part ids either way
            assert spec.get('subset_bones') and len(m.bones) < len(gsk), (role, len(m.bones), len(gsk))
            pairs = [(pb_, gsk[pb_['id']]) for pb_ in m.bones]
        if len(gsk) == len(bones):
            id_parent = all((pb_['id'], pb_['parent']) == (g['attach'], g['parent']) for pb_, g in pairs)
            dt = max(max(abs(x - y) for x, y in zip(pb_['pos'], g['translation'])) for pb_, g in pairs)
            dt_body = max(max(abs(x - y) for x, y in zip(g['translation'], b['translation'])) for g, b in zip(gsk, bones))
        assert id_parent and dt <= bone_tol, (role, id_parent, dt)
        tris = pb.triangles(m)
        for mat in m.materials:
            image_index = tpl_bases[tpl_arc] + mat['diffuse']
            next_base = (tpl_bases[tpl_arcs[tpl_arcs.index(tpl_arc) + 1]]
                         if tpl_arcs.index(tpl_arc) + 1 < len(tpl_arcs) else len(images))
            assert tpl_bases[tpl_arc] <= image_index < next_base, (role, tpl_arc, mat['diffuse'])
            if image_index not in used:
                used.append(image_index)
        sections.append(dict(arc=arc, role=role, tpl=tpl_arc, image_base=tpl_bases[tpl_arc],
                             bin=m, tris=tris, gbin=gbin, gmesh=gc_mesh(gbin),
                             check=dict(arc=hex(arc), role=role, ps2_bin_bytes=len(pbin), ps2_bin_sha256=sha(pbin),
                                        gc_bin_bytes=len(gbin), gc_bin_sha256=sha(gbin), bones=len(m.bones),
                                        bone_id_parent_equal=id_parent, bone_translation_max_diff_mm=dt,
                                        gc_section_vs_body_translation_max_diff_mm=dt_body,
                                        ps2_materials=[dict(flag=x['flag'], diffuse=x['diffuse'], opacity=x['opacity']) for x in m.materials],
                                        ps2_triangles=len(tris), ps2_strip_vertices=sum(len(s['verts']) for n in m.nodes for s in n['segments']),
                                        ps2_segments=sum(len(n['segments']) for n in m.nodes))))
    used.sort()
    gutters = {}
    if spec.get('atlas_wrap_gutters'):
        if spec.get('repeat_uvs') or spec.get('uv_edge_texels'):
            raise ValueError('atlas_wrap_gutters preserves raw UVs; do not combine with UV transforms')
        bounds, wraps = {}, {}
        for s in sections:
            for material in s['bin'].materials:
                image = material['diffuse']
                k = s['image_base'] + image
                wrap = tpl_wrap_modes(gc_entry(gc, s['tpl'], 'TPL'), image)
                if k in wraps and wraps[k] != wrap:
                    raise ValueError('one atlas image has inconsistent source wrap modes')
                wraps[k] = wrap
                bounds.setdefault(k, ([0, 0], [256, 256]))
            for mat_i, corners in s['tris']:
                image = s['bin'].materials[mat_i]['diffuse']
                k = s['image_base'] + image
                lo, hi = bounds[k]
                for c in corners:
                    for axis, value in enumerate(c['raw']['uv']):
                        lo[axis] = min(lo[axis], value)
                        hi[axis] = max(hi[axis], value)
        for k in used:
            im = images[k]
            pixels, padding = gutter_texture(im['rgba'], im['width'], im['height'], bounds[k], wraps[k])
            gutters[k] = dict(rgba=pixels, padding=padding, wrap=wraps[k], uv_bounds=bounds[k])
        val['atlas_wrap_gutters'] = {str(k): {q: v for q, v in g.items() if q != 'rgba'} for k, g in gutters.items()}
    cells, (aw, ah) = pack_atlas([(k, images[k]['width'] + sum(gutters[k]['padding'][::2]),
                                 images[k]['height'] + sum(gutters[k]['padding'][1::2])) if k in gutters else
                                (k, images[k]['width'], images[k]['height']) for k in used])
    atlas = Image.new('RGBA', (aw, ah), (0, 0, 0, 255))
    for k in used:
        im = images[k]
        if k in gutters:
            x, y, w, h = cells[k]
            atlas.paste(Image.frombytes('RGBA', (w, h), gutters[k]['rgba']), (x, y))
            left, top, _, _ = gutters[k]['padding']
            cells[k] = (x + left, y + top, im['width'], im['height'])
        else:
            atlas.paste(Image.frombytes('RGBA', (im['width'], im['height']), im['rgba']), cells[k][:2])
    opaque = all(a >= 128 for im in images for a in im['alpha_raw'] if im['index'] in used)
    atlas_rgb = atlas.convert('RGB').convert('RGBA')  # opaque: PS2 alpha 0x80 = 1.0; RGB565 VQ has no alpha
    atlas_rgb.save(out / 'atlas.png')
    if not opaque:
        # Preserve authored PS2 partial alpha for the existing mask-run converter.
        atlas.save(out / 'atlas-rgba.png')
    val['texture'] = dict(tpl_arc=tpl_records[0]['arc'], tpl_bytes=tpl_records[0]['bytes'], tpl_sha256=tpl_records[0]['sha256'],
                          images=[{k: v for k, v in im.items() if k != 'rgba'} for im in images], used=used,
                          atlas=[aw, ah], cells={str(k): v for k, v in cells.items()}, opaque=opaque,
                          uv_rule='PS2 s16 / 256 (ps2_room_r4im.py: JADERLINK vt x 255/256), cell offset in the atlas')
    if len(tpl_records) > 1:
        val['texture']['tpls'] = tpl_records
        val['texture']['section_tpls'] = [hex(tpl_arc) for _, _, tpl_arc in selections]
        val['texture']['image_bases'] = {hex(arc): base for arc, base in tpl_bases.items()}
    # mesh json (PS2 geometry, GC bone indices)
    vert_index, positions, weights, triangles = {}, [], [], []
    zero_normals = 0
    for si, s in enumerate(sections):
        gm = s['gmesh']
        for mat_i, corners in s['tris']:
            cx, cy, cw, ch = cells[s['image_base'] + s['bin'].materials[mat_i]['diffuse']]
            raw_uvs = [c['raw']['uv'] for c in corners]
            if spec.get('repeat_uvs'):
                wrap = tpl_wrap_modes(gc_entry(gc, s['tpl'], 'TPL'), s['bin'].materials[mat_i]['diffuse'])
                normalized = repeat_triangle_uv(raw_uvs, wrap)
                if any(tuple(a) != tuple(b) for a, b in zip(raw_uvs, normalized)):
                    val['repeat_uv_triangles_shifted'] = val.get('repeat_uv_triangles_shifted', 0) + 1
                raw_uvs = normalized
            if spec.get('uv_edge_texels'):
                # lane ps2cast2: a PS2 corner up to uv_edge_texels texels outside its 256 image (the bat: 7 corners at
                # 257 on a GX_REPEAT image) is clamped to the image edge (counted); anything farther is refused.
                k = spec['uv_edge_texels']
                if any(not -k <= x <= 256 + k for uv in raw_uvs for x in uv):
                    raise ValueError('PS2 UV beyond uv_edge_texels')
                clamped = [[min(256, max(0, x)) for x in uv] for uv in raw_uvs]
                n = sum(tuple(a) != tuple(b) for a, b in zip(raw_uvs, clamped))
                if n:
                    val['uv_edge_corners_clamped'] = val.get('uv_edge_corners_clamped', 0) + n
                raw_uvs = clamped
            cs = []
            fa, fb, fc = (np.asarray(c['p']) for c in corners)
            face = np.cross(fb - fa, fc - fa)
            if not np.linalg.norm(face):  # a degenerate strip triangle draws nothing
                val['degenerate_triangles_dropped'] = val.get('degenerate_triangles_dropped', 0) + 1
                continue
            face = face / np.linalg.norm(face)
            for c, (raw_u, raw_v) in zip(corners, raw_uvs):
                if not any(c['n']):  # a zero PS2 normal: the face normal (winding as read)
                    c = dict(c, n=tuple(face)); zero_normals += 1
                if any(b not in id_to_index for b, v in c['w'] if v > 0):
                    raise ValueError(f'{s["role"]}: a PS2 vertex weighted to a bone the GC skeleton lacks')
                w = [(id_to_index[b], float(v)) for b, v in c['w'] if v > 0]
                if not w:
                    raise ValueError(f'{s["role"]}: an unweighted PS2 vertex')
                wk = tuple(sorted(w))
                key = (tuple(round(x, 5) for x in c['p']), wk)
                if key not in vert_index:
                    vert_index[key] = len(positions)
                    positions.append([float(x) for x in c['p']])
                    weights.append([[b, v] for b, v in w])
                u = (cx + raw_u * cw / 256.0) / aw  # PS2 UVs are normalised to the image (s16 / 256)
                v = (cy + raw_v * ch / 256.0) / ah
                assert 0 <= u <= 1 and 0 <= v <= 1
                cs.append(dict(vertex=vert_index[key], normal=[float(x) for x in c['n']], uv=[u, v]))
            triangles.append(dict(source_info=si, corners=cs))
    P = np.asarray(positions)
    val['zero_normals_replaced_by_face_normal'] = zero_normals
    # winding: the GC convention (face normal vs vertex normals) must hold for the PS2 triangles too
    flip = None
    for si, s in enumerate(sections):
        gm = s['gmesh']
        g_ok = winding_agreement(gm['positions'], gm['triangles'], gm['corner_normals'])
        ts = [t for t in triangles if t['source_info'] == si]
        pt = np.asarray([[c['vertex'] for c in t['corners']] for t in ts])
        p_ok = winding_agreement(P, pt, [[np.asarray(c['normal']) for c in t['corners']] for t in ts])
        s['check'].update(gc_winding_agreement=g_ok, ps2_winding_agreement_as_read=p_ok)
        want = g_ok > .5
        f = (p_ok > .5) != want
        assert flip in (None, f), 'sections disagree on the winding flip'
        flip = f
    if flip:
        for t in triangles:
            t['corners'] = t['corners'][::-1]
    val['winding_flipped'] = bool(flip)
    # source.json (GC side) + mesh.json
    infos = []
    for si, s in enumerate(sections):
        gm = s['gmesh']
        infos.append(dict(id=si, address=f'{spec["archive"]}:arc:{s["arc"]:03x}', source_data_address=f'{spec["archive"]}:arc:{s["arc"]:03x}',
                          source_bin_arc=s['arc'], source_tpl_arc=s['tpl'], source_sha256=sha(s['gbin']), role=s['role'],
                          gc_positions=len(gm['positions']), gc_normals=gm['normals'], gc_palettes=gm['palettes'],
                          gc_triangles=len(gm['triangles'])))
    source = dict(name=preset, schema='ps2cast-source-1', source_units='millimetres', source_archive=spec['archive'],
                  source_archive_sha256=rec['gc']['sha256'], ps2_archive_sha256=rec['ps2']['sha256'],
                  bones=[dict(id=b['id'], parent=b['parent'], address=f'{spec["archive"]}:part:{b["id"]}', rest=b['rest'], capture=b['capture'])
                         for b in bones], infos=infos, category=spec['category'], rooms=spec['rooms'], types=spec['types'])
    sp = out / 'source.json'
    sp.write_text(json.dumps(source))
    mesh = dict(schema='re4dc-approved-render-mesh-1', source_sha256=sha(sp.read_bytes()), mesh=preset.replace('-', '_') + '_ps2',
                positions_mm=positions, weights=weights, bones=source['bones'], triangles=triangles,
                policy='PS2 source geometry, normals, UVs (atlas cells) and skin weights, bound to the GC skeleton '
                       '(identical bone table); no reduction or refit.')
    mp = out / 'mesh.json'
    mp.write_text(json.dumps(mesh))
    # skin checks: weights, rest and posed surface distance to the GC mesh
    for si, s in enumerate(sections):
        gm = s['gmesh']
        ts = [t for t in triangles if t['source_info'] == si]
        vids = sorted({c['vertex'] for t in ts for c in t['corners']})
        pv = P[vids]
        d0, cand = surface_distance(pv, gm['positions'], gm['triangles'])
        # GC -> PS2 too (holes / missing parts show here)
        pt = np.asarray([[c['vertex'] for c in t['corners']] for t in ts])
        remap = {v: i for i, v in enumerate(vids)}
        ptl = np.vectorize(remap.get)(pt)
        g0, _ = surface_distance(gm['positions'], pv, ptl)
        ws = [weights[v] for v in vids]
        s['check'].update(
            ps2_unique_positions=len(vids), gc_positions=len(gm['positions']), gc_triangles=len(gm['triangles']),
            ps2_palettes=len({tuple(map(tuple, w)) for w in ws}), gc_palettes=gm['palettes'],
            max_influences=max(len(w) for w in ws), weight_sum_range=[min(sum(x for _, x in w) for w in ws), max(sum(x for _, x in w) for w in ws)],
            bones_used=sorted({b for w in ws for b, _ in w}),
            rest_ps2_to_gc_surface_mm=dict(median=float(np.median(d0)), p95=float(np.percentile(d0, 95)), max=float(d0.max())),
            rest_gc_to_ps2_surface_mm=dict(median=float(np.median(g0)), p95=float(np.percentile(g0, 95)), max=float(g0.max())))
        # normals vs the GC's at coincident positions (< 0.5 mm)
        angs = []
        for t in ts:
            for c in t['corners']:
                p = P[c['vertex']]
                dd = np.linalg.norm(gm['positions'] - p, axis=1)
                j = int(dd.argmin())
                if dd[j] < .5:
                    gn = [gm['corner_normals'][ti][k] for ti, tri in enumerate(gm['triangles']) for k in range(3) if tri[k] == j]
                    best = max(float(np.dot(c['normal'], n)) for n in gn)
                    angs.append(math.degrees(math.acos(max(-1, min(1, best)))))
        if angs:
            s['check']['normal_angle_vs_gc_deg_at_shared_positions'] = dict(n=len(angs), median=float(np.median(angs)), p95=float(np.percentile(angs, 95)))
        S = json.loads(Path(poses).read_text())['samples'] if poses else None
        if S and len(S[0]['world']) != len(bones):
            s['check']['posed_ps2_to_gc_surface_mm'] = f'skipped: the pose file has {len(S[0]["world"])} bones, the model {len(bones)}'
        elif S:
            worst = []
            for k, smp in enumerate(S[::4]):
                mats = np.asarray(smp['world']) @ np.linalg.inv(rest)
                pp = skin(pv, ws, mats)
                gp = skin(gm['positions'], gm['weights'], mats)
                dk, _ = surface_distance(pp, gp, gm['triangles'], cand)
                worst.append((float(np.percentile(dk, 95)), float(dk.max())))
            s['check']['posed_ps2_to_gc_surface_mm'] = dict(poses=len(worst), source=str(poses),
                                                          p95_max=max(w[0] for w in worst), max=max(w[1] for w in worst),
                                                          p95_median=float(np.median([w[0] for w in worst])))
    val['sections'] = [s['check'] for s in sections]
    # pack (the cast's packer, unchanged) + host fixture
    pk = load_module('pack_coarse_actor', PROTO / 'tools/pack_coarse_actor.py')
    native = out / 'native'
    if native.exists():
        shutil.rmtree(native)
    # The packer stores positions as s16 at 1/16 mm (+-2048 mm). A larger model (spec 'shift', the GC BIN's own
    # position shift: El Gigante 2) packs positions / 2^(4 - shift) (normals, weights and binds unchanged) and its
    # registry descriptor carries the shift (NATIVE_MODEL_REGISTRY_SHIFT); mesh.json keeps millimetres.
    shift = spec.get('shift', 4)
    val['position_shift'] = shift
    # flat_normals (PS2CAST_FLAT_NORMALS=1, Ganado cast bundles only): every packed corner normal is one constant
    # vector, so each chunk keeps a single normal and records merge on (position, uv). The cast Ganados draw unlit in
    # the play recipe (ACTOR_GANADO_SOURCE_LIGHT=0: a constant-colour SourceLighting, normals never read), so the image
    # is unchanged while the static data shrinks (the s30 heap-4 gate). A lit-Ganado image needs the normal bundle.
    flat = os.environ.get('PS2CAST_FLAT_NORMALS') == '1'
    val['flat_normals'] = flat
    # lane ps2cast-4: the registry animals (dog, cow, chicken) draw flat too (the constant actor light, as today's cast
    # animals); a preset marked lit (em22: the source lighting record) keeps its normals
    if flat and (spec['category'] not in ('human', 'animal') or spec.get('lit')):
        raise ValueError('PS2CAST_FLAT_NORMALS is for the unlit Ganado cast and the flat registry animals only')
    if shift != 4 or flat:
        pm = dict(mesh)
        if shift != 4:
            pm['positions_mm'] = [[x / (1 << (4 - shift)) for x in p] for p in positions]
            pm['policy'] += f' Positions / {1 << (4 - shift)} for the s16 range (drawn at shift {shift}).'
        if flat:
            pm['triangles'] = [dict(t, corners=[dict(c, normal=[0.0, 1.0, 0.0]) for c in t['corners']]) for t in triangles]
            pm['policy'] += ' Normals flattened to one constant vector (unlit cast; PS2CAST_FLAT_NORMALS=1).'
        mpk = out / 'mesh-pack.json'
        mpk.write_text(json.dumps(pm))
        mp = mpk
    pk.pack(mp, sp, native, 'castmodel')
    host_fixture(native, source)
    report = json.loads((native / 'native-report.json').read_text())
    val['native'] = {k: v for k, v in report.items() if k != 'chunks'}
    val['native']['chunks'] = [{k: v for k, v in c.items() if k != 'palette_weights'} for c in report['chunks']]
    # cast layout files (GC signatures; texture key from the atlas identity)
    binds = []
    for s in sections:
        binds.append(dict(bin=s['arc'], tpl=s['tpl'], role=s['role'], **gc_signature(s['gbin']),
                          binding_scope='GC source array signature (the loaded model the PS2 mesh replaces)'))
    (out / 'source-bindings.json').write_text(json.dumps(binds, indent=2))
    key = texture_key(out / 'atlas.png')
    val['texture'].update(key=key)
    (out / 'validation.json').write_text(json.dumps(val, indent=1))
    print(json.dumps(dict(preset=preset, triangles=report['triangles'], winding_flipped=val['winding_flipped'], key=key,
                          sections=[{k: s[k] for k in ('role', 'ps2_triangles', 'gc_triangles', 'ps2_palettes', 'gc_palettes',
                                                       'rest_ps2_to_gc_surface_mm', 'rest_gc_to_ps2_surface_mm',
                                                       'posed_ps2_to_gc_surface_mm', 'normal_angle_vs_gc_deg_at_shared_positions',
                                                       'gc_winding_agreement', 'ps2_winding_agreement_as_read') if k in s}
                                    for s in val['sections']]), indent=1))


def pack_atlas(items):
    """Guillotine packing of power-of-two images (k, w, h) into the smallest power-of-two atlas (square or 2:1
    wide) that holds them, largest first, deterministic. -> ({k: (x, y, w, h)}, (atlas w, atlas h))."""
    area = sum(w * h for _, w, h in items)
    side = max(max(w for _, w, _ in items), max(h for _, _, h in items))
    side = 1 << (side - 1).bit_length()  # optional gutters need not have power-of-two dimensions
    cands = []
    # from side / 2 (lane ps2cast-4): a single wide image (em22's 512 x 256 TPL) takes a 2:1 atlas of its own size
    # instead of a square one twice as large (a too small candidate simply fails to pack)
    s = max(side // 2, 8)
    while s <= 2048:
        cands += [(s, s), (2 * s, s)]
        s *= 2
    for aw, ah in sorted(set(cands), key=lambda c: (c[0] * c[1], c[0])):
        if aw * ah < area or aw > 2048:
            continue
        free, out, ok = [(0, 0, aw, ah)], {}, True
        for k, w, h in sorted(items, key=lambda t: (-t[1] * t[2], -t[1], t[0])):
            fit = [f for f in free if f[2] >= w and f[3] >= h]
            if not fit:
                ok = False
                break
            f = min(fit, key=lambda f: (f[2] * f[3], f[1], f[0]))
            free.remove(f)
            out[k] = (f[0], f[1], w, h)
            if f[2] > w:
                free.append((f[0] + w, f[1], f[2] - w, h))
            if f[3] > h:
                free.append((f[0], f[1] + h, f[2], f[3] - h))
        if ok:
            return out, (aw, ah)
    raise ValueError('atlas does not fit 2048')


def host_fixture(n, source):
    """prepare_dynamic_native_check.py's host-fixture.bin (the cast agent's check-dynamic input)."""
    rest = np.asarray([b['rest'] for b in source['bones']]); cap = np.asarray([b['capture'] for b in source['bones']])
    sk = cap @ np.linalg.inv(rest); sk[:, :3, 3] += rest[0, :3, 3] - cap[0, :3, 3]
    r = json.loads((n / 'native-report.json').read_text())
    buf = bytearray(struct.pack('<I', len(r['chunks'])))
    for c in r['chunks']:
        i = c['info']
        parts = [(n / f'info{i}.{ext}').read_bytes() for ext in ['pos', 'nrm', 'uv', 'gx']]
        poses = np.asarray([sum(w * sk[b] for b, w in ws)[:3, :4].T.flatten() for ws in c['palette_weights']], dtype='<f4').tobytes()
        buf.extend(struct.pack('<10I', i, c['positions'], c['normals'], c['palettes'], c['triangles'], *[len(x) for x in parts], len(poses)))
        for p in parts + [poses]:
            buf.extend(p)
    (n / 'host-fixture.bin').write_bytes(buf)


def texture_key(png):
    """package_coarse_texture.py's identity: CRC32 / FNV-1a of the image as GX RGBA8 (format 6) tiles."""
    image = Image.open(png).convert('RGBA'); w, h = image.size
    px = np.asarray(image, dtype=np.uint8)
    enc = bytearray()
    for y in range(0, h, 4):
        for x in range(0, w, 4):
            blk = px[y:y + 4, x:x + 4].reshape(16, 4)
            enc.extend(bytes(np.stack([blk[:, 3], blk[:, 0]], 1).reshape(-1)))
            enc.extend(bytes(np.stack([blk[:, 1], blk[:, 2]], 1).reshape(-1)))
    ident = struct.pack('<5I', w, h, 6, 0xffffffff, 0) + bytes(enc)
    crc = zlib.crc32(ident) & 0xffffffff
    fnv = 2166136261
    for b in ident:
        fnv = ((fnv ^ b) * 16777619) & 0xffffffff
    return f'{crc:08x}-{fnv:08x}'


# ------------------------------------------------------------------------------------------ finish / castdir


def blob_stats(header):
    cb = load_module('cast_bundle', os.environ.get('RE4_CAST_BUNDLE', '//wsl.localhost/Ubuntu-24.04/root/probe/d367-agents/coarse-actors-4k/tools/cast_bundle.py'))
    # cast_bundle.py is fixed at the Ganado's 34 bones; the stats themselves are bone-count independent
    cb.BONES = int(re.search(r'bone_count=(\d+);', Path(header).read_text()).group(1))
    chunks, arrays, weights, blobs = cb.parse_header(str(header), 0)
    return cb.blob_stats(blobs, arrays, chunks), cb.skin_stream_bytes(weights, [c[3] for c in chunks], str(header))


def finish(out):
    """after ps2_cast_native.sh: manifest.json with the runtime header's counts (cast manifest keys)."""
    val = json.loads((out / 'validation.json').read_text())
    hdr = out / 'runtime' / 'castmodel_runtime.h'
    s, skin_bytes = blob_stats(hdr)
    tex = json.loads((out / 'texture' / 'package.json').read_text())
    preset = val['preset']
    spec = PRESETS[preset]
    level = dict(runtime_header='runtime/castmodel_runtime.h', header_sha256=sha(hdr.read_bytes()), triangles=s['triangles'],
                 transformed_records=s['records'], records_per_triangle=s['records'] / s['triangles'],
                 strip_vertices=s['corners'], strip_vertices_per_triangle=s['corners'] / s['triangles'], palettes=s['palettes'],
                 palette_runs=s['palette_runs'], meshlets=s['meshlets'], skin_stream_bytes=skin_bytes)
    man = dict(name=preset, revision='ps2-v1', source=dict(name=preset, archive=spec['archive'], rooms=spec['rooms'], types=spec['types'],
               sections=[dict(bin=a, tpl=t, role=r) for a, r, t in section_specs(spec)]),
               status='PS2 conversion; needs user look review', bones=val['sections'][0]['bones'], sections=len(val['sections']),
               source_palette_sum=sum(x['gc_palettes'] for x in val['sections']),
               ps2_palette_sum=sum(x['ps2_palettes'] for x in val['sections']),
               levels=dict(conservative=level, lean=level),
               texture_package=dict(package='texture/' + tex['key'] + '.re4tex', package_sha256=tex['package_sha256'], key=tex['key'],
                                    width=tex['width'], height=tex['height'], format=tex['format'], vram_bytes=tex['vram_bytes']))
    (out / 'manifest.json').write_text(json.dumps(man, indent=1))
    print(json.dumps(level, indent=1))


def castdir(cast, outs, hand_arcs=range(0x1c0, 0x1c9)):
    """A cast dir for cast_bundle.py: <cast>/<name>/{manifest,source-bindings,source}.json + header + texture,
    source/candidate-revisions.json, and em<archive>-hand-<i>/source-bindings.json (GC hand-pose signatures)."""
    cast.mkdir(parents=True, exist_ok=True)
    (cast / 'source').mkdir(exist_ok=True)
    revs = {}
    archives = set()
    for o in outs:
        man = json.loads((o / 'manifest.json').read_text())
        name = man['name']
        d = cast / name
        if d.exists():
            shutil.rmtree(d)
        d.mkdir()
        for f in ('source-bindings.json', 'validation.json'):
            shutil.copy2(o / f, d / f)
        # cast_bundle.py resolves manifest paths against the cast root
        m2 = json.loads(json.dumps(man))
        for L in m2['levels'].values():
            L['runtime_header'] = f'{name}/{L["runtime_header"]}'
        m2['texture_package']['package'] = f'{name}/{man["texture_package"]["package"]}'
        (d / 'manifest.json').write_text(json.dumps(m2, indent=1))
        src = json.loads((o / 'source.json').read_text())
        (d / 'source.json').write_text(json.dumps(dict(src, bones=[dict(b) for b in src['bones']])))
        (d / 'runtime').mkdir()
        shutil.copy2(o / 'runtime' / 'castmodel_runtime.h', d / 'runtime' / 'castmodel_runtime.h')
        (d / 'texture').mkdir()
        shutil.copy2(o / man['texture_package']['package'], d / man['texture_package']['package'])
        revs[name] = dict(revision=man['revision'], reason='PS2 conversion (ps2_cast.py)')
        archives.add((man['source']['archive'], o))
    (cast / 'source' / 'candidate-revisions.json').write_text(json.dumps(revs, indent=1))
    for archive, o in sorted(archives):
        gin = json.loads((o / 'validation.json').read_text())['inputs']['gc']
        gd = Path(gin['cache']).read_bytes()
        assert sha(gd) == gin['sha256'], 'GC archive cache changed'
        gc = drs.Drs(gd)
        for i, arc in enumerate(hand_arcs):
            d = cast / f'{archive}-hand-{i}'
            d.mkdir(exist_ok=True)
            b = gc_entry(gc, arc, 'BIN')
            (d / 'source-bindings.json').write_text(json.dumps([dict(bin=arc, role='hand-pose', **gc_signature(b))], indent=1))
    print('cast dir', cast, sorted(revs))


def to_wsl(p):
    s = str(p).replace('\\', '/')
    m = re.match(r'^//wsl\.localhost/[^/]+(/.*)$', s)
    if m:
        return m.group(1)
    m = re.match(r'^([A-Za-z]):(/.*)$', s)
    return f'/mnt/{m.group(1).lower()}{m.group(2)}' if m else s


def regcast(cast, overlay, outs):
    """A cast dir in the external cast's registry layout for tools/d367/model_registry.py (NATIVE_MODEL_REGISTRY):
    <cast>/<overlay>/integration-bundle/catalog.json, <cast>/<name>/{manifest,source,source-bindings}.json,
    <cast>/<name>/ps2-v1/{revision-manifest.json, header, texture}, <cast>/source/{candidate-revisions,
    archive-audit}.json. Paths inside are WSL paths (the generator runs in WSL). One atlas per model: every chunk
    (source_info) binds the same package. em12 joins archive-audit.json for the generator's self-check."""
    cast.mkdir(parents=True, exist_ok=True)
    (cast / 'source').mkdir(exist_ok=True)
    ib = cast / overlay / 'integration-bundle'
    ib.mkdir(parents=True, exist_ok=True)
    base_audit = json.loads((PRIV / 'cast-20260925' / 'source' / 'archive-audit.json').read_text())
    audit = {'em12': {k: base_audit['em12'][k] for k in ('source', 'sha256')}}
    catalog, revs = [], {}
    for o in outs:
        man = json.loads((o / 'manifest.json').read_text())
        val = json.loads((o / 'validation.json').read_text())
        name, preset = man['name'], val['preset']
        spec = PRESETS[preset]
        d = cast / name
        if d.exists():
            shutil.rmtree(d)
        (d / 'ps2-v1' / 'texture').mkdir(parents=True)
        hdr = d / 'ps2-v1' / 'castmodel_runtime.h'
        shutil.copy2(o / 'runtime' / 'castmodel_runtime.h', hdr)
        tp = man['texture_package']
        pkg = d / 'ps2-v1' / 'texture' / Path(tp['package']).name
        shutil.copy2(o / tp['package'], pkg)
        fmt = 'VQ RGB565' if 'VQ' in tp['format'] else tp['format']
        tex = dict(key=tp['key'], package=to_wsl(pkg), package_sha256=tp['package_sha256'], format=fmt,
                   rectangle=[0, 0, tp['width'], tp['height']], vram_bytes=tp['vram_bytes'])
        level = dict(runtime_header=f'{name}/ps2-v1/castmodel_runtime.h', header_sha256=sha(hdr.read_bytes()))
        packages = {str(i): tex for i in range(man['sections'])}
        entry = dict(name=name, revision='ps2-v1', previous_revision=None, rooms=spec['rooms'], category=spec['category'],
                     levels=dict(conservative=level), texture_packages=packages, position_shift=val.get('position_shift', 4),
                     status='PS2 conversion (ps2_cast.py); render-only replacement of the GC source mesh')
        catalog.append(entry)
        (d / 'ps2-v1' / 'revision-manifest.json').write_text(json.dumps(dict(entry, levels=dict(conservative=level)), indent=1))
        (d / 'manifest.json').write_text(json.dumps(dict(name=name, revision='ps2-v1'), indent=1))
        shutil.copy2(o / 'source-bindings.json', d / 'source-bindings.json')
        src = json.loads((o / 'source.json').read_text())
        src['source_model_id'] = spec['model_id']
        (d / 'source.json').write_text(json.dumps(src))
        gin = val['inputs']['gc']
        assert sha(Path(gin['cache']).read_bytes()) == gin['sha256'], 'GC archive cache changed'
        audit[spec['archive']] = dict(source=to_wsl(gin['cache']), sha256=gin['sha256'])
        revs[name] = dict(revision='ps2-v1', reason='PS2 conversion (ps2_cast.py)')
    (ib / 'catalog.json').write_text(json.dumps(catalog, indent=1))
    (cast / 'source' / 'candidate-revisions.json').write_text(json.dumps(revs, indent=1))
    (cast / 'source' / 'archive-audit.json').write_text(json.dumps(audit, indent=1))
    print('registry cast dir', cast, sorted(revs))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest='cmd', required=True)
    c = sp.add_parser('convert'); c.add_argument('preset', choices=sorted(PRESETS)); c.add_argument('out', type=Path)
    c.add_argument('--ps2-iso', default=PS2_ISO); c.add_argument('--gc-iso', default=GC_ISO); c.add_argument('--poses')
    c.add_argument('--bone-tol', type=float, default=0.001)
    f = sp.add_parser('finish'); f.add_argument('out', type=Path)
    d = sp.add_parser('castdir'); d.add_argument('cast', type=Path); d.add_argument('outs', type=Path, nargs='+')
    r = sp.add_parser('regcast'); r.add_argument('cast', type=Path); r.add_argument('overlay'); r.add_argument('outs', type=Path, nargs='+')
    sp.add_parser('list')
    a = ap.parse_args()
    if a.cmd == 'convert':
        convert(a.preset, a.out, a.ps2_iso, a.gc_iso, a.poses, a.bone_tol)
    elif a.cmd == 'finish':
        finish(a.out)
    elif a.cmd == 'castdir':
        castdir(a.cast, a.outs)
    elif a.cmd == 'regcast':
        regcast(a.cast, a.overlay, a.outs)
    else:
        for k, v in sorted(PRESETS.items()):
            print(k, v['archive'], [(hex(x), r) for x, r in v['sections']], 'tpl', hex(v['tpl']), v['rooms'])


if __name__ == '__main__':
    main()
