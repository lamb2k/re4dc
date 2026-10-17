#!/usr/bin/env python3
"""Selectable em12 key residency via existing qualified source/FCV transport.

All FCV headers/joint identities, SEQ event tables, EFF behavior, meshes and ordinal
slots stay resident. Native key files are exact existing little-endian codec
output, consumed only through bounded source-motion evaluation leases. No clip
is removed because it was absent from a replay; original DRS remains untouched.
Optional upload-only textures use the existing NTR/shared native package path;
palettes, mip chains and unreviewed embedded EFM textures stay resident.
pl00/wep02 also support textures-only preparation, retaining every motion.
"""
from pathlib import Path
import argparse, hashlib, json, struct, tempfile, zlib
import le_mirror as mirror
import compact_effect_records as effects
from prepare_native_ui import compact_spans, select_upload_only, native_identity_index

MAGIC=b'R4MOTBL\0'
STRIDE=20
MAX_CLIP=32768
# Ganado modules link the shared em10.cpp (config/G4BE08/modules.py): same EFF slot0
# family, FCV/SEQ transport and source motion evaluators as em12 (frontier W1).
# em13 (r104's chapter 1-2 Ganados; native scene lane 2026-10-03): the same three units as em12/em15
# (config/G4BE08/modules.py: em13/em10.cpp, em10_tmpl.cpp, em13_set.cpp), so the same consumers. Its GC
# archive's 4,367,968 B body did not fit r104's heap 4 (DVD: Memory allocate failed, EmSetFromList2 Id=13).
# em17 (r108's chapter 1-3 Ganados, route lane c13): em17/em10.cpp, em10_tmpl.cpp, em17_set.cpp, the same three
# units; its GC archive did not fit r108's heap 4 next to the room and its PS2 world (route-c13-r102c).
# em11 (r117's later-visit Ganados, ESL 0x50/0x51, chapter 2-1; route lane r117 2026-10-10): em11/em10.cpp,
# em10_tmpl.cpp, em11_set.cpp, the same three units; its 5.8 MB GC archive did not fit r117's heap 4 (largest cell
# 3.1 MB: DVD: Memory allocate failed, readEmData em/em11.drs).
# em1d / em1e / em1f (ROUTE_CH3, the island soldiers and Ganados of r300 / r301 r303 r305; stage 3 lane 2026-10-14): em1d/em10.cpp,
# em10_tmpl.cpp, em1d_set.cpp (em1e the same), the em11 contract. Their GC archives (4,634,272 / 4,502,752 B bodies)
# did not fit r300's heap 4 on the disc-2 image (4,042,976 B free: DVD: Memory allocate failed, Em set failed Id=1d).
# em16 (r11d's chapter 2-3 night-village Ganados and the Bella sisters, chainsaw types 3 / 4; lane ch2code16 2026-10-16):
# em16/em10.cpp, em10_tmpl.cpp, em16_set.cpp, the same three units (ROUTE_CH23 links it in the em10g group); its 4,246,528 B
# GC body never fit r11d's heap 4 next to the room, Ashley and em3b (CH22-ROUTE-20261014 blocker 1).
# em1a / em1b / em14 (castle chapter 3 Ganados, ROUTE_CH31; castle lane 2026-10-15): em1x/em10.cpp, em10_tmpl.cpp,
# em1x_set.cpp, the em10g group's units, so the same consumers; their GC archives (3.9-4.3 MB bodies) did not fit heap 4
# in r208 / r201 / r204 next to the room and its PS2 world (cx-r20x-t12-01: readEmData error).
# em19 (r20d Ganados, ROUTE_CH32; same em10.cpp / em10_tmpl.cpp / em19_set.cpp units, 4,293,760 B GC body).
# em1c (r218 Ganados, ROUTE_CH41; em10.cpp / em10_tmpl.cpp / em1c_set.cpp, 4,988,480 B GC body).
GANADO=('em12.drs','em15.drs','em13.drs','em17.drs','em11.drs','em16.drs','em1a.drs','em1b.drs','em14.drs','em19.drs','em1c.drs',
        'em1d.drs','em1e.drs','em1f.drs')
SMALL=('em26.drs','em28.drs','em21.drs','em2b.drs','em2f.drs','em22.drs','em23.drs','em18.drs','pl11.drs','pl0f.drs')
# em2a / em24 / em27 / em29 / em2e (the chapter 1 traps, snake, fish, bat and wall crawler; lane ps2cast 2026-10-15,
# registry room packages of the released chapter 1-1..2-1 rooms): textures only (--keep-motion-resident). Each module's
# model TPL reaches only modelInit (src/em2a/em2a.cpp ARC 5 / 7 / 9, em24 ARC 6, em27 ARC 5, em29 ARC 5, em2e ARC 5 / 6);
# none uploads or reads texels on the CPU, so the prepared R4NREF descriptors replace exactly what the source path draws.
SMALL+=('em2a.drs','em24.drs','em27.drs','em29.drs','em2e.drs')
# em2c (Verdugo, r221) / em38 (Salazar + the Queen, r228) (lane ch3found16 2026-10-16, ROUTE_BOSS4 stress test): textures
# only (--keep-motion-resident). em2c's model TPL (ARC 6) reaches only modelInit (Em2c R0 init: modelInit(ARC 5 / 0x86,
# ARC 6)); its ice blend is a TexRender target (em2cTexrenderInit), not TPL texels. em38's model TPL (ARC 8) and ARC 0xA
# reach only modelInit and ModInfoMgr.create (em38 R0 init, the pl11 pattern). Their EFF slots (em2c ARC 4, em38 ARC
# 0xB, EspDataLoad) keep their own textures (top-level TPLs only are selected). Motions stay resident: both modules keep
# raw FCV pointers (em2c w->blendM0.., em38 w->mot[]), so motion streaming needs its own consumer audit.
SMALL+=('em2c.drs','em38.drs')
# em2d (Novistadors, r205 / r20a, ROUTE_CH32 room overlay; lane ch3found16 2026-10-16): textures only. Its model TPL reaches
# only modelInit (em2d R0 init, modelInit(bin, tpl)); its EFF slot (ARC 4, EspDataLoad) keeps its own textures. The GC
# body (3,700,672 B) did not fit r205's heap 4 (largest 2,334,560 B, cx-r205-h1-01 Flycast).
SMALL+=('em2d.drs',)
# Island enemies (lane ch5found16 2026-10-16, ROUTE_CH3 room overlays): textures only (--keep-motion-resident), the em2d
# contract. Their model TPLs reach only modelInit / ModInfoMgr.create / SetObj16 (src/em36/em36.cpp em36 R0 init ARC 0x13
# 0x14 0x24, the tentacle SetObj16 ARC 0x8E / 0x8F; src/em39/em39.cpp ARC 0x17 0x10 0x18 0x12 0x1D 0x1E 0x22 and the
# knife-fight hand on Leon's subArc; src/em3a/em3a.cpp ARC 6 / 0xC; src/em32/em32.cpp ARC 5; src/em3d/em3d.cpp ARC 6);
# the source path uploads their colour texels and never reads them on the CPU. Their EFF slots (EspDataLoad: em36 ARC
# 0x25, em3a ARC 4, em32 ARC 8, em3d ARC 4) keep their own textures (top-level TPLs only are selected). Motions stay
# resident: their FCV consumers are not audited for motion streaming.
SMALL+=('em36.drs','em39.drs','em3a.drs','em32.drs','em3d.drs')
# em31 (Saddler's final form, r332; lane stress16b 2026-10-16, the model-only stress disc STRESS_SADDLER): textures only
# (--keep-motion-resident). Its model TPL (ARC 7) reaches only modelInit and ModInfoMgr.create (src/em31/em31.cpp
# em31_R0_Init: body ARC 4 + head ARC 5, tentacle ARC 8); its EFF slot (ARC 9, EspDataLoad) keeps its own textures (top-level
# TPLs only are selected). Motions stay resident (the em2c / em38 boss rule: raw FCV pointers are not audited).
SMALL+=('em31.drs',)
# pl0f (the lake boat, r10b r11b; lane ps2cast 2026-10-15, PS2_CAST_BOAT discs): textures only (--keep-motion-resident),
# the em2f contract. Its one model TPL (ARC 6) reaches only modelInit (src/pl0f/pl0f.cpp pl0f_R0_Init, modelInit(ARC 5,
# ARC 6)); the source path uploads its colour texels and never reads them on the CPU. ARC 8 (Leon's harpoon hand BIN,
# cPlBody::initWepHand) and ARC 7 are BINs (unchanged). Its EFF slot (ARC 4, EspDataLoad) keeps its own textures
# (top-level TPLs only are selected). The registry owner path proves its texture rows only on a texture-prepared archive.
# pl11 (Ashley, cSubAshley; r117 first; lane ps2cast 2026-10-14, PS2_ASHLEY discs): textures only
# (--keep-motion-resident), the em18 contract. Her model TPLs (ARC 5 body / extras / hands, ARC 8 hair, ARC 0xB head)
# reach only modelInit and ModInfoMgr.create (src/pl11/pl11.cpp cSubAshley::modelSet / setHand); the source path
# uploads their colour texels and never reads them on the CPU. Her EFF slot (ARC 0x11, EspDataLoad group 4) keeps its
# own textures (top-level TPLs only are selected). Codex's bounded 'pl11-r11f' profile below audits the same TPLs.
# em18 (the merchant, r102 r10d r10e r112; lane ps2cast2 2026-10-14, PS2_CAST_MERCHANT discs): textures only
# (--keep-motion-resident), the em22 contract. Its model TPLs (ARC 6 body / hands / goods, ARC 8 head, ARC 0xF robe and
# coat) reach only modelInit and ModInfoMgr.create (src/em18/em18.cpp em18_R0_Init, em18ClothPartsSet, the goods and hand
# infos); the source path uploads their colour texels and never reads them on the CPU. Its EFF slot (ARC 4,
# EspDataLoad) keeps its own textures (top-level TPLs only are selected). The registry owner path proves its texture
# rows only on a texture-prepared archive (R4NREF descriptors).
# em2f (Del Lago, r10b; lane ps2cast-2 2026-10-10, PS2_DELLAGO discs): textures only (--keep-motion-resident). Its
# model TPLs (ARC 5 type 0, ARC 7 type 1) reach only modelInit (src/em2f/em2f.cpp em2f_R0_Init); the source path
# uploads their colour texels (materialSetup -> re4dc_model_material) and never reads them on the CPU. The bump map
# (an IA8 image, bound only by bumpSetup to the GX stubs) is not a native format and stays resident. Its EFF slot
# (ARC 8, EspDataLoad) keeps its own textures (top-level TPLs only are selected). em2f is a ROUTE_OVL room overlay.
# em22 (parasite dog, r11b r118; lane ps2cast-4 2026-10-11, PS2_WOLF discs): textures only (--keep-motion-resident), the
# em2f contract. Its body TPL (ARC 5) reaches only modelInit (src/em22/em22.cpp em22_R0_Init); the back parasites'
# TPLs (ARC 0x3A / 0x48) only SetObj16 (cObj16 model textures, as em2b's parasite); the source path uploads their
# colour texels and never reads them on the CPU. Its EFF slot (ARC 6, EspDataLoad) keeps its own textures (top-level
# TPLs only are selected). The registry owner path proves its texture rows only on a texture-prepared archive.
# em23 (crows, r100 r105 r108 r109; Phase 2 A3 2026-10-11, PS2_CROW discs): its textures too (with its motion contract
# below, as em21). The model TPL (ARC 8) reaches only modelInit (src/em23/em23.cpp em23_R0_Init, modelInit(ARC 5, ARC 8))
# and em23SetWing's wing info (ARC 6 / 7 with ARC 8); the source path uploads its colour texels and never reads them on
# the CPU. Its EFF slot (ARC 4, EspDataLoad) keeps its own textures (top-level TPLs only are selected).
# Small enemies whose motions also leave the body: em21 (r100 trap dog) plays every clip through
# MotionSetCore/MotionMove (src/em21/em21.cpp; ARC() otherwise only feeds modelInit), the leased
# evaluators in motion.cpp. Needed for heap 4 in r100's post-house ambush (em21 + em23 + em2a).
# em23 (crows) passes its ARC motions only to MotionSetCore; em2a (traps) also reads a clip's
# frame count from the FCV header (*(u16*)ARC(0xB)), which stays resident, and lends its subArc
# to the player's trap motions (same leased evaluator). Their textures are not audited: motion only.
MOTION_SMALL=('em21.drs','em23.drs','em2a.drs','em2b.drs')
# Motion streaming for room-overlay enemies whose resident body does not fit their rooms' heap 4 (lane ch5found16
# 2026-10-16; generic: an enemy joins with an audit comment here, a hot set from tools/d367/motion/motion_hot.py and the
# prepare call in tools/d367/motion/README.txt). Every streamed entry is an FCV; SEQ key tables, PTH paths, BINs, TPLs,
# EFF and FCV headers stay resident (prepare() retains them), so only MotionSetCore's `data` argument can be cold.
# em36 (regenerator / iron maiden, r306..r310 r326; ARC(n) = archive slot n-4): every FCV it names goes to MotionSetCore:
# directly (em36.cpp, 86 calls), through the m0 / m1 pairs of its act table (em36.cpp 2879-2938: m0 = ARC(0x4A 0x4B 0x4C
# 0x4E 0x58 0x59 0x5B 0x5C), all FCV; m1 = ARC(0x4D 0x4F 0x5A 0x5D) is MotionSetCore's `seq` (a u16* key table: slots
# 0x49 0x4B 0x56 0x59 are SEQ entries, resident), MotSetObj00 (obj00.cpp: MotionSetCore on the weak-point object, ARC(0x83)
# = FCV slot 0x7F) and MotSetObj16 (the tentacles, ARC(0x8F) = FCV slot 0x8B). It reads no FCV header field itself (no
# maxFrame reads); MotionMove / MotionMoveF take the work, not ARC. SetObj00(ARC(0x81), ARC(0x82)) is BIN + TPL, ARC(5..8)
# BINs. Heap 4: the textures-only body (3,517,280 B) did not fit r307 (largest block 3,218,496) or r310 (3,083,744).
MOTION_SMALL+=('em36.drs',)
# em31 (Saddler's final form, r332, ROUTE_FINAL room overlay; lane final16 2026-10-16; ARC(n) = archive slot n-4): every
# FCV it names reaches MotionSetCore. (1) Its own body / tentacle: MotionSetCore directly (em31.cpp, 106 calls), including
# the m0 / m1 act pairs (1576 / 1764 / 2355: m1 = ARC(0x26 0x28 0x24 0x48 0x4A 0x4C) is MotionSetCore's `seq`) and the
# `mot` locals (ARC(0x44 0x45 0x6A 0x66 0x67), 2221 / 2272). (2) The tail objects: SetObj16(ARC(0x76) BIN, ARC(0x77) TPL)
# + MotSetObj16(ARC(0x78) / ARC(0x79)) = MotionSetCore on the cObj16; em31 reads the FCV header maxFrame of 0x78 / 0x79
# (*(u16*) & 0x3FFF, 4319 / 4330 / 4778): headers stay resident. (3) The pillar (src/game/objPillar.cpp): SetPillar(ARC(0x7A)
# BIN, ARC(0x7B) TPL); setThrow(ARC(0x7C), ARC(0x7D), ARC(0x7E), ARC(0x75)), setFall(ARC(0x7D), ARC(0x7F)), setBreak(ARC(0x6D),
# seq ARC(0x6E)) only store the pointers; objPillar plays each through MotionSetCore (on the pillar: 164 / 232 / 259 / 360 /
# 390 / 402; on the player: 577 / 579 / 680) and reads motBreak's header maxFrame (163, resident). (4) The player while em31
# lends Leon its subArc (pl->subArc = PL_EM(pl)->subArc, the em2b grab pattern; 1643 / 1916 / 3124 / 3622): PL_ARC(0x6D / 0x6E
# / 0x6B / 0x73 / 0x82 / 0x83 / 0x84) and the macro's PL_ARC_PTR(subArc, mot) go to MotionSetCore on the player.
# BIN / TPL / EFF slots: ARC(4 5 6 7 8 9) (modelInit, ModInfoMgr.create, SetObj00, EspDataLoad), PL_ARC(0x86 / 0x85) (the
# catch object's model). r332.cpp names only room-archive motions (ROOM_ARC_PTR). No FCV is passed anywhere else.
MOTION_SMALL+=('em31.drs',)
# em2b (El Gigante, r119; route lane r119 2026-10-10): every FCV it names goes to MotionSetCore, directly or through
# em2bBlendMotSet (two MotionSetCore calls; the blend work is evaluated by MotionMoveCore), MotSetObj16 (the
# parasite head and the tentacles: MotionSetCore) and plBlendMotSet / MotionSetCore on the player while it lends
# Leon its subArc (the grab). The one other FCV read is ARC(0xE2)'s header maxFrame (em2bTentacleSet), which
# stays resident. Textures: the top-level model TPLs (the four giant variants, the parasite, tentacles, chain,
# rock, the tree it uproots, the grabbed-player prop) go through modelInit / ModInfoMgr / SetObj16 / SetChain /
# SetRock; its EFF slot keeps its own textures. em2b is a ROUTE_OVL room overlay, so its static REL is stripped
# with the knob-conditional module set (ROUTE_OVL_MODULES). The room's heap 4: r119 frees 3,854,656 B in two
# cells, the largest 2,770,912 B, under the 4,689,664 B rel-stripped body.
# em31 (ROUTE_FINAL room overlay, lane final16): its static REL is stripped like the island overlays' (the motion table
# binding needs the 64-byte retained descriptor: native_motion.cpp re4dc_motion_bind, bytes - rel == 64).
ROUTE_OVL_MODULES=('em2b','em2f','em22','pl11','em1d','em1e','em1f','em36','em39','em3a','em32','em3d','em31')
# pl11 (Ashley; PS2_ASHLEY discs, lane ps2cast 2026-10-14): the route overlay dc/pl11.ovl carries her module, so her
# archive's static REL is stripped against it like the room overlays above.
# Knob-conditional static modules (Makefile `MODULES +=` under a route knob) whose archives are compacted against
# their own registry row like the room overlays above: em11 (ROUTE_CH21, r117), em18 (ROUTE_CH13, r102: module 22),
# em16 (ROUTE_CH23, r11d: module 20), and the castle Ganados (ROUTE_CH31 / CH32 / CH41).
KNOB_STATIC_MODULES=('em11','em18','em16','em1a','em1b','em14','em19','em1c')
GANADO_OVERSIZED_RESIDENT=('em1b.drs',)  # + ROUTE_CH31's castle Ganado RELs
# Leon's archives, textures-only: pl00 (jacket, costume 0) and pl08 (no jacket, costume 1: title.cpp picks it in
# every room but r120/r100/r101/r103/r106 once the r106 closet event has run). Same cPlLeon consumers, so pl08
# takes pl00's reviewed textures-only contract (route lane 2026-10-01, r104).
LEON=('pl00.drs','pl08.drs')

# New bounded profiles are explicit and exact-source qualified. They do not
# change existing version2 assets or the global 32KiB producer policy.
BOUNDED_PROFILES={
    'em35-r11f': dict(name='em35.drs',module=61,cap=131072,count=82,
        source='53b653c169d7a022407c8dd75d1a304d904709aae278f80cda5f843dc3b361a0',retain=(0x46,)),
    'pl11-r11f': dict(name='pl11.drs',module=47,cap=32768,count=69,
        source='f6fd174c7a02949c467f792eb08ecbd0529034a66189766dd7fd87e0ee991c58',retain=(0x40,0x43)),
    # castle lane 2026-10-15: pl11-r11f plus Ashley's near-enemy clips kept in the body (MOTION_MISS_LOG, Flycast:
    # entries 0 / 6 / 61 cycled through the two slabs in r203, 61 / 6 / 0 / 3 / 1 / 18 in r208, 140-160 ms per miss).
    # Retained arcs 18 19 21 24 36 68 108 109 (= r11f entries 0 1 3 6 18 47 60 61, 29,056 B); the rest stays bounded.
    'pl11-hot': dict(name='pl11.drs',module=47,cap=32768,count=61,
        source='f6fd174c7a02949c467f792eb08ecbd0529034a66189766dd7fd87e0ee991c58',
        retain=(0x40,0x43,18,19,21,24,36,68,108,109)),
}

def prepare(source, destination, hot_slots=(), textures=None, keep_motion_resident=False, compact_effects=False, bounded_profile=None):
    source,destination=map(Path,(source,destination))
    name=source.name.lower();file='em/'+name
    profile=BOUNDED_PROFILES.get(bounded_profile) if bounded_profile else None
    if bounded_profile and (profile is None or name!=profile['name']):raise ValueError('bounded profile/source mismatch')
    if profile and (hot_slots or keep_motion_resident or compact_effects or textures is None):
        raise ValueError('bounded profiles require all-cold motion plus audited top-level textures')
    if not profile and (name not in GANADO+SMALL+MOTION_SMALL+LEON+('wep02.drs',) or (name not in GANADO+MOTION_SMALL and not keep_motion_resident)):
        raise ValueError('supported contracts: Ganado (em12/em15/em13) and em21/em23/em2a motion; em26/em28/em21/pl00/pl08/wep02 textures')
    if textures is not None and not profile and name not in GANADO+SMALL+LEON+('wep02.drs',):raise ValueError('textures not audited for '+name)
    if compact_effects and name not in GANADO+SMALL:raise ValueError('only enemy EFF slot0 effect consumers qualified')
    if keep_motion_resident and textures is None and not compact_effects:raise ValueError('no selected compaction')
    if destination.exists():raise FileExistsError(destination)
    hot_slots=set(hot_slots)
    original=source.read_bytes();converted=bytearray(original);refs=[];palettes=[];sequences=[]
    if profile and hashlib.sha256(original).hexdigest()!=profile['source']:raise ValueError('unqualified bounded source identity')
    old=mirror.OFFSET_OBSERVER;old_tpl=mirror.TPL_OBSERVER;old_seq=mirror.SEQUENCE_OBSERVER;start=len(mirror.REPORT)
    mirror.OFFSET_OBSERVER=lambda file,field,base,value:refs.append((field,base,value))
    mirror.TPL_OBSERVER=lambda file,off,data,ctx:palettes.append((off,data,ctx))
    mirror.SEQUENCE_OBSERVER=lambda file,off,data,ctx:sequences.append((off,data,ctx))
    try:mirror.convert_file(file,converted)
    finally:mirror.OFFSET_OBSERVER=old;mirror.TPL_OBSERVER=old_tpl;mirror.SEQUENCE_OBSERVER=old_seq
    coverage=mirror.REPORT[start:]
    with tempfile.NamedTemporaryFile(mode='w') as required:
        required.write(file+'\n');required.flush()
        bad=mirror.check_required(coverage,required.name)
    # em2f's four DMY sub-files (#50..#53) have no le_mirror handler; today's r10b disc (le_mirror of the whole tree)
    # already ships them raw, so the texture-only package keeps them raw too (same bytes as today).
    if name=='em2f.drs':bad=[b for b in bad if not b.endswith('no handler (tag DMY)')]
    if bad:raise ValueError('unqualified enemy: '+', '.join(bad))
    # Retain the already-implemented static REL policy; don't restore PPC code.
    converted=mirror.compact_static_rel(file,converted,coverage,mirror.static_module_ids(
        ((source.stem.lower(),) if profile else tuple(m for m in ROUTE_OVL_MODULES+KNOB_STATIC_MODULES if m==source.stem.lower()))))
    slot=mirror.native_payload_slot(converted)
    size,base=struct.unpack_from('<I4xI',converted,slot+4)
    body=converted[base:base+size]
    count,rel=struct.unpack_from('<2I',body)
    boundary=rel or len(body)
    offsets=struct.unpack_from('<%dI'%count,body,16)
    tags=[bytes(body[16+4*count+4*i:20+4*count+4*i]) for i in range(count)]
    first=min(x for x in offsets if x)
    effect_ranges,effect_entries=effects.prepare_sequences(
        [(o-base,d,c) for o,d,c in sequences if base<=o<base+boundary],file+':0#0') if compact_effects else ([],[])
    if compact_effects and not effect_entries:raise ValueError('no eligible effect sequences')
    extra_slots=int(not keep_motion_resident)+int(textures is not None)+int(bool(effect_entries))
    header_growth=(max(0,16+8*(count+extra_slots)-first)+31)&~31
    texture_ranges=[];selected=[];retained=[]
    if textures is not None:
        # Only top-level player/weapon TPLs are selected. Enemy EFF slot0
        # retains D326's separate texture-ID/noise audit; no new EFF family is
        # automatically qualified by this filename extension.
        top_tpl={file+':0#'+str(i) for i,t in enumerate(tags) if t==b'TPL\0'}
        ids=[]
        if name in GANADO:
            if tags[0]!=b'EFF\0':raise ValueError('em12 effect family changed')
            eff=offsets[0];ids_at=eff+struct.unpack_from('<I',body,eff+4)[0]
            num_ids=struct.unpack_from('<I',body,ids_at)[0]
            ids=[struct.unpack_from('<H',body,ids_at+4+i*8)[0] for i in range(num_ids)]
        def allowed(ctx):
            if ctx in top_tpl:return True
            if name in GANADO and ctx.startswith(file+':0#0/tpl'):
                i=int(ctx.rsplit('tpl',1)[1]);return i<len(ids) and ids[i]!=0xfe
            return False
        local_palettes=[(o-base,d,c) for o,d,c in palettes if base<=o<base+boundary]
        texture_ranges,selected,retained=select_upload_only(body,local_palettes,Path(textures),allowed)
        if not texture_ranges:raise ValueError('no qualified enemy textures selected')
    # em2f: its DMY entries keep le_mirror's whole-file qualification from stripping the static REL (today's disc
    # carries the whole REL too); it moves intact behind the tables like the 64-byte descriptor does.
    # pl0f: the release disc carries its whole REL too (pl0f is in no static / overlay module list); it moves intact.
    # em24: the release disc carries its whole REL too (le_mirror keeps it: 394,176 B on the disc = the GC file).
    # em2c / em38 (ROUTE_BOSS4 room overlays): le_mirror keeps their whole REL as for pl0f; it moves intact.
    if rel and rel+64!=len(body) and name not in ('em2f.drs','pl0f.drs','em24.drs','em2c.drs','em38.drs','em2d.drs','em36.drs','em39.drs','em3a.drs','em32.drs','em3d.drs','em31.drs'):raise ValueError('expected retained 64-byte static REL descriptor')
    original_size,original_base=struct.unpack_from('>I4xI',original,slot+4)
    codec=mirror.motion_codec();ranges=[];entries=[];files={};oversized=[]
    for off in ([] if keep_motion_resident else sorted(set(offsets))):
        if not off:continue
        slots=[i for i,o in enumerate(offsets) if o==off]
        if profile and any(i+4 in profile['retain'] for i in slots):continue
        if tags[slots[0]]!=b'FCV\0':continue
        if any(tags[i]!=b'FCV\0' for i in slots):raise ValueError('mixed-tag alias')
        end=min([o for o in offsets if o>off]+[boundary])
        raw=original[original_base+off:original_base+end]
        parsed=codec.parse(raw)
        if codec.serialise(parsed)!=raw:raise ValueError('source FCV roundtrip differs')
        native=codec.serialise(parsed,'<')
        if native!=body[off:end]:raise ValueError('native FCV differs from qualified archive')
        if not parsed.joints:continue # empty motion is already 32 bytes; keep ordinary
        if len(native)>(profile['cap'] if profile else MAX_CLIP):
            # em21: a clip over the runtime's slot limit stays resident (ordinary FCV, exact bytes);
            # the Ganado contract keeps refusing, as before.
            # em1b (castle lane 2026-10-15): one Ganado clip over the slot limit stays resident the same way (exact bytes,
            # ordinary FCV path); every other em1b clip streams. Other Ganados keep refusing.
            if name in MOTION_SMALL or name in GANADO_OVERSIZED_RESIDENT:oversized.append({'source_arc_indices':[i+4 for i in slots],'bytes':len(native)});continue
            raise ValueError('clip exceeds validated cache slot')
        prefix=codec.header_size(len(parsed.joints));resident=(prefix+31)&~31
        if resident>=len(native):continue
        crc=zlib.crc32(native)&0xffffffff
        fnv=2166136261
        for byte in native:fnv=((fnv^byte)*16777619)&0xffffffff
        key='%08x-%08x'%(crc,fnv)
        if key in files and files[key]!=native:raise ValueError('motion identity collision')
        files[key]=native
        ranges.append((off,end,native[:prefix]+bytes(resident-prefix)))
        entries.append({'source_offset':off,'slots':slots,'bytes':len(native),'prefix_bytes':prefix,
                        'resident_bytes':resident,'hot':bool(hot_slots.intersection(i+4 for i in slots)),'source_arc_indices':[i+4 for i in slots],'key':key,'crc':crc,'fnv':fnv,
                        'sha256':hashlib.sha256(native).hexdigest(),'classification':'reloadable key data; stable header retained'})
    if not entries and not keep_motion_resident:raise ValueError('no qualified motion payloads')
    if profile and len(entries)!=profile['count']:raise ValueError('bounded profile motion count differs')
    ranges=sorted(ranges+texture_ranges+effect_ranges)
    local_refs=[(f-base,b-base,v) for f,b,v in refs if base<=f<base+boundary]
    # Existing fmt_drs_body preserves this scalar; it is also an archive-relative
    # boundary and must follow the moved static REL, unlike per-FCV key offsets.
    if rel:local_refs.append((4,0,rel))
    if header_growth:ranges.insert(0,(first,first,bytes(header_growth)))
    out,mapped=compact_spans(body,local_refs,ranges)
    # Insert MTC before the static module so readEmData's data/REL split stays true.
    new_rel=mapped(boundary);table=bytearray()
    for e in entries:
        e['resident_offset']=mapped(e['source_offset'])
        table+=struct.pack('<5I',e['resident_offset'],e['bytes'],e['crc'],e['fnv'],int(e['hot']))
    table_bytes=((32+len(table)+31)&~31) if entries else 0
    texture_index_bytes=((32+12*len(selected)+31)&~31) if selected else 0
    effect_index_bytes=((32+12*len(effect_entries)+31)&~31) if effect_entries else 0
    final_bytes=len(out)+table_bytes+texture_index_bytes+effect_index_bytes
    tables=bytearray();new_tags=[];new_offsets=[]
    if effect_entries:
        new_tags.append(b'ESQ\0');new_offsets.append(new_rel)
        tables+=effects.identity_index(effect_entries,mapped,final_bytes)
    if selected:
        new_tags.append(b'NTR\0');new_offsets.append(new_rel+len(tables))
        tables+=native_identity_index(selected,mapped,len(body),final_bytes)
    if entries:
        new_tags.append(b'MTC\0');new_offsets.append(new_rel+len(tables))
        header=struct.pack('<8s6I',MAGIC,3 if profile else 2,len(entries),STRIDE,zlib.crc32(table)&0xffffffff,final_bytes,profile['cap'] if profile else MAX_CLIP)
        tables+=header+table+bytes(table_bytes-32-len(table))
    out=out[:new_rel]+tables+out[new_rel:]
    struct.pack_into('<2I',out,0,count+extra_slots,new_rel+len(tables) if rel else 0)
    for i,off in enumerate(new_offsets):struct.pack_into('<I',out,16+4*(count+i),off)
    out[16+4*(count+extra_slots):16+8*(count+extra_slots)]=b''.join(tags+new_tags)
    # Every non-FCV archive family and module descriptor retains exact bytes.
    for off in sorted(set(offsets)):
        if not off:continue
        end=min([o for o in offsets if o>off]+[boundary])
        if (keep_motion_resident or tags[list(offsets).index(off)]!=b'FCV\0') and not any(off<=a<end for a,b,_ in texture_ranges+effect_ranges):
            assert out[mapped(off):mapped(end)]==body[off:end]
    if rel:assert out[-64:]==body[-64:]
    packaged=mirror.replace_native_payload(converted,out)
    report={'contract':source.stem+'-native-textures-v1' if keep_motion_resident else source.stem+'-source-motion-cache-v2','source_sha256':hashlib.sha256(original).hexdigest(),
            'original_static_body_bytes':size,'resident_body_bytes':len(out),
            'archive_recovery_bytes':size-len(out),'index_bytes':table_bytes,'header_growth_bytes':header_growth,
            'motion_source_bytes':sum(e['bytes'] for e in entries),'motion_header_bytes':sum(e['resident_bytes'] for e in entries),
            'motions_resident':keep_motion_resident,
            'effects':{'entries':effect_entries,'index_bytes':effect_index_bytes,
                'recovery_bytes':sum(b-a-len(v) for a,b,v in effect_ranges)-effect_index_bytes,
                'policy':'all records resident; exact native word reconstruction, stable retained generator references'},
            'textures':{'selected':selected,'retained':retained,'identity_table_bytes':texture_index_bytes,
                'removed_payload_bytes':sum(b-a for a,b,_ in texture_ranges),
                'replacement_record_bytes':32*len(texture_ranges)},
            'max_clip_bytes':max((e['bytes'] for e in entries),default=0),'oversized_resident':oversized,
            'hot_payload_bytes':sum(e['bytes'] for e in entries if e['hot']),
            'cold_reserve_bytes':2*max((e['bytes'] for e in entries if not e['hot']),default=0),
            'cache_policy':None if keep_motion_resident else 'retain hot set and LRU cold entries until capacity pressure; evaluation release never evicts','entries':entries,'qualification':coverage,
            'retained':'all SEQ events, EFF behavior tables, CPU/palette/mip texels, models/materials/skeletons and exact FCV headers',
            'lifetime':'all motions remain source-owned; native identity views follow archive ownership' if keep_motion_resident else 'keys remain cached; pins protect source MotionSetCore, MotionMoveCore, MotionGetSpeed and MotionGetPosition; header/SEQ pointers remain source-archive-owned',
            'limits':'offline contract only until native binding, source consumer lifetimes, actual heap and visible output are qualified; motion selection also requires complete prefetch/concurrency audit'}
    if profile:
        report['contract']=bounded_profile+'-source-motion-cache-v3'
        report['bounded_profile']=dict(profile=bounded_profile,module=profile['module'],version=3,clip_cap=profile['cap'],
            count=len(entries),table_crc32=zlib.crc32(table)&0xffffffff,body_bytes=len(out),
            body_crc32=zlib.crc32(out)&0xffffffff,body_sha256=hashlib.sha256(out).hexdigest(),
            descriptor_sha256=hashlib.sha256(out[-64:]).hexdigest(),descriptor_words=list(struct.unpack('<16I',out[-64:])),
            preserved_full_arcs=list(profile['retain']),policy='two reserved slabs only; zero hot flags; no spill; no heap12 cache')
        report['cache_policy']=report['bounded_profile']['policy']
    destination.mkdir();(destination/'mot').mkdir()
    for key,data in files.items():(destination/'mot'/(key+'.fcv')).write_bytes(data)
    (destination/name).write_bytes(packaged)
    (destination/(source.stem+'.arc')).write_bytes(out)
    (destination/'motion-residency-report.json').write_text(json.dumps(report,indent=2)+'\n')
    return report

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',required=True,type=Path);p.add_argument('--output',required=True,type=Path)
    p.add_argument('--hot-audit',type=Path,help='Source-derived diagnostic hot-set audit; not a replay usage filter')
    p.add_argument('--diagnostic-incomplete-prefetch',action='store_true',help='Allow a clearly labelled source-audit diagnostic, never production qualification')
    p.add_argument('--textures',type=Path,help='Existing exact native texture packages; externalize reviewed upload-only enemy texels')
    p.add_argument('--keep-motion-resident',action='store_true',help='Texture-only selection retains every FCV payload; no motion cache')
    p.add_argument('--compact-effects',action='store_true',help='Selectable lossless resident em12 EST records; original heads and all effect behavior retained')
    p.add_argument('--bounded-profile',choices=sorted(BOUNDED_PROFILES),help='Exact-source r11f version3 reserve-only profile')
    a=p.parse_args()
    if not a.keep_motion_resident and not a.hot_audit:p.error('--hot-audit is required for motion residency')
    audit=json.loads(a.hot_audit.read_text()) if a.hot_audit else {}
    if not a.keep_motion_resident and not audit.get('source_complete') and not a.diagnostic_incomplete_prefetch:
        p.error('prefetch/concurrency audit is incomplete; explicit diagnostic selection required')
    r=prepare(a.source,a.output,audit.get('union',{}).get('source_arc_indices',()),a.textures,a.keep_motion_resident,a.compact_effects,a.bounded_profile)
    report_path=a.output/'motion-residency-report.json'
    r['prefetch_audit']=audit
    r['runtime_qualified']=False
    report_path.write_text(json.dumps(r,indent=2)+'\n')
    print('em12 resident body',r['original_static_body_bytes'],'->',r['resident_body_bytes'],'motion entries',len(r['entries']),'hot + cold cap',r['hot_payload_bytes']+r['cold_reserve_bytes'])
