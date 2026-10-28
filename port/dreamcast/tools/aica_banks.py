#!/usr/bin/env python3
"""Build-time conversion of GameCube sound banks to AICA 4-bit ADPCM (AICA_AUDIO=1).

Every sound bank of the game (room .dar, enemy/player/weapon .drs, etc/core.das,
bgm/bio4midi.dat, bgm/doorse.dat) is a DvdHeader archive whose sound blocks are
a type-1 part (MRAM: ISS tables + the SYN wavetable) and a type-2 part (ARAM:
the GC DSP-ADPCM sample image). This tool rewrites each type-2 part IN PLACE
(same offset, same size, so no archive offset changes) as

    AicaBankHeader (32 bytes) + AICA ADPCM image (+ zero padding)

and platform/audio_aica.cpp copies the image straight into its fixed AICA slot
instead of decoding and re-encoding on the SH-4 at load time.

The image layout is the one the runtime derives from the wavetable: samples in
sample-index order, each decimated by a power of two to the bank's rate cap
(`sample_shift`) and packed to 4-byte blocks (`sample_bytes`). The rate caps
come from a per-room AICA budget over a route (`plan`), so every room of the
route fits the fixed AICA layout: resident slots (CORE, PL, WEP, BGM0, BGM1,
DOOR) plus one room arena (ROOM, FOOT, enemies) reset at each room load.

usage:
  aica_banks.py plan  --mirror DIR [--route r100,r101,r103] [--json OUT]
  aica_banks.py build --mirror DIR --out OVERLAY [--route ...] [--cache DIR] [--json OUT] [--check]
  aica_banks.py streams --mirror DIR --out OVERLAY [--streams 0:2,0:8]
      (bgm/aica_str.dat: the route's disc streams as AICA ADPCM, see build_streams)
  aica_banks.py merge --mirror DIR --overlay OVERLAY --out DATADIR
      (a disc data directory for mkdisc.sh: the mirror hardlinked, overlay files in place)
  aica_banks.py disc --mirror DIR --out DATADIR --cache DIR [--json OUT]
      (build + streams + merge in one step, both cached by content: what
      tools/d367/stage.sh runs for every disc; banks rewritten, the rest hardlinked)
  aica_banks.py reconvert --root DISCTREE --mirror DIR[,DIR...] --out OVERLAY [--cache DIR] [--json OUT]
      (refilter the prebuilt banks of an existing disc tree with decimate_aa, headers and sizes kept)
  aica_banks.py fit --mirror DISCTREE --file FILE --room rNNN --out FILE2 [--cache DIR] [--json OUT] [--check]
      (prebuild a file's GC room-arena banks into DISCTREE's frozen layout, next to the room's prebuilt banks there)
  aica_banks.py fitwep --mirror DISCTREE --file FILE --out FILE2 [--cache DIR] [--json OUT] [--check]
      (prebuild a weapon file's GC WEP block into DISCTREE's frozen WEP slot at the highest cap that fits)

Prebuilt banks are decimated with an anti-alias filter (decimate_aa, FILTER_VERSION 2); the runtime
converter for banks that are not prebuilt keeps its box average (decimate mirrors it).

Game data never enters the repository: the mirror, the overlay and the cache are
private directories.
"""
import argparse
import hashlib
import json
import os
import struct
import sys

MAGIC = 0x31434941           # "AIC1"
VERSION = 1
# AicaBankHeader (platform/audio_aica.cpp): magic, version, cap_hz, image bytes, samples,
# FNV-1a of the wavetable sample table, GC part size, slot of this block, 0,
# then the whole route layout (slot bytes by block index 0..8, 8 = room arena), padding.
HDR = struct.Struct('<IHHIIIIII9I7I')
HDR_SIZE = 96
assert HDR.size == HDR_SIZE

AICA_POOL = 1900544          # KOS snd_mem pool after snd_init (0x200000 - AICA_RAM_START 0x30000)
MOVIE_RESERVE = 64 * 1024    # kept unallocated: snd_stream (movies, 2 x 8 KB) + margin
STREAM_RING = 2 * 24 * 1024  # disc streams (st002/st008): stereo AICA ADPCM ring, 2 x 0.77 s at 32 kHz
CAPS = (32000, 22050, 16000, 11025, 8000)

# Slot of a sound block type (DvdHeader sndType/sndNo -> SndMem block index t).
SLOT_NAMES = {0: 'CORE', 1: 'PL', 2: 'WEP', 3: 'BGM0', 4: 'BGM1', 7: 'DOOR', 8: 'ARENA'}
BLOCK_NAMES = {0: 'CORE', 1: 'PL', 2: 'WEP', 3: 'BGM0', 4: 'BGM1', 5: 'FOOT', 6: 'ROOM', 7: 'DOOR'}


def block_index(snd_type, snd_no):
    if snd_type == 3:
        return 3 + snd_no
    if snd_type == 8:
        return 8 + snd_no
    return snd_type


def slot_of(t):
    return 8 if t in (5, 6) or t >= 8 else t


# Preferred (maximum) rate cap per block kind; the planner lowers caps to fit.
def pref_cap(t):
    if t in (3, 4):
        return 32000
    if t in (0, 2, 7):
        return 22050
    if t == 6:
        return 16000
    return 11025


# Order in which the planner gives up quality: enemies, footsteps, player, room
# ambience, weapon, door, core UI, music last.
LOWER_ORDER = (8, 5, 1, 6, 2, 7, 0, 3)

# Fixed caps under the planner's floor for banks that do not fit the frozen arena even at 8 kHz (decision 2026-10-15:
# no arena relayout; match the PS2's lower rates, else the least audible ambience first, enemy voices kept). The
# planner never lowers these further. The frozen ARENA slot is 1,004,192 B (layout line of the build log). Enemy voices
# of the castle Ganados (em1a / em1b / em14 / em19) are em11's bank (same key; on the PS2 em1b.snd == em11.snd), frozen
# at 8 kHz by the earlier route. The PS2 keeps these rooms' banks at 8 / 12 / 16 kHz, so there is no lower rate to match.
# r201: ROOM 257,900 + FOOT 92,284 + pl11 68,064 + em11 682,196 = 1,100,444 B; ROOM 8000 -> 4000 Hz (128,980 B).
# r209: ROOM 267,144 + FOOT 79,476 + em11 682,196 = 1,028,864 B; ROOM 8000 -> 4000 Hz (133,608 B).
# r20c / r20d: em11 + em25 (131,516 B at 8 kHz) + room: 1,055,520 / 1,043,552 B; ROOM 8000 -> 4000 Hz (74,772 /
# 72,924 B). FOOT and every voice bank keep their planned rates.
FORCED_CAPS = {('st2/r201.dar', 6): 4000, ('st2/r209.dar', 6): 4000,
               ('st2/r20c.dar', 6): 4000, ('st2/r20d.dar', 6): 4000}

# Route: resident banks and the room-arena banks of each room (enemy lists from
# the frontier ESL audit, /root/probe/d367-agents/frontier/frontier-ledger.json).
# em/pl08.drs: Leon without the jacket (costume 1, every room after r106; title.cpp) loads into the same player
# area as pl00 and carries the identical PL bank (fnv 556f69f1), so it is resident like pl00 and adds no bytes.
# Room music that loads into the resident BGM0 slot (route lane c13, chapter 1-3): bgm/bgmtbl.dat lists these
# bio4midi entries for the room's first BGM track. They are prebuilt at the highest cap that fits the frozen BGM0
# slot, so no room converts music at load time (runtime conversion into free AICA RAM failed: SND SEQ data error at
# r109). A room's second-slot track (BGM1, 0 bytes in the frozen layout) is replaced at runtime by a resident one
# (snd.cpp, ROUTE_CH13). Only rooms of the planned route add entries. r104 and r107 both request
# bank 9; it must also be prebuilt, otherwise runtime conversion exhausts the unreserved AICA bytes.
ROOM_BGM0 = {'r102': [1], 'r104': [9], 'r107': [9], 'r108': [5], 'r109': [3], 'r10a': [3], 'r10b': [3], 'r11b': [10], 'r11a': [10], 'r119': [3], 'r118': [11], 'r117': [11],
             'r112': [1], 'r111': [6], 'r113': [6], 'r11c': [6],
             # chapter 2-3 (lane ch22-1014; the runtime's "blk 3 (N GC bytes) does not fit" sizes matched to the
             # bio4midi entries): r11d #6 (as r11c), r10f / r11f / r200 #8 (740151 GC bytes)
             'r11d': [6], 'r10f': [8], 'r11f': [8], 'r200': [8],
             # chapter 3-1 (castle lane 2026-10-15): r202 plays #8 at entry (740160 GC bytes, as r200)
             'r202': [8],
             # island (lane ch5found16): bgm/bgmtbl.dat slot-0 track of each room's entry 0 (the runtime's "blk 3"
             # sizes 637,312 / 476,384 matched): #7 (637,306 GC bytes), r311 #14, r315 #5, r31a / r31b #1
             'r300': [7], 'r301': [7], 'r30a': [7], 'r31c': [7], 'r31d': [7], 'r320': [7], 'r321': [7], 'r325': [7], 'r327': [7], 'r329': [7],
             'r311': [14], 'r315': [5], 'r31a': [1], 'r31b': [1],
             # chapter 4 (lane ch4found16): bgm/bgmtbl.dat entry 0 slot-0 track (low byte), matched to the runtime's
             # "blk 3 (637,312 / 476,384 GC bytes) does not fit": #7 (r211 r213 r214 r226 r227 r22a), #14 (r210 r222
             # r224); r219 / r225 #5 and r21d / r229 #1 are already prebuilt (r108 / r102).
             'r211': [7], 'r213': [7], 'r214': [7], 'r226': [7], 'r227': [7], 'r22a': [7],
             'r210': [14], 'r222': [14], 'r224': [14], 'r219': [5], 'r225': [5], 'r21d': [1], 'r229': [1]}

# Leon's other stage-1 weapons (--weapons; stage.sh AICA_WEAPONS=1; issue lamb2k/re4dc#1, silent weapons). The GC
# loads the equipped weapon's SE block (WEP, block 2) on every weapon change (weaponLoad -> its .drs) into the one WEP
# area; audio_aica.cpp places a prebuilt WEP bank into the resident WEP slot the same way (blk_prepare frees the
# previous one). Without a prebuilt image the runtime converts into free AICA RAM, which holds only the 30 KB headroom
# (taken in r100 by em2a's runtime bank), so every weapon but the handgun was silent ("blk 2 ... does not fit").
# Each bank is built at the highest rate cap whose image fits the planned (or frozen) WEP slot, so the layout and every
# other bank stay byte-identical. wep20 (TMP + stock) shares wep11's bank, wep21 / wep24 (rifle + scopes) wep09's.
# snd28 round 3 (10-28, issue #1 again): the weapon banks that still converted at load were silent on every equip
# ("blk 2 ... does not fit": wep03 / wep04 / wep05 / wep12 / wep18 seen, items 0x25-0x29 / 0x34); every remaining one
# is prebuilt the same way (the release recipe's copies: fitwep, data set snd28c).
WEAPONS = ['em/wep01.drs', 'em/wep07.drs', 'em/wep09.drs', 'em/wep11.drs', 'em/wep13.drs', 'em/wep19.drs',
           'em/wep20.drs', 'em/wep21.drs', 'em/wep24.drs',
           'em/wep03.drs', 'em/wep04.drs', 'em/wep05.drs', 'em/wep06.drs', 'em/wep08.drs', 'em/wep10.drs',
           'em/wep12.drs', 'em/wep14.drs', 'em/wep15.drs', 'em/wep16.drs', 'em/wep17.drs', 'em/wep18.drs']

RESIDENT = ['etc/core.das','em/pl00.drs', 'em/pl08.drs', 'em/wep02.drs', 'bgm/bio4midi.dat#0', 'bgm/doorse.dat#*']
ROOMS = {
    'title': ['ss/cmn/title.snd'],                  # title / menu ROOM bank, on every boot
    'r100': ['st1/r100.dar', 'em/em12.drs', 'em/em23.drs', 'em/em21.drs'],
    'r101': ['st1/r101.dar', 'em/em15.drs', 'em/em26.drs', 'em/em28.drs'],
    'r103': ['st1/r103.dar', 'em/em26.drs', 'em/em28.drs', 'em/em21.drs', 'em/em12.drs'],
    # r106 (route lane): R106Init EmReadSearch 0x12/0x29/0x2A/0x2E (hall Ganados, bats, the dog's em2a, crawlers)
    'r106': ['st1/r106.dar', 'em/em12.drs', 'em/em29.drs', 'em/em2a.drs', 'em/em2e.drs'],
    # r104 (route lane): no EmReadSearch; the ESL (etc/emleon00.esl) lists em13 only (assets.sh discover r104)
    'r104': ['st1/r104.dar', 'em/em13.drs'],
    # r107 (route lane): the ESL lists em12 / em27 (the lake fish) / em2a (assets.sh discover r107)
    'r107': ['st1/r107.dar', 'em/em12.drs', 'em/em27.drs', 'em/em2a.drs'],
    # r105 (route lane): the ESL lists em15 (enabled later) / em23 / em2a (assets.sh discover r105)
    'r105': ['st1/r105.dar', 'em/em15.drs', 'em/em23.drs', 'em/em2a.drs'],
    # Chapter 1-3 (route lane c13; assets.sh discover): r102 em18 (the merchant, script load), r108 em17 (enabled
    # later) / em23 / em24 (read at room entry, route-c13-r108a), r10a em12 / em24 / em2a (r109 below: em23).
    'r102': ['st1/r102.dar', 'em/em18.drs'],
    'r108': ['st1/r108.dar', 'em/em17.drs', 'em/em23.drs', 'em/em24.drs'],
    'r10a': ['st1/r10a.dar', 'em/em12.drs', 'em/em24.drs', 'em/em2a.drs'],
    # r10b (chapter 1-3's end, the lake): the ESL lists pl0f (Leon's boat, entry) / em2f (Del Lago, enabled later);
    # R10bInit's r10b_setEm sets five em27 fish (EmSetEvent). bgmtbl: slot 0 = bio4midi #3 (as r109 / r10a), no slot 1.
    'r10b': ['st1/r10b.dar', 'em/pl0f.drs', 'em/em2f.drs', 'em/em27.drs'],
    # r11b (chapter 2-1's start, the lake shore): pl0f (the boat, entry), em22 (the shore wolves, script spawn), em27
    # (the fish, entry). bgmtbl: both slots bio4midi #10 (as r10c / r11a), stream 0:17 (the battle stream).
    'r11b': ['st1/r11b.dar', 'em/pl0f.drs', 'em/em22.drs', 'em/em27.drs'],
    # r210 (St2, world coverage lane): no enemy archive (assets.sh discover r210: lists emleon03/04, no entries).
    # Ashley (pl11) is beside Leon here (lane ch4found16: cxc4cmW loads em/pl11.drs at entry).
    'r210': ['st2/r210.dar', 'em/pl11.drs'],
    # r40c (St4, world coverage lane): no enemy archive (discover r40c: omake00.esl, no entries)
    'r40c': ['st4/r40c.dar'],
    # r219 (St2, world coverage lane): no enemy archive (discover r219: emleon04.esl, no entries); Ashley (pl11) as r210
    'r219': ['st2/r219.dar', 'em/pl11.drs'],
    # r40a (St4, world coverage lane): the em1f island soldiers (discover r40a: omake00.esl, 11 entries, script load)
    'r40a': ['st4/r40a.dar', 'em/em1f.drs'],
    # Follow-up 7 (world coverage lane, St1; assets.sh discover: the rooms' ESL / script enemies)
    'r109': ['st1/r109.dar', 'em/em23.drs'],
    'r10c': ['st1/r10c.dar', 'em/em12.drs'],
    # r10d / r10e (lane ch2rooms20, chapter 2-1's side path; the runtime's blk 8.. load order): r10d em18 (the merchant)
    # + pl0f (the boat); r10e pl0f, em29, em27, em18.
    'r10d': ['st1/r10d.dar', 'em/em18.drs', 'em/pl0f.drs'],
    'r10e': ['st1/r10e.dar', 'em/pl0f.drs', 'em/em29.drs', 'em/em27.drs', 'em/em18.drs'],
    'r10f': ['st1/r10f.dar', 'em/em13.drs', 'em/pl11.drs'],   # pl11: Ashley (chapter 2-3, lane ch22-1014)
    # r11a (route lane r11a, chapter 2-1): em24 is also read at room entry, as in r108 / r10a (route-r11a-x1a:
    # "blk 9 (34040 bytes) does not fit the room arena"). bgmtbl: bio4midi #10 (as r11b).
    'r11a': ['st1/r11a.dar', 'em/em12.drs', 'em/em24.drs'],
    # r119 (route lane r119, El Gigante): em2b (the giant, script spawn, rel-stripped) and em21 (the dog that helps, set
    # by the dog event). bgmtbl: slot 0 = bio4midi #3 (as r109 / r10a / r10b), stream 0:5 (the giant battle).
    'r119': ['st1/r119.dar', 'em/em2b.drs', 'em/em21.drs'],
    # r118 (route lane r118, the church, entered from r119 door 0 before Ashley is rescued): em22 (ESL entry 0x78
    # type, loaded at room entry; the dog spawns only after the rescue). em17 / em3b are enabled later (the after-rescue
    # Ganados; not on this route). bgmtbl: slot 0 = bio4midi #11, slot 1 = #9 (snd.cpp plays slot 1's requests on the
    # resident slot-0 track, as r108 / r10a), stream 0:0x17.
    'r118': ['st1/r118.dar', 'em/em22.drs'],
    # r117 (route lane r117, the church interior, chapter 2-1's end): pl11 (Ashley, enemy module 3: R117Init reads her
    # archive, SubCharInit after the s00 event) and em11 (the Ganados R117Init sets on a later visit, Part 0).
    # bgmtbl: slot 0 = bio4midi #11 (as r118) in both entries (0 and the post-s10 entry 1), no slot 1, no stream.
    'r117': ['st1/r117.dar', 'em/pl11.drs', 'em/em11.drs'],
    # Chapter 2-2 (route lane ch22, ROUTE_CH22; assets.sh discover + the rooms' bgmtbl entries): Ashley (pl11) follows
    # Leon through every room. r118 after the rescue (Item_find_flg 0x00100000) sets the Ganados 0x79..0x7F (em17) and
    # the dog 0x78 (em22): with Ashley that set needs 1,053,528 B even at 8 kHz (arena 1,004,192), so r118 keeps its
    # chapter 2-1 list (the later archive's bank does not fit and stays silent; open). r112: em18 (the merchant), bgmtbl #1 (as r102), streams 0:0x19. r111 / r113: em17 (the
    # Ganados) and em2a (the crows), bgmtbl #6 (r113's slot 1 is #3: snd.cpp plays it on the slot-0 track), stream 0:9.
    'r112': ['st1/r112.dar', 'em/em18.drs', 'em/pl11.drs'],
    # Stage 3 (ROUTE_CH3 first pass, disc 2; assets.sh discover with the stage-3 ESL rule: etc/emleon06.esl):
    # r300 em1d (the island soldiers, enabled later), r301 em1e (enabled later + entry) / em3b (entry), r303 em1e.
    # Banks not built yet (needs a disc-2 mirror); the soldiers' archives also do not fit heap 4 uncompacted.
    'r300': ['st3/r300.dar', 'em/em1d.drs'],
    'r301': ['st3/r301.dar', 'em/em1e.drs', 'em/em3b.drs'],
    'r303': ['st3/r303.dar', 'em/em1e.drs'],
    # Island chapters 5-1..5-4 (lane ch5found16, 2026-10-16): room .dar (st3 lane rel33) + the room's enemies from the
    # PS2 lists (ISLAND-ROUTE-20261016.md) + Ashley (pl11) from her rescue in r30c to r316 and again from r329.
    'r304': ['st3/r304.dar', 'em/em1f.drs', 'em/em25.drs'],
    'r305': ['st3/r305.dar', 'em/em1e.drs'],
    'r306': ['st3/r306.dar'],
    'r307': ['st3/r307.dar'],
    'r308': ['st3/r308.dar'],
    'r30b': ['st3/r30b.dar', 'em/em1f.drs', 'em/pl11.drs'],
    'r30c': ['st3/r30c.dar', 'em/em1f.drs', 'em/em25.drs', 'em/pl11.drs'],
    'r30e': ['st3/r30e.dar', 'em/em1e.drs', 'em/pl11.drs'],
    'r309': ['st3/r309.dar', 'em/pl11.drs'],
    'r30a': ['st3/r30a.dar', 'em/em18.drs', 'em/em23.drs', 'em/pl11.drs'],
    'r310': ['st3/r310.dar', 'em/pl11.drs'],
    'r311': ['st3/r311.dar', 'em/em1f.drs', 'em/pl11.drs'],
    'r30d': ['st3/r30d.dar', 'em/pl11.drs'],
    'r312': ['st3/r312.dar', 'em/em18.drs', 'em/pl11.drs'],
    'r30f': ['st3/r30f.dar', 'em/em1f.drs', 'em/pl11.drs'],
    'r315': ['st3/r315.dar', 'em/em1e.drs', 'em/pl11.drs'],
    'r316': ['st3/r316.dar', 'em/em1e.drs', 'em/pl11.drs'],
    'r317': ['st3/r317.dar'],
    'r318': ['st3/r318.dar'],
    'r31a': ['st3/r31a.dar', 'em/em18.drs'],
    'r31b': ['st3/r31b.dar', 'em/em32.drs'],
    'r31d': ['st3/r31d.dar', 'em/em1e.drs'],
    'r31c': ['st3/r31c.dar', 'em/em39.drs', 'em/em3a.drs'],
    'r320': ['st3/r320.dar', 'em/em1d.drs', 'em/em3d.drs'],
    'r321': ['st3/r321.dar', 'em/em1f.drs'],
    'r325': ['st3/r325.dar'],
    'r326': ['st3/r326.dar'],
    'r327': ['st3/r327.dar', 'em/em1d.drs'],
    'r329': ['st3/r329.dar', 'em/em18.drs', 'em/pl11.drs'],
    'r330': ['st3/r330.dar', 'em/em1f.drs', 'em/pl11.drs'],
    # not listed yet (no prepared archive the tool can read): em36
    'r111': ['st1/r111.dar', 'em/em17.drs', 'em/em2a.drs', 'em/pl11.drs'],
    'r113': ['st1/r113.dar', 'em/em17.drs', 'em/em2a.drs', 'em/pl11.drs'],
    # r11c (the cabin, chapter 2-2's end): Ashley (pl11, module 3), Luis (pl14, module 4) and the siege Ganados (em13),
    # bgmtbl #6, stream 0:0xA. em13's bank is em12's (same sound ID), frozen at 11025 Hz by the opening route (601,288 B):
    # with the room's own banks at 8 kHz and pl11 the arena has no room for pl14's (55,324 B at 8 kHz; 8.8 KB over), so
    # Luis's bank stays silent (open, as r118's later archive).
    'r11c': ['st1/r11c.dar', 'em/pl11.drs', 'em/em13.drs'],
    # Chapter 2-3 (lane ch22-1014, ROUTE_CH23; assets.sh discover + run logs): Ashley (pl11) follows Leon through
    # every room. r11d: em3b (no sound block) and em16 (enabled later); r11e: em2b (the second El Gigante, script
    # load); r11f: em35 (Mendez); r200: em12 / em18 / em3b (pre-read for s00) and pl11. r10f's row is below.
    'r11d': ['st1/r11d.dar', 'em/pl11.drs', 'em/em16.drs'],
    'r11e': ['st1/r11e.dar', 'em/pl11.drs', 'em/em2b.drs'],
    'r11f': ['st1/r11f.dar', 'em/pl11.drs', 'em/em35.drs'],
    'r200': ['st2/r200.dar', 'em/pl11.drs', 'em/em12.drs', 'em/em18.drs'],
    # Chapter 3-1 (castle lane 2026-10-15; assets.sh discover + first-pass runs, "aica: blk 5/6 ... does not fit"):
    # Ashley (pl11) follows Leon; Ganados em11 (r202 r207 r203), the merchant em18 (r202), em1b (r201), em1a (r208),
    # em14 (r204). Room archives are the compact31 (upload-only + native mips) .dar files.
    'r202': ['st2/r202.dar', 'em/pl11.drs', 'em/em11.drs', 'em/em18.drs'],
    'r207': ['st2/r207.dar', 'em/pl11.drs', 'em/em11.drs'],
    'r203': ['st2/r203.dar', 'em/pl11.drs', 'em/em11.drs'],
    'r201': ['st2/r201.dar', 'em/pl11.drs', 'em/em1b.drs'],
    'r208': ['st2/r208.dar', 'em/pl11.drs', 'em/em1a.drs'],
    'r204': ['st2/r204.dar', 'em/pl11.drs', 'em/em14.drs'],
    # Chapters 3-2 .. 3-4 (castle lane 2026-10-15, ROUTE_CH32; assets.sh discover lists): Ashley is captured at 3-1's end
    # (r204s00) and returns as the player in 3-4 (r20d / r20e; her player bank is not planned yet). Room archives are the
    # rel31 (compact32 + GC scenery release) .dar files.
    'r205': ['st2/r205.dar', 'em/em2d.drs'],
    'r209': ['st2/r209.dar', 'em/em1a.drs'],
    'r20a': ['st2/r20a.dar', 'em/em23.drs', 'em/em2d.drs'],
    'r20b': ['st2/r20b.dar', 'em/em18.drs', 'em/em22.drs'],
    'r20c': ['st2/r20c.dar', 'em/em11.drs', 'em/em1b.drs', 'em/em25.drs'],
    'r20f': ['st2/r20f.dar', 'em/em14.drs', 'em/em25.drs'],
    # r206: Ashley (pl11) is beside Leon for the snipe, s10 and after s20 (cx32g: em11 'does not fit' without her row)
    'r206': ['st2/r206.dar', 'em/pl11.drs', 'em/em11.drs'],
    'r20d': ['st2/r20d.dar', 'em/em11.drs', 'em/em19.drs', 'em/em25.drs'],
    'r20e': ['st2/r20e.dar', 'em/em3c.drs'],
    # Chapter 4-1..4-4 (lane ch4found16, 2026-10-16): room .dar (lane rel31) + the room's enemies from the PS2 lists
    # (CH4-FOUNDATIONS-20261016.md cast list) + Ashley (pl11) where the runs load her (r210 r212 r219). The boss rooms
    # r221 (Verdugo, em2c) and r228 (Salazar, em38) are left to their owners (ch3found16 / cast16).
    'r211': ['st2/r211.dar', 'em/em14.drs'],
    'r212': ['st2/r212.dar', 'em/em11.drs', 'em/pl11.drs'],
    'r213': ['st2/r213.dar', 'em/em2d.drs'],
    'r214': ['st2/r214.dar', 'em/em14.drs', 'em/em1a.drs', 'em/em25.drs'],
    'r215': ['st2/r215.dar'],
    'r216': ['st2/r216.dar', 'em/em3c.drs'],
    'r217': ['st2/r217.dar', 'em/em11.drs', 'em/em25.drs'],
    'r218': ['st2/r218.dar', 'em/em1c.drs'],
    'r21b': ['st2/r21b.dar', 'em/em15.drs'],
    'r21d': ['st2/r21d.dar', 'em/em2d.drs'],
    'r220': ['st2/r220.dar', 'em/em18.drs'],
    'r222': ['st2/r222.dar', 'em/em11.drs'],
    'r223': ['st2/r223.dar', 'em/em16.drs'],
    'r224': ['st2/r224.dar', 'em/em2b.drs'],
    'r225': ['st2/r225.dar', 'em/em13.drs'],
    'r226': ['st2/r226.dar', 'em/em11.drs'],
    'r227': ['st2/r227.dar', 'em/em14.drs'],
    'r229': ['st2/r229.dar', 'em/em29.drs', 'em/em18.drs'],
    'r22a': ['st2/r22a.dar', 'em/em18.drs'],
    'r22b': ['st2/r22b.dar'],
    # r40b (St4, follow-up 7): em1f (bringup inventory: em1f/em1f, st4_0)
    'r40b': ['st4/r40b.dar', 'em/em1f.drs'],
}


# ---------------------------------------------------------------- archives
def fnv1a(b):
    h = 0x811C9DC5
    for x in b:
        h = ((h ^ x) * 0x01000193) & 0xFFFFFFFF
    return h


def archive_bases(mirror, spec):
    """(path, [archive base offsets]) for 'file', 'file#N' (container entry N) or 'file#*'."""
    name, _, sel = spec.partition('#')
    path = os.path.join(mirror, name)
    if not sel:
        return path, [0]
    base = os.path.splitext(path)[0]
    hed = open(base + '.hed', 'rb').read()
    if name.endswith('bio4midi.dat'):
        offs = list(struct.unpack_from('<24I', hed, 0))
        offs = [o for i, o in enumerate(offs) if i == 0 or o]
    elif name.endswith('doorse.dat'):
        n = struct.unpack_from('<I', hed, 0x60)[0]
        offs = list(struct.unpack_from('<%dI' % n, hed, 0x20))
    else:
        raise ValueError('unknown container ' + name)
    if sel == '*':
        return path, offs
    return path, [offs[int(sel)]]


def parse_entries(d, base):
    out = []
    p = base + 0x20
    while p + 32 <= len(d) and len(out) < 64:
        e = struct.unpack_from('<8I', d, p)
        p += 32
        if e[0] == 0xFFFFFFFF:
            return out
        if e[0] > 16:          # not a little-endian DvdHeader (unswapped GC entry)
            return None
        out.append(e)
    return out


def sound_blocks(d, base, rel=None):
    """[(t, mram_ofs, mram_size, aram_ofs, aram_size)] of an archive at `base` (nested included)."""
    rel = base if rel is None else rel
    ents = parse_entries(d, base)
    if ents is None:
        return None
    mram, aram, out = [], [], []
    for (typ, size, dest, ofs, st, arg, no, x) in ents:
        if typ == 4:
            sub = sound_blocks(d, rel + ofs, rel + ofs)
            if sub:
                out += sub
        elif typ == 1:
            mram.append((block_index(st, no), rel + ofs, size))
        elif typ == 2:
            aram.append((block_index(st, no), rel + ofs, size))
    for (t, mo, ms) in mram:
        for j, (t2, ao, asz) in enumerate(aram):
            if t2 == t:
                out.append((t, mo, ms, ao, asz))
                del aram[j]
                break
    return out


def wavetable(d, t, mo, ms):
    """(sample table bytes, [(fmt, rate, offset, length, adpcm_index)], [coef tables])."""
    m = d[mo:mo + ms]
    base = 0 if t in (3, 4) else struct.unpack_from('<I', m, 0)[0]
    num, dls, sit, seq = struct.unpack_from('<4I', m, base)
    wt = base + dls
    x0, inst, rgn, art, smp, adp = struct.unpack_from('<6I', m, wt)
    n = (adp - smp) // 16
    table = m[wt + smp: wt + smp + 16 * n]
    samples = [struct.unpack_from('<HHIIH', table, 16 * i) for i in range(n)]
    nco = max(s[4] for s in samples) + 1 if samples else 0
    coefs = []
    for i in range(nco):
        a = struct.unpack_from('<16h7H', m, wt + adp + 0x2E * i)
        coefs.append((a[:16], a[16:]))
    return table, samples, coefs


# ---------------------------------------------------------------- codec (mirrors audio_aica.cpp)
def sample_shift(rate, length, cap):
    sh = 0
    while sh < 3 and ((rate >> sh) > cap + cap // 64 or (length >> sh) > 65534):
        sh += 1
    return sh


def sample_bytes(length, sh):
    n = (length + (1 << sh) - 1) >> sh
    return ((n + 7) // 8) * 4


def bank_bytes(samples, cap):
    return sum(sample_bytes(s[3], sample_shift(s[1], s[3], cap)) for s in samples)


def dsp_decode(img, offset_nib, length, coef, hist):
    """GC DSP-ADPCM -> list of s16 (offset in nibbles from the block start, frame aligned)."""
    a, (gain, ps, yn1, yn2, lps, ly1, ly2) = coef
    h1 = yn1 - 65536 if yn1 >= 32768 else yn1
    h2 = yn2 - 65536 if yn2 >= 32768 else yn2
    out = []
    p = offset_nib // 2
    left = length
    app = out.append
    while left > 0:
        hdr = img[p]
        scale = 1 << (hdr & 0xF)
        idx = (hdr >> 4) & 7
        c1, c2 = a[2 * idx], a[2 * idx + 1]
        for k in range(14 if left >= 14 else left):
            byte = img[p + 1 + (k >> 1)]
            nib = (byte & 0xF) if (k & 1) else (byte >> 4)
            if nib >= 8:
                nib -= 16
            v = (((nib * scale) << 11) + 1024 + c1 * h1 + c2 * h2) >> 11
            if v > 32767:
                v = 32767
            elif v < -32768:
                v = -32768
            h2 = h1
            h1 = v
            app(v)
        left -= 14
        p += 8
    return out


def decimate(x, sh):
    if sh == 0:
        return x
    n = 1 << sh
    out = []
    full = len(x) // n * n
    for i in range(0, full, n):
        out.append(sum(x[i:i + n]) >> sh)
    if full < len(x):
        rest = x[full:]
        s = sum(rest)
        out.append(int(s / len(rest)))      # C: acc / (s32) acc_n truncates toward zero
    return out


# Anti-alias decimation for PREBUILT banks (issue lamb2k/re4dc#15 follow-up). decimate() above mirrors the runtime
# converter (platform/audio_aica.cpp, banks that are not prebuilt): a box average of 2^sh neighbours, whose first
# sidelobe is only ~13 dB down, so everything between the new Nyquist and the source band folds back as grainy
# aliasing. decimate_aa() low-passes at the INPUT rate with a Kaiser-windowed sinc (cutoff 0.45 x the output rate,
# stopband from 0.5 x the output rate, ~72 dB) and keeps every 2^sh-th filtered value. Same output count as
# decimate() ((len + n - 1) >> sh), same centre (input k*n + (n - 1)/2, the box's centre), so lengths, loop points,
# bank sizes, slots and the planner's results are unchanged; only the PCM differs. Values are rounded and clamped to
# s16. Outside a loop the signal is zero before the first and after the last sample (a one-shot starts and ends in
# silence). Loop seam: outputs whose input centre lies in the loop body [ls, le) read the body circularly (index
# ls + (i - ls) mod (le - ls)), so the samples on both sides of the jump are filtered as one continuous periodic
# signal and the seam stays click-free on every pass. The intro -> loop transition (played once) keeps its linear
# neighbourhood. Loops come from the wavetable regions (sample_loops); a sample no region loops is filtered as a
# one-shot. FILTER_VERSION is part of the bank cache key (cached_convert).
FILTER_VERSION = 2          # 1 = box average (decimate), 2 = Kaiser sinc (decimate_aa)
AA_CUTOFF = 0.45            # x output rate
AA_HALF = 24                # half width in output samples (taps = ~48 x 2^sh + 2^sh at the input rate)
AA_BETA = 6.98              # Kaiser beta for ~72 dB stopband attenuation
_AA_KERNELS = {}


def _bessel_i0(x):
    s, t, k = 1.0, 1.0, 1
    while t > 1e-12 * s:
        t *= (x / (2.0 * k)) ** 2
        s += t
        k += 1
    return s


def aa_kernel(sh):
    """(first relative input offset, taps) of the decimate_aa filter for 2^sh."""
    if sh in _AA_KERNELS:
        return _AA_KERNELS[sh]
    import math
    n = 1 << sh
    c0 = (n - 1) / 2.0
    w = float(AA_HALF * n)
    fc = AA_CUTOFF / n                          # cycles per input sample
    r0 = int(math.floor(c0 - w)) + 1
    r1 = int(math.ceil(c0 + w)) - 1
    i0b = _bessel_i0(AA_BETA)
    taps = []
    for r in range(r0, r1 + 1):
        t = r - c0
        x = 2.0 * fc * t
        sinc = 1.0 if x == 0 else math.sin(math.pi * x) / (math.pi * x)
        u = t / w
        win = _bessel_i0(AA_BETA * math.sqrt(max(0.0, 1.0 - u * u))) / i0b
        taps.append(2.0 * fc * sinc * win)
    g = sum(taps)
    taps = [v / g for v in taps]                # unity DC gain
    _AA_KERNELS[sh] = (r0, taps)
    return _AA_KERNELS[sh]


def decimate_aa(x, sh, loop=None):
    """Anti-aliased decimation by 2^sh; loop = (start, end) in input samples or None. See the comment above."""
    if sh == 0:
        return list(x)
    import operator
    mul = operator.mul
    n = 1 << sh
    ln = len(x)
    cnt = (ln + n - 1) >> sh
    r0, taps = aa_kernel(sh)
    nt = len(taps)
    pad = nt + n
    xp = [0] * pad + list(x) + [0] * pad
    out = [0] * cnt

    def emit(k, buf, start):
        v = sum(map(mul, taps, buf[start:start + nt]))
        v = int(v + 0.5) if v >= 0 else -int(-v + 0.5)
        out[k] = 32767 if v > 32767 else (-32768 if v < -32768 else v)

    k_lo, k_hi = cnt, cnt
    if loop:
        ls, le = loop
        le = min(le, ln)
        if 0 <= ls < le:
            # outputs whose centre k*n + (n-1)/2 lies in [ls, le)
            k_lo = max(0, (2 * ls - (n - 1) + 2 * n - 1) // (2 * n))
            k_hi = min(cnt, (2 * le - (n - 1) + 2 * n - 1) // (2 * n))
            if k_lo < k_hi:
                period = le - ls
                base = k_lo * n + r0             # first input index any loop output reads
                span = (k_hi - 1) * n + r0 + nt - base
                ring = [x[ls + (i - ls) % period] for i in range(base, base + span)]
                for k in range(k_lo, k_hi):
                    emit(k, ring, k * n + r0 - base)
            else:
                k_lo = k_hi = cnt
    for k in range(cnt):
        if k_lo <= k < k_hi:
            continue
        emit(k, xp, k * n + r0 + pad)
    return out


def sample_loops(d, t, mo, ms, nsamples):
    """{sample index: (loop start, loop end)} from the wavetable regions (WTREGION: loopStart, loopLength,
    sampleIndex), as audio_aica.cpp plays them (n.lsa = loopStart >> sh, n.len = (loopStart + loopLength) >> sh).
    The first looped region of a sample wins (regions sharing a sample carry the same loop)."""
    m = d[mo:mo + ms]
    base = 0 if t in (3, 4) else struct.unpack_from('<I', m, 0)[0]
    num, dls, sit, seq = struct.unpack_from('<4I', m, base)
    wt = base + dls
    offs = struct.unpack_from('<6I', m, wt)
    rgn = offs[2]
    later = [o for o in offs[1:] if o > rgn]
    if not rgn or not later:
        return {}
    out = {}
    for i in range((min(later) - rgn) // 24):
        p = wt + rgn + 24 * i
        if p + 24 > len(m):
            break
        unity, kg, fine, attn, lstart, llen, art, sidx = struct.unpack_from('<BBhiIIII', m, p)
        if llen and sidx < nsamples and sidx not in out:
            out[sidx] = (lstart, lstart + llen)
    return out


SCALE = (230, 230, 230, 230, 307, 409, 512, 614)


def yamaha_encode(x):
    """AICA/Yamaha 4-bit ADPCM, low nibble first, padded to 4-byte blocks."""
    pred, step = 0, 127
    nibs = []
    app = nibs.append
    for v in x:
        d = v - pred
        neg = d < 0
        t = (-d if neg else d) << 2
        s = step
        if t >= s << 3:
            q = 7
        else:
            q = 0
            if t >= s << 2:
                q = 4
                t -= s << 2
            if t >= s << 1:
                q += 2
                t -= s << 1
            if t >= s:
                q += 1
        delta = (s * (2 * q + 1)) >> 3
        pred = pred - delta if neg else pred + delta
        if pred > 32767:
            pred = 32767
        elif pred < -32768:
            pred = -32768
        step = (step * SCALE[q]) >> 8
        if step < 127:
            step = 127
        elif step > 24576:
            step = 24576
        app(q | (8 if neg else 0))
    if len(nibs) & 1:
        nibs.append(0)
    b = bytes(nibs[i] | (nibs[i + 1] << 4) for i in range(0, len(nibs), 2))
    return b + bytes((-len(b)) % 4)


def yamaha_decode(b, n):
    pred, step = 0, 127
    out = []
    for i in range(n):
        q = (b[i >> 1] >> (4 * (i & 1))) & 0xF
        m = q & 7
        delta = (step * (2 * m + 1)) >> 3
        pred = pred - delta if q & 8 else pred + delta
        pred = max(-32768, min(32767, pred))
        step = max(127, min(24576, (step * SCALE[m]) >> 8))
        out.append(pred)
    return out


def energies(ref, got):
    return sum(v * v for v in ref), sum((a - b) ** 2 for a, b in zip(ref, got))


def convert_block(img, samples, coefs, cap, check=False, loops=None, filt=FILTER_VERSION):
    """AICA image (bytes) and, when `check`, the bank SNR (signal energy over ADPCM
    error energy, all samples, dB) after decoding the image back. filt 2 (default):
    decimate_aa with `loops` ({sample index: (start, end)}); filt 1: the runtime's box."""
    import math
    parts, sig, err = [], 0, 0
    for si, (fmt, rate, offset, length, ai) in enumerate(samples):
        sh = sample_shift(rate, length, cap)
        src = dsp_decode(img, offset, length, coefs[ai], None)
        pcm = decimate_aa(src, sh, (loops or {}).get(si)) if filt >= 2 else decimate(src, sh)
        enc = yamaha_encode(pcm)
        need = sample_bytes(length, sh)
        enc = enc[:need] + bytes(need - min(need, len(enc)))
        parts.append(enc)
        if check:
            s_, e_ = energies(pcm, yamaha_decode(enc, len(pcm)))
            sig += s_
            err += e_
    worst = 10 * math.log10((sig or 1) / (err or 1)) if check else 999.0
    return b''.join(parts), worst


# ---------------------------------------------------------------- route / plan
class Bank:
    def __init__(self, spec, path, base, t, mo, ms, ao, asz, table, samples, coefs):
        self.spec, self.path, self.base, self.t = spec, path, base, t
        self.mo, self.ms, self.ao, self.asz = mo, ms, ao, asz
        self.table, self.samples, self.coefs = table, samples, coefs
        self.fnv = fnv1a(table)
        self.key = (self.fnv, asz)
        self.cap = FORCED_CAPS.get((spec, t), pref_cap(t))

    def bytes_at(self, cap):
        return bank_bytes(self.samples, cap)

    @property
    def size(self):
        return self.bytes_at(self.cap)

    @property
    def name(self):
        return '%s:%s' % (self.spec, BLOCK_NAMES.get(self.t, 'EM%d' % (self.t - 8)))


def load_banks(mirror, specs, cache):
    out = []
    for spec in specs:
        path, bases = archive_bases(mirror, spec)
        if not os.path.exists(path):
            print('  missing', spec, file=sys.stderr)
            continue
        if path not in cache:
            with open(path, 'rb') as f:
                cache[path] = f.read()
        d = cache[path]
        for base in bases:
            blocks = sound_blocks(d, base)
            if blocks is None:
                continue
            for (t, mo, ms, ao, asz) in blocks:
                if struct.unpack_from('<I', d, ao)[0] == MAGIC:
                    raise SystemExit('%s already converted (AIC1 at %#x): use the unconverted mirror' % (spec, ao))
                table, samples, coefs = wavetable(d, t, mo, ms)
                if samples:
                    out.append(Bank(spec, path, base, t, mo, ms, ao, asz, table, samples, coefs))
    return out


def plan(mirror, rooms, budget, fixed=(), weapons=()):
    """fixed: a route planned first whose caps and layout are frozen (the discs already built on it keep
    every bank byte-identical); the other rooms then only lower banks no fixed room uses, until each fits
    the frozen layout (route lane, r106 2026-10-01)."""
    frozen, fixed_slots = {}, None
    if fixed:
        # nested levels ([[...], [...]]): each level is planned on the frozen result of the levels before it, so a
        # route extension keeps every bank of the previous route byte-identical (lane ch22-1014: em18 of r102)
        levels = [list(x) for x in fixed] if isinstance(fixed[0], (list, tuple)) else [list(fixed)]
        _, _, funiq, fixed_slots, _ = plan(mirror, levels[-1], budget, levels[:-1])
        frozen = {k: b.cap for k, b in funiq.items()}
    data = {}
    resident = load_banks(mirror, RESIDENT, data)
    room_banks = {r: load_banks(mirror, ROOMS[r], data) for r in rooms}
    # one Bank object per distinct bank (same wavetable + size = same sound ID)
    uniq = {}
    for b in resident + [b for r in rooms for b in room_banks[r]]:
        uniq.setdefault(b.key, b)
    res = [uniq[b.key] for b in resident]
    per_room = {r: list({uniq[b.key].key: uniq[b.key] for b in room_banks[r]}.values()) for r in rooms}
    for k, cap in frozen.items():
        if k in uniq:
            uniq[k].cap = cap

    def layout():
        slots = {}
        for b in res:
            s = slot_of(b.t)
            slots[s] = max(slots.get(s, 0), (b.size + 31) & ~31)
        arena = {r: sum((b.size + 31) & ~31 for b in per_room[r]) for r in rooms}
        slots[8] = max(arena.values()) if arena else 0
        return slots, arena

    while True:
        slots, arena = layout()
        total = sum(slots.values())
        if fixed_slots is not None:
            if all(v <= fixed_slots.get(s, 0) for s, v in slots.items()):
                break
        elif total <= budget:
            break
        # lower one cap step on the largest bank of the first kind in LOWER_ORDER that can still go down
        done = False
        for kind in LOWER_ORDER:
            cands = [b for b in uniq.values() if (b.t if b.t < 8 else 8) == kind and b.cap > CAPS[-1]
                     and b.key not in frozen]
            if kind == 8 or kind in (5, 6):
                worst = max(arena, key=arena.get)
                cands = [b for b in cands if b in per_room[worst]]
            if not cands:
                continue
            b = max(cands, key=lambda x: x.size)
            b.cap = CAPS[CAPS.index(b.cap) + 1]
            done = True
            break
        if not done:
            raise SystemExit('route does not fit %d bytes even at %d Hz' % (budget, CAPS[-1]))
    slots, arena = layout()
    if fixed_slots is not None:
        slots = dict(fixed_slots)
    bgm0 = slots.get(3, 0)
    for r in rooms:
        for n in ROOM_BGM0.get(r, ()):
            for b in load_banks(mirror, ['bgm/bio4midi.dat#%d' % n], data):
                if b.key in uniq:
                    continue
                fit = [c for c in CAPS if c <= pref_cap(b.t) and ((b.bytes_at(c) + 31) & ~31) <= bgm0]
                if b.t != 3 or not fit:
                    raise SystemExit('bio4midi #%d (%s) does not fit the BGM0 slot (%d bytes)' % (n, r, bgm0))
                b.cap = fit[0]
                uniq[b.key] = b   # the frozen layout, so every bank header stays byte-identical
    wep = slots.get(2, 0)
    for b in load_banks(mirror, list(weapons), data):
        if b.key in uniq:
            continue           # the resident handgun bank, or a variant sharing an earlier weapon's bank
        fit = [c for c in CAPS if c <= pref_cap(b.t) and ((b.bytes_at(c) + 31) & ~31) <= wep]
        if b.t != 2 or not fit:
            raise SystemExit('%s does not fit the WEP slot (%d bytes)' % (b.name, wep))
        b.cap = fit[0]
        uniq[b.key] = b
    return res, per_room, uniq, slots, arena


def report(res, per_room, uniq, slots, arena, budget):
    def row(b):
        return {'bank': b.name, 'gc_bytes': b.asz, 'samples': len(b.samples), 'cap_hz': b.cap,
                'aica_bytes': b.size, 'aica_at_pref_cap': b.bytes_at(pref_cap(b.t)),
                'max_src_rate': max(s[1] for s in b.samples)}
    rep = {'budget_bytes': budget, 'pool_bytes': AICA_POOL, 'movie_reserve': MOVIE_RESERVE, 'stream_ring': STREAM_RING,
           'slots': {SLOT_NAMES[s]: v for s, v in sorted(slots.items())},
           'layout_total': sum(slots.values()), 'headroom': budget - sum(slots.values()),
           'resident': [row(b) for b in res],
           'rooms': {r: {'arena_bytes': arena[r], 'resident_bytes': sum(v for s, v in slots.items() if s != 8),
                         'total_bytes': arena[r] + sum(v for s, v in slots.items() if s != 8),
                         'banks': [row(b) for b in per_room[r]]} for r in per_room}}
    wep = [row(b) for b in uniq.values() if b.t == 2 and b not in res]
    if wep:
        rep['weapons'] = wep
    return rep


def build(mirror, out, res, per_room, uniq, slots, cache_dir, check, weapons=()):
    data, banks = {}, {}
    for b in uniq.values():
        banks.setdefault(b.path, []).append(b)
    # every occurrence of a bank (also duplicates in other files) gets the same caps
    by_key = {b.key: b for b in uniq.values()}
    written = []
    # Every planned room's files too: a file whose banks all duplicate another file's (em13.drs's EM0 is em12's,
    # route lane 2026-10-01) holds no unique bank, but its copy still needs the prebuilt image.
    room_paths = set(archive_bases(mirror, s)[0] for r in per_room for s in ROOMS[r])
    room_paths |= set(archive_bases(mirror, s)[0] for s in weapons)   # wep20 / 21 / 24 hold no unique bank
    for path in sorted({b.path for b in uniq.values()} | set(archive_bases(mirror, s)[0] for s in RESIDENT) | room_paths):
        if not os.path.exists(path):
            continue
        with open(path, 'rb') as f:
            d = bytearray(f.read())
        rel = os.path.relpath(path, mirror)
        spec_like = [s for s in RESIDENT + list(weapons) + [x for r in ROOMS.values() for x in r]
                     + ['bgm/bio4midi.dat#%d' % n for r in per_room for n in ROOM_BGM0.get(r, ())] if s.partition('#')[0] == rel]
        bases = sorted({bb for s in spec_like for bb in archive_bases(mirror, s)[1]})
        n_conv = 0
        for base in bases:
            for (t, mo, ms, ao, asz) in sound_blocks(bytes(d), base) or []:
                table, samples, coefs = wavetable(bytes(d), t, mo, ms)
                key = (fnv1a(table), asz)
                if key not in by_key or not samples:
                    continue
                b = by_key[key]
                loops = sample_loops(bytes(d), t, mo, ms, len(samples))
                img, worst = cached_convert(cache_dir, bytes(d[ao:ao + asz]), samples, coefs, b.cap, check, loops)
                assert len(img) == b.size, (b.name, len(img), b.size)
                lay = [slots.get(i, 0) for i in range(9)]
                hdr = HDR.pack(MAGIC, VERSION, b.cap, len(img), len(samples), key[0], asz, slot_of(t), 0, *lay, *([0] * 7))
                blob = hdr + img
                if len(blob) > asz:     # cannot happen for real banks (4-bit GC -> <=4-bit AICA)
                    print('  %s: header + image %d > GC part %d, left for runtime conversion' % (b.name, len(blob), asz))
                    continue
                d[ao:ao + asz] = blob + bytes(asz - len(blob))
                n_conv += 1
                print('  %-34s t=%-2d %8d GC -> %8d AICA at %5d Hz  fnv %08x%s' % (rel + '@%#x' % base, t, asz, len(img), b.cap,
                      fnv1a(img), '' if worst > 900 else '  ADPCM SNR %.1f dB' % worst))
        if n_conv:
            dst = os.path.join(out, rel)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            with open(dst, 'wb') as f:
                f.write(d)
            written.append((rel, n_conv))
    return written


def cached_convert(cache_dir, img, samples, coefs, cap, check, loops=None, filt=FILTER_VERSION):
    # The filter version and the loops are part of the key: a cache filled by the box filter (keys without them)
    # is never reused for a filtered bank. The bank header keeps VERSION 1 (audio_aica.cpp rejects any other
    # version and the image layout is unchanged).
    if cache_dir:
        key = img + struct.pack('<I', cap) + repr(samples).encode()
        if filt >= 2:
            key += b' filter %d %r %r %r %r' % (filt, AA_CUTOFF, AA_HALF, AA_BETA, sorted((loops or {}).items()))
        h = hashlib.sha256(key).hexdigest()
        p = os.path.join(cache_dir, h + ('.chk2' if check else '') + '.aic')
        if os.path.exists(p):
            blob = open(p, 'rb').read()
            return blob[8:], struct.unpack_from('<d', blob, 0)[0]
    out, worst = convert_block(img, samples, coefs, cap, check, loops, filt)
    if cache_dir:
        os.makedirs(cache_dir, exist_ok=True)
        with open(p, 'wb') as f:
            f.write(struct.pack('<d', worst) + out)
    return out, worst


# ---------------------------------------------------------------- disc streams (snd_str)
# bgm/aica_str.dat: the route's disc streams transcoded to AICA 4-bit ADPCM at their
# own rate (32 kHz), played by audio_aica.cpp from a 2 x 12 KB per channel AICA ring
# (ADPCM long-stream mode) refilled by a reader thread; the GC ring voices stay silent.
#
#   header  : magic 'AIS1', count, 0, 0, then `count` entries of STR_ENT
#   entry   : file offset of the stream in its .sbb (SND_SHD offset), rate,
#             flags (1 = loops | stream block << 8 | request number << 16), channels, intro samples (A = [0, loop end)),
#             loop samples (B = [loop start, loop end), 0 = none), A data offset,
#             B data offset (bytes in this file, 2 KB aligned)
#   data    : per region, channels interleaved in 2 KB blocks (L 2 KB, R 2 KB, ...),
#             so one contiguous read refills both channels.
STR_MAGIC = 0x31534941   # "AIS1"
STR_ENT = struct.Struct('<8I')
STR_BLOCK = 2048
# Stream block -> file (snd.cpp StrFileTbl {1, 0x5F} -> dvd.cpp FileTbl): 0 music, 1 events / voice.
STREAM_FILES = {0: 'bgm/bio4bgm.sbb', 1: 'bgm/bio4evt.sbb'}
ROUTE_STREAMS = [
    (0, 2), (0, 8),   # bgmtbl: r100 / r101 0x8002, r103 0x8008
    (1, 3),           # Ope radio (sscrn.cpp OpeSetOpenTerm strTbl: terms 0, 1 in r100, 0xC at r101 entry)
    (1, 14),          # em21 (em21.cpp SndStrReq(1, 0xE)), in r100 and r103
    (1, 0x33),        # Ope radio, strTbl term 2: r101 post-bell call (r101_execOperator, design-r103 W8c)
]
# Radio call voices (stage.sh AICA_CALL_VOICES=1 / --call-voices). Without them the call screen is
# silent: SndSubScreenEnter ducks the BGM and pauses the SEs for the voice, which the reader logs as
# "stream sbb=... not in aica_str.dat, silent". Requests seen on the stage-1 route (sbb offsets):
# 1:140 (09310000, r100 first call), 1:141 (09400000, r100 call after the s20 truck), 1:142, 1:144,
# 1:145, 1:152. One-shots streamed through the same ring; disc cost ~4 MB.
CALL_VOICE_STREAMS = [(1, 140), (1, 141), (1, 142), (1, 144), (1, 145), (1, 152)]
# The play disc's list through chapter 2-1 (ROUTE_CH21: r10b, r11b, r11a), `--streams ch21`. Each room's streams are
# appended, so every earlier entry keeps its data bytes (only the 2 KB header grows): 0:4 (r10b, the boss), 0:17 + 1:36
# (r11b, the battle and the ambush), 1:148 (the r11b radio call voice, 22 s one-shot; requested on r11b entry after
# the Ope radio 1:3: "stream sbb=9900000 (1:148) not in aica_str.dat" without it).
CH21_STREAMS = ROUTE_STREAMS + CALL_VOICE_STREAMS + [(0, 4), (0, 17), (1, 36), (1, 148)]
# The current play disc's file (r22j test 7: lane r118 snd.sh order, ch21 + 0:5 + 0:23 for r119 / r118) plus 0:29, the
# chapter 1-3 results / save screen music in r10b (sbb 0x3480000, 60 s one-shot; "not in aica_str.dat, silent"
# without it). `--streams ch21r`: entries 0..16 and their data bytes identical to the lane r118 file.
CH21R_STREAMS = (ROUTE_STREAMS[:4] + [(1, 0x33)] + CALL_VOICE_STREAMS + [(0, 4), (0, 17), (1, 36), (0, 5), (1, 148),
                 (0, 23), (0, 29)])
# Chapter 2-2 (ROUTE_CH22, route lane ch22): ch21r plus the bgmtbl streams of r112 (0:0x19), r111 / r113 (0:9) and
# r11c (0:0xA), and the event streams of r118 after the rescue (1:5 room stream, 1:0xE0 the altar view) and r113 (1:0x27,
# the shoulder ride), appended so every earlier entry keeps its data bytes. `--streams ch22`.
CH22_STREAMS = CH21R_STREAMS + [(0, 0x19), (0, 9), (0, 0xA), (1, 5), (1, 0xE0), (1, 0x27)]
# Chapter 1 completion (lane audio16, 2026-10-16): every stream the chapter 1 rooms (r100..r10b) request that ch21r lacks,
# appended so entries 0..17 and their data bytes stay identical to the ch21r file (only the 2 KB header grows). From the
# rooms' bgm/bgmtbl.dat entries and their scripts' SndStrReq / SndRoomStrStart / EvtSndStrPlay calls; the full-play logs
# showed 0:0, 0:10, 0:25 and 0:21 as "not in aica_str.dat, silent". r10a's 0:16 shares 0:23's stream header (already in).
#   0:0    death / continue screen (game.cpp, 8.6 s loop)      0:25 (0x19) r102 room stream (the merchant, 41 s loop)
#   0:10   r104 / r107 room stream (52 s loop)                 0:21 (0x15) r104 show view (r104_execShowView, 9 s)
#   0:7    r106 battle stream (area 4, r106_ctrlBgm, 117 s)    0:51 (0x33) r108 show view (r108_execShowView, 5.5 s)
#   0:18   r100 skull message (r100_mes_gaikotu_bgm, 5.7 s)    1:34 (0x22) r100 house event stream
#   1:62 / 1:59 (0x3E / 0x3B) r101 fight start (by side)       1:134 (0x86) r104 event, 1:29 (0x1D) r10b event
#   1:180..1:194 (0xB4..0xC2) the merchant's voice lines (ss_shop.cpp shop_msg[].str, shopStrPlay; 1:185 "over here"
#   was "not in aica_str.dat" in the r102 run)
# The backend plays one stream at a time (audio_aica.cpp str_scan), so a request made while another plays stays silent
# as before; the file only removes the "not on the disc" case. 45 entries: the reader needs AICA_STR_ENT_MAX=48 (game
# Makefile; at the default 32 it refuses the whole file and every disc stream is silent). `--streams ch1`.
CH1_STREAMS = CH21R_STREAMS + [(0, 0), (0, 0x19), (0, 10), (0, 0x15), (0, 7), (0, 0x33), (0, 0x12), (1, 0x22), (1, 0x3E),
                               (1, 0x3B), (1, 0x86), (1, 0x1D)] + [(1, n) for n in range(0xB4, 0xC3)]
# Chapter 2-3 (ROUTE_CH23, lane ch22-1014): ch22 plus the streams the 2-3 rooms requested ("stream sbb=... not in
# aica_str.dat" in the first-pass runs): r11d 0:22, r200 0:24, r11e 1:76; appended so every earlier entry keeps its
# data bytes. `--streams ch23` (the 10-14 lane file; superseded by ch2 below).
CH23_STREAMS = CH22_STREAMS + [(0, 22), (0, 24), (1, 76)]
# Chapters 1 to 2-3 (lane ch2code16, 2026-10-16): ch1 (snd16, 45 entries) plus the chapter 2-2 / 2-3 streams ch1 lacks,
# appended so entries 0..44 and their data bytes stay identical to the test 15 snd16 file. 53 entries: the reader needs
# AICA_STR_ENT_MAX >= 53 (the chapter 2 arms use 56; test 15 keeps 48 with snd16). `--streams ch2`.
CH2_STREAMS = CH1_STREAMS + [s for s in CH23_STREAMS if s not in CH1_STREAMS]
# Chapter 3-1 (castle lane 2026-10-15): ch23 plus r207's radio call voice 1:153 (sbb 0x9ba0000, "not in
# aica_str.dat, silent" on r207 entry); appended so every earlier entry keeps its data bytes. `--streams ch31`.
CH31_STREAMS = CH23_STREAMS + [(1, 153)]
# Chapter 3 foundations (lane ch3found16, 2026-10-16): the ch1 file (test 15, 45 entries, unchanged) plus every ch31
# stream it lacks (the chapter 2-2 / 2-3 rooms and r207's radio voice 1:153), appended so entries 0..44 and their data
# bytes stay identical to the ch1 file. `--streams ch3`; the reader needs AICA_STR_ENT_MAX >= len(CH3_STREAMS).
# + the castle room streams the ch3found16 runs requested (cxc3fmW, Flycast: "stream sbb=1d18000" r208, "sbb=25e0000" r209 /
#   r20c, both "not in aica_str.dat, silent"): 0:15 and 0:20 (bio4bgm.sbb; 25e0000 is also 1:49's offset in bio4evt.sbb,
#   the room BGM block is 0). 55 entries.
CH3_STREAMS = CH1_STREAMS + [k for k in CH31_STREAMS if k not in CH1_STREAMS] + [(0, 15), (0, 20)]
# The island disc (lane ch5found16, 2026-10-16; three-disc layout, user decision: disc 3 = island + final chapter).
# Disc 3 carries its own bgm/aica_str.dat (streams are found by sbb offset, so the order is free): the shared
# streams (0:0 death / continue, 0:29 results, the merchant's voice lines 1:180..1:194), every room stream the island
# rooms' bgm/bgmtbl.dat entries name (r300..r330, blk 0) and the event / voice streams the first-pass runs logged as
# "not in aica_str.dat, silent" (cx5cmW, Flycast). `--streams ch5`; 37 entries, so AICA_STR_ENT_MAX=56 holds it.
CH5_STREAMS = ([(0, 0), (0, 29)] + [(1, n) for n in range(0xB4, 0xC3)]
               + [(0, n) for n in (0x14, 0x27, 0x39, 0x34, 0x1A, 0x29, 0x28, 0x03, 0x30, 0x19, 0x2A, 0x2B, 0x2C, 0x2D, 0x3B)]
               + [(1, 159), (1, 230), (1, 233), (1, 234), (1, 238)])
# Chapter 4 (lane ch4found16, 2026-10-16): CH3_STREAMS (55) + chapter 4 would pass the 63-entry header, so chapter 4
# gets its own file, as the island disc does (ch5): the shared streams (0:0 death / continue, 0:29 results, the
# merchant's voice lines 1:180..1:194), every stream the chapter 4 rooms' bgm/bgmtbl.dat entries name (r210..r22b, all
# entries, blk 0) and the streams the first-pass runs logged as "not in aica_str.dat, silent" (cxc4cmW, Flycast):
# r218 0:31 (sbb 36f8000), r222 0:46 (5890000), r227 1:95 (5690000), r22b 1:135 (8f80000), r229 1:157 (a0e8000).
# `--streams ch4`; 39 entries (AICA_STR_ENT_MAX=56 holds it). Which disc carries it is the disc layout's call.
CH4_STREAMS = ([(0, 0), (0, 29)] + [(1, n) for n in range(0xB4, 0xC3)]
               + [(0, n) for n in (5, 13, 15, 16, 22, 25, 27, 31, 32, 33, 34, 35, 36, 37, 38, 47, 53, 56, 46)]
               + [(1, 95), (1, 135), (1, 157)])
# The castle disc (three-disc layout: disc 2 = chapters 3 and 4; coordinator 10-16): one file, CH3_STREAMS (entries
# 0..54 in their order) + the chapter 4 streams it lacks (18). 73 entries: a two-sector header, AICA_STR_ENT_MAX >= 73
# (80). `--streams castle`. Measured against swapping a ch3 and a ch4 file at the chapter 4 save: 100,765,696 B on
# disc vs 114,851,840 B (the shared streams twice), +768 B of .bss (56 -> 80 entries) and one 2 KB read at boot.
CASTLE_STREAMS = CH3_STREAMS + [k for k in CH4_STREAMS if k not in CH3_STREAMS]
STREAM_PRESETS = {'ch21': CH21_STREAMS, 'ch21r': CH21R_STREAMS, 'ch22': CH22_STREAMS, 'ch1': CH1_STREAMS,
                  'ch23': CH23_STREAMS, 'ch2': CH2_STREAMS, 'ch31': CH31_STREAMS, 'ch3': CH3_STREAMS,
                  'ch4': CH4_STREAMS, 'castle': CASTLE_STREAMS, 'ch5': CH5_STREAMS}


def nibble_to_sample(n):
    return (n // 16) * 14 + max(0, (n % 16) - 2)


def stream_headers(mirror):
    with open(os.path.join(mirror, 'bgm', 'bio4str.hed'), 'rb') as f:
        h = f.read()
    out = {}
    for blk in range(2):
        base = struct.unpack_from('<I', h, 4 * blk)[0]
        num, shd_ofs, rit_ofs = struct.unpack_from('<3I', h, base)
        for no in range(num):
            shd_no = struct.unpack_from('<h', h, base + rit_ofs + 16 * no)[0]
            so = base + shd_ofs + struct.unpack_from('<I', h, base + shd_ofs + 4 * shd_no)[0]
            flag, samples, ln, rate, start, loop, lpend, offset = struct.unpack_from('<8I', h, so)
            coefs = [struct.unpack_from('<16h', h, so + 0x20), struct.unpack_from('<16h', h, so + 0x40)]
            yn1 = struct.unpack_from('<2h', h, so + 0x68)
            yn2 = struct.unpack_from('<2h', h, so + 0x6C)
            out[(blk, no)] = dict(flag=flag, samples=samples, len=ln, rate=rate, loop=loop, lpend=lpend,
                                  offset=offset, coefs=coefs, yn1=yn1, yn2=yn2)
    return out


def decode_stream(sbb, shd):
    """Both channels of a GC stream as s16 lists (stereo: 16 KB L/R halves interleaved)."""
    stereo = shd['flag'] & 1
    half = 0x4000 if stereo else 0x8000
    nch = 2 if stereo else 1
    frames = (shd['samples'] + 13) // 14
    chans = []
    for c in range(nch):
        data = bytearray()
        need = frames * 8
        blk = 0
        while len(data) < need:
            o = shd['offset'] + blk * half * nch + c * half
            data += sbb[o:o + half]
            blk += 1
        # SND_SHD keeps a1 of the 8 predictor pairs in coef[0..7] and a2 in coef[8..15]
        # (snd_str3.cpp: adpcm.a[i] = {coef[i], coef[i + 8]}); dsp_decode wants the pairs
        # interleaved, as in a wavetable. Read as interleaved pairs, the filters are
        # unstable and the decoded stream saturates (issue lamb2k/re4dc#15).
        sc = shd['coefs'][c]
        pairs = tuple(v for i in range(8) for v in (sc[i], sc[i + 8]))
        coef = (pairs, (0, 0, shd['yn1'][c] & 0xFFFF, shd['yn2'][c] & 0xFFFF, 0, 0, 0))
        chans.append(dsp_decode(bytes(data[:need]), 0, shd['samples'], coef, None))
    return chans


def yamaha_encode_state(x, pred=0, step=127):
    """yamaha_encode with an explicit start state; returns (bytes, end pred, end step)."""
    nibs = []
    app = nibs.append
    for v in x:
        d = v - pred
        neg = d < 0
        t = (-d if neg else d) << 2
        s = step
        if t >= s << 3:
            q = 7
        else:
            q = 0
            if t >= s << 2:
                q = 4
                t -= s << 2
            if t >= s << 1:
                q += 2
                t -= s << 1
            if t >= s:
                q += 1
        delta = (s * (2 * q + 1)) >> 3
        pred = pred - delta if neg else pred + delta
        pred = 32767 if pred > 32767 else (-32768 if pred < -32768 else pred)
        step = (step * SCALE[q]) >> 8
        step = 127 if step < 127 else (24576 if step > 24576 else step)
        app(q | (8 if neg else 0))
    if len(nibs) & 1:
        nibs.append(0)
    return bytes(nibs[i] | (nibs[i + 1] << 4) for i in range(0, len(nibs), 2)), pred, step


def interleave(chans):
    n = max(len(c) for c in chans)
    blocks = (n + STR_BLOCK - 1) // STR_BLOCK
    out = bytearray()
    for b in range(blocks):
        for c in chans:
            part = c[b * STR_BLOCK:(b + 1) * STR_BLOCK]
            out += part + bytes(STR_BLOCK - len(part))
    return bytes(out)


def build_streams(mirror, out, keys):
    shds = stream_headers(mirror)
    sbbs = {}
    ents, blobs, report = [], [], []
    # header: 16 + 32 x count bytes in whole 2 KB sectors (one sector up to 63 entries; more need AICA_STR_ENT_MAX > 63)
    hsz = max(STR_BLOCK, (16 + STR_ENT.size * len(keys) + STR_BLOCK - 1) // STR_BLOCK * STR_BLOCK)
    pos = hsz
    for key in keys:
        shd = shds[key]
        if key[0] not in sbbs:
            with open(os.path.join(mirror, STREAM_FILES[key[0]]), 'rb') as f:
                sbbs[key[0]] = f.read()
        chans = decode_stream(sbbs[key[0]], shd)
        loops = bool(shd['flag'] & 4)          # the driver loops (str_ax_voice_loop_to_top) on 0x4
        # intro and loop lengths in whole 4-byte ADPCM words (8 samples): every ring write
        # is then G2-aligned; moves the loop point by < 8 samples (0.25 ms)
        end = shd['samples'] & ~7
        ls = (end - ((end - nibble_to_sample(shd['loop'])) & ~7)) if loops else 0
        A, B, seam = [], [], []
        for pcm in chans:
            a, p, s = yamaha_encode_state(pcm[:end])
            A.append(a)
            if loops:
                # the loop body starts from the decoder state it really has at the jump:
                # its own end state, iterated to a fixed point, so every pass is seamless
                bp, bs = p, s
                b = b''
                for _ in range(6):
                    b, p2, s2 = yamaha_encode_state(pcm[ls:end], bp, bs)
                    if (p2, s2) == (bp, bs):
                        break
                    bp, bs = p2, s2
                B.append(b)
                seam.append('A end (%d,%d) loop start (%d,%d)' % (p, s, bp, bs))
        a_data = interleave(A)
        b_data = interleave(B) if loops else b''
        a_ofs = pos
        pos += len(a_data)
        b_ofs = pos if loops else 0
        pos += len(b_data)
        ents.append(STR_ENT.pack(shd['offset'], shd['rate'], (1 if loops else 0) | key[0] << 8 | key[1] << 16, len(chans), end,
                                 (end - ls) if loops else 0, a_ofs, b_ofs))
        blobs += [a_data, b_data]
        report.append({'stream': '%d:%d' % key, 'sbb_offset': shd['offset'], 'seconds': round(end / shd['rate'], 2),
                       'loop_from_s': round(ls / shd['rate'], 2) if loops else None, 'channels': len(chans),
                       'bytes': len(a_data) + len(b_data), 'seam': seam})
        print('  stream %d:%d  %.1f s %s, %d bytes  %s' % (key[0], key[1], end / shd['rate'],
              ('loop from %.2f s' % (ls / shd['rate'])) if loops else 'one-shot', len(a_data) + len(b_data),
              '; '.join(seam)))
    hdr = struct.pack('<4I', STR_MAGIC, len(ents), 0, 0) + b''.join(ents)
    assert len(hdr) <= hsz
    dst = os.path.join(out, 'bgm', 'aica_str.dat')
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    with open(dst, 'wb') as f:
        f.write(hdr + bytes(hsz - len(hdr)))
        for b in blobs:
            f.write(b)
    return report


STREAM_VERSION = 3   # bump when build_streams output changes


def cached_streams(mirror, out, keys, cache_dir):
    """build_streams, reusing bgm/aica_str.dat from `cache_dir` when its inputs are unchanged."""
    h = hashlib.sha1(b'%d %r ' % (STREAM_VERSION, keys))
    with open(os.path.join(mirror, 'bgm', 'bio4str.hed'), 'rb') as f:
        h.update(f.read())
    for blk in sorted({k[0] for k in keys}):
        st = os.stat(os.path.join(mirror, STREAM_FILES[blk]))
        h.update(b'%d %d %d ' % (blk, st.st_size, st.st_mtime_ns))
    cached = os.path.join(cache_dir, 'streams-%s.dat' % h.hexdigest()[:20])
    dst = os.path.join(out, 'bgm', 'aica_str.dat')
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    if not os.path.exists(cached):
        tmp = os.path.join(cache_dir, 'streams-tmp')
        os.makedirs(tmp, exist_ok=True)
        build_streams(mirror, tmp, keys)
        os.makedirs(cache_dir, exist_ok=True)
        os.replace(os.path.join(tmp, 'bgm', 'aica_str.dat'), cached)
    else:
        print('  streams: cached %s' % os.path.basename(cached))
    os.link(cached, dst)


def disc(mirror, out, cache_dir, rooms, keys, json_out, weapons=()):
    """A disc data directory: the mirror hardlinked, route banks converted, disc streams added."""
    import shutil
    import tempfile
    if os.path.exists(out):
        raise SystemExit(out + ' exists')
    os.makedirs(cache_dir, exist_ok=True)
    budget = AICA_POOL - MOVIE_RESERVE - STREAM_RING
    res, per_room, uniq, slots, arena = plan(mirror, rooms, budget, weapons=weapons)
    rep = report(res, per_room, uniq, slots, arena, budget)
    # AICA RAM at run time: the layout plus the stream ring; what stays free must
    # cover the movie reserve (snd_stream, agreed with the cutscene audio). plan()
    # already sizes the layout against pool - reserve - ring; this is the hard check.
    used = rep['layout_total'] + STREAM_RING
    free = AICA_POOL - used
    if free < MOVIE_RESERVE:
        raise SystemExit('aica: layout %d + stream ring %d leaves %d bytes free, below the %d byte movie reserve'
                         % (rep['layout_total'], STREAM_RING, free, MOVIE_RESERVE))
    overlay = tempfile.mkdtemp(prefix='aica-overlay.', dir=cache_dir)
    try:
        rep['overlay'] = build(mirror, overlay, res, per_room, uniq, slots, os.path.join(cache_dir, 'banks'), False,
                               weapons)
        cached_streams(mirror, overlay, keys, cache_dir)
        merge(mirror, overlay, out)
    finally:
        shutil.rmtree(overlay, ignore_errors=True)
    if json_out:
        with open(json_out, 'w') as f:
            json.dump(rep, f, indent=1)
    print('aica: AICA RAM %d of %d (layout %d + stream ring %d), free %d = movie reserve %d + spare %d; '
          '%d banks rewritten, %d streams' % (used, AICA_POOL, rep['layout_total'], STREAM_RING, free, MOVIE_RESERVE,
                                              free - MOVIE_RESERVE, sum(n for _, n in rep['overlay']), len(keys)))


def tree_layout(tree):
    """The frozen route layout (slot bytes 0..8) from the prebuilt resident banks of a disc tree."""
    for spec in RESIDENT:
        path, bases = archive_bases(tree, spec)
        if not os.path.exists(path):
            continue
        d = open(path, 'rb').read()
        for base in bases:
            for (t, mo, ms, ao, asz) in sound_blocks(d, base) or []:
                if struct.unpack_from('<I', d, ao)[0] == MAGIC:
                    return list(HDR.unpack_from(d, ao)[9:18])
    raise SystemExit('fit: no prebuilt resident bank in %s (no frozen layout)' % tree)


def fit(path_in, path_out, tree, room, cache_dir, check=False, json_out=None, tail_blk=None, tail_bytes=0):
    """Prebuild the room-arena banks (ROOM, FOOT, enemies) that a disc file still carries as GC data, into the frozen
    layout of an existing disc tree (lane audio16, 2026-10-16: test 13's objs13 st1/r103.dar was rebuilt from an
    unconverted .dar, so r103's ROOM / FOOT banks went to runtime conversion, which only has the ~30 KB outside the
    layout: "blk 6 / blk 5 does not fit", footsteps and ambience silent). The room's other arena banks are read from
    `tree` as prebuilt there (ROOMS[room]); the free arena is layout[8] minus their bytes. Each block starts at
    pref_cap and the planner's LOWER_ORDER steps one cap down on the largest block of the first kind that can still go
    down until all fit. Same image, header and filter as `build` (decimate_aa, AicaBankHeader with the tree's layout);
    every other byte of the file is kept.
    tail_blk / tail_bytes (--tail-blk T --tail-bytes N, lane ch2rooms20, ROUTE_CH21_FULL images): block T of the file is
    marked tail-first (header pad bit 0) and placed by the runtime in the BGM0 slot's unused tail (N bytes = the slot
    minus the room's BGM0 bank) instead of the arena, so it is left out of the arena budget and must fit N."""
    layout = tree_layout(tree)
    d = bytearray(open(path_in, 'rb').read())
    me = [s for s in ROOMS[room] if not s.partition('#')[0].endswith(os.path.basename(path_in))]
    others, runtime_others = 0, []
    for spec in me:
        p, bases = archive_bases(tree, spec)
        if not os.path.exists(p):
            raise SystemExit('fit: %s not in %s' % (spec, tree))
        od = open(p, 'rb').read()
        for base in bases:
            for (t, mo, ms, ao, asz) in sound_blocks(od, base) or []:
                if slot_of(t) != 8:
                    continue
                if struct.unpack_from('<I', od, ao)[0] == MAGIC:
                    h = HDR.unpack_from(od, ao)
                    if list(h[9:18]) != layout:
                        raise SystemExit('fit: %s was built for another layout' % spec)
                    others += (h[3] + 31) & ~31
                else:
                    runtime_others.append(spec)
    todo = []
    for (t, mo, ms, ao, asz) in sound_blocks(bytes(d), 0) or []:
        if slot_of(t) != 8 or struct.unpack_from('<I', d, ao)[0] == MAGIC:
            continue
        table, samples, coefs = wavetable(bytes(d), t, mo, ms)
        if samples:
            todo.append(dict(t=t, mo=mo, ms=ms, ao=ao, asz=asz, samples=samples, coefs=coefs, fnv=fnv1a(table),
                             cap=pref_cap(t)))
    free = layout[8] - others

    def need():
        return sum((bank_bytes(b['samples'], b['cap']) + 31) & ~31 for b in todo if b['t'] != tail_blk)
    for b in todo:
        if b['t'] == tail_blk:
            while (bank_bytes(b['samples'], b['cap']) + 31) & ~31 > tail_bytes:
                if b['cap'] == CAPS[-1]:
                    raise SystemExit('fit: tail block %d needs %d bytes even at %d Hz, tail %d'
                                     % (tail_blk, bank_bytes(b['samples'], b['cap']), CAPS[-1], tail_bytes))
                b['cap'] = CAPS[CAPS.index(b['cap']) + 1]
    if tail_blk is not None and not any(b['t'] == tail_blk for b in todo):
        raise SystemExit('fit: --tail-blk %d is not a GC arena block of %s' % (tail_blk, path_in))
    while need() > free:
        for kind in LOWER_ORDER:
            c = [b for b in todo if (b['t'] if b['t'] < 8 else 8) == kind and b['cap'] > CAPS[-1] and b['t'] != tail_blk]
            if c:
                b = max(c, key=lambda x: bank_bytes(x['samples'], x['cap']))
                b['cap'] = CAPS[CAPS.index(b['cap']) + 1]
                break
        else:
            raise SystemExit('fit: %s needs %d arena bytes even at %d Hz, %d free' % (path_in, need(), CAPS[-1], free))
    rows = []
    for b in todo:
        loops = sample_loops(bytes(d), b['t'], b['mo'], b['ms'], len(b['samples']))
        img, worst = cached_convert(cache_dir, bytes(d[b['ao']:b['ao'] + b['asz']]), b['samples'], b['coefs'], b['cap'],
                                    check, loops)
        assert len(img) == bank_bytes(b['samples'], b['cap'])
        blob = HDR.pack(MAGIC, VERSION, b['cap'], len(img), len(b['samples']), b['fnv'], b['asz'], slot_of(b['t']),
                        1 if b['t'] == tail_blk else 0, *layout, *([0] * 7)) + img
        assert len(blob) <= b['asz'], (b['t'], len(blob), b['asz'])
        d[b['ao']:b['ao'] + b['asz']] = blob + bytes(b['asz'] - len(blob))
        rows.append({'block': BLOCK_NAMES.get(b['t'], 'EM%d' % (b['t'] - 8)), 'gc_bytes': b['asz'],
                     'samples': len(b['samples']), 'cap_hz': b['cap'], 'aica_bytes': len(img),
                     'aica_at_pref_cap': bank_bytes(b['samples'], pref_cap(b['t'])), 'fnv': '%08x' % fnv1a(img),
                     'adpcm_snr_db': None if worst > 900 else round(worst, 1), 'tail_first': b['t'] == tail_blk})
        print('  %s %-4s %7d GC -> %7d AICA at %5d Hz%s' % (os.path.basename(path_in), rows[-1]['block'], b['asz'],
              len(img), b['cap'], '' if worst > 900 else '  ADPCM SNR %.1f dB' % worst))
    os.makedirs(os.path.dirname(os.path.abspath(path_out)), exist_ok=True)
    with open(path_out, 'wb') as f:
        f.write(d)
    rep = {'room': room, 'file': path_in, 'out': path_out, 'sha256': hashlib.sha256(bytes(d)).hexdigest(),
           'layout': layout, 'arena': layout[8], 'other_arena_bytes': others, 'runtime_other_banks': runtime_others,
           'free_before': free, 'used_by_fit': need(), 'arena_left': free - need(), 'blocks': rows,
           'tail_blk': tail_blk, 'tail_bytes': tail_bytes}
    if json_out:
        with open(json_out, 'w') as f:
            json.dump(rep, f, indent=1)
    print('fit %s: arena %d = others %d + these %d + left %d%s' % (room, layout[8], others, need(), free - need(),
          ('; runtime (outside the arena): ' + ', '.join(runtime_others)) if runtime_others else ''))
    return rep


def fit_wep(path_in, path_out, tree, cache_dir, check=False, json_out=None):
    """Prebuild a weapon file's GC WEP block (block 2) into the frozen WEP slot of an existing disc tree (lane snd28,
    2026-10-28, issue #1 round 2): the same rule as plan()'s WEAPONS (the highest cap <= pref_cap(2) whose image fits
    layout[2]); same image, header and filter as `build` / `fit`; every other byte of the file is kept. For a weapon
    file a data set already rewrote (wep24 models), so the release recipe's banks need no full rebuild."""
    layout = tree_layout(tree)
    d = bytearray(open(path_in, 'rb').read())
    rows = []
    for (t, mo, ms, ao, asz) in sound_blocks(bytes(d), 0) or []:
        if t != 2 or struct.unpack_from('<I', d, ao)[0] == MAGIC:
            continue
        table, samples, coefs = wavetable(bytes(d), t, mo, ms)
        fits = [c for c in CAPS if c <= pref_cap(2) and ((bank_bytes(samples, c) + 31) & ~31) <= layout[2]]
        if not fits:
            raise SystemExit('fitwep: %s does not fit the WEP slot (%d bytes) even at %d Hz' % (path_in, layout[2], CAPS[-1]))
        cap = fits[0]
        loops = sample_loops(bytes(d), t, mo, ms, len(samples))
        img, worst = cached_convert(cache_dir, bytes(d[ao:ao + asz]), samples, coefs, cap, check, loops)
        assert len(img) == bank_bytes(samples, cap)
        blob = HDR.pack(MAGIC, VERSION, cap, len(img), len(samples), fnv1a(table), asz, slot_of(t), 0, *layout,
                        *([0] * 7)) + img
        assert len(blob) <= asz, (t, len(blob), asz)
        d[ao:ao + asz] = blob + bytes(asz - len(blob))
        rows.append({'block': 'WEP', 'gc_bytes': asz, 'samples': len(samples), 'cap_hz': cap, 'aica_bytes': len(img),
                     'wep_slot': layout[2], 'max_src_rate': max(s[1] for s in samples),
                     'adpcm_snr_db': None if worst > 900 else round(worst, 1)})
        print('  %s WEP %7d GC -> %7d AICA at %5d Hz (slot %d)' % (os.path.basename(path_in), asz, len(img), cap, layout[2]))
    if not rows:
        raise SystemExit('fitwep: %s has no GC WEP block' % path_in)
    os.makedirs(os.path.dirname(os.path.abspath(path_out)), exist_ok=True)
    with open(path_out, 'wb') as f:
        f.write(d)
    if json_out:
        with open(json_out, 'w') as f:
            json.dump({'file': path_in, 'layout': layout, 'blocks': rows}, f, indent=1)
    return rows


BANK_EXTS = ('.dar', '.drs', '.das', '.snd', '.dat')


def file_bases(root, rel):
    """Archive bases of a disc / mirror file: container entries for bio4midi.dat / doorse.dat, else [0]."""
    if rel.endswith('bio4midi.dat') or rel.endswith('doorse.dat'):
        return archive_bases(root, rel + '#*')[1]
    return [0]


def reconvert(root, mirrors, out, cache_dir, json_out=None, only=None):
    """Re-run the decimation of every prebuilt bank already on a disc tree with the current filter, keeping
    each AicaBankHeader (cap, sizes, slot, layout) and the image size exactly. The GC sample data comes from
    the unconverted mirror(s) (same path, block found by wavetable hash + part size). Proof of identical inputs:
    the box conversion (filter 1) of that source must reproduce the disc's image byte for byte, else the file
    is reported and left alone. Writes only changed files to `out` (relative paths)."""
    rep = {'filter_version': FILTER_VERSION, 'files': [], 'refused': []}
    for dirpath, dirs, files in os.walk(root):
        dirs.sort()
        for fn in sorted(files):
            if not fn.endswith(BANK_EXTS):
                continue
            rel = os.path.relpath(os.path.join(dirpath, fn), root)
            if only and rel not in only:
                continue
            with open(os.path.join(root, rel), 'rb') as f:
                d = bytearray(f.read())
            try:
                bases = file_bases(root, rel)
            except (OSError, ValueError, struct.error):
                continue
            todo = []
            for base in bases:
                for (t, mo, ms, ao, asz) in (sound_blocks(bytes(d), base) or []):
                    if ao + HDR_SIZE <= len(d) and struct.unpack_from('<I', d, ao)[0] == MAGIC:
                        todo.append((t, mo, ms, ao, asz))
            if not todo:
                continue
            src_blocks = None
            for m in mirrors:
                p = os.path.join(m, rel)
                if not os.path.exists(p):
                    continue
                with open(p, 'rb') as f:
                    md = f.read()
                blk = {}
                try:
                    mb = file_bases(m, rel)
                except (OSError, ValueError, struct.error):
                    continue
                for base in mb:
                    for (t, mo2, ms2, ao2, asz2) in (sound_blocks(md, base) or []):
                        if struct.unpack_from('<I', md, ao2)[0] == MAGIC:
                            continue
                        table, samples, coefs = wavetable(md, t, mo2, ms2)
                        blk.setdefault((fnv1a(table), asz2), md[ao2:ao2 + asz2])
                need = set()
                for (t, mo, ms, ao, asz) in todo:
                    table, _, _ = wavetable(bytes(d), t, mo, ms)
                    need.add((fnv1a(table), asz))
                if need <= set(blk):
                    src_blocks = (m, blk)
                    break
            if src_blocks is None:
                rep['refused'].append({'file': rel, 'why': 'no mirror holds the GC source of every block'})
                print('  %s: REFUSED (no mirror source)' % rel)
                continue
            n_new, ok = 0, True
            rows = []
            for (t, mo, ms, ao, asz) in todo:
                h = HDR.unpack_from(d, ao)
                cap, total, nsmp, fnv = h[2], h[3], h[4], h[5]
                table, samples, coefs = wavetable(bytes(d), t, mo, ms)
                gc = src_blocks[1][(fnv1a(table), asz)]
                if fnv != fnv1a(table) or nsmp != len(samples):
                    ok = False
                    rows.append({'aram_ofs': ao, 'why': 'header does not match the wavetable'})
                    break
                old, _ = cached_convert(cache_dir, gc, samples, coefs, cap, False, None, 1)
                cur = bytes(d[ao + HDR_SIZE:ao + HDR_SIZE + total])
                if len(old) != total or old != cur:
                    ok = False
                    rows.append({'aram_ofs': ao, 'why': 'box conversion of the mirror source differs from the disc image'})
                    break
                loops = sample_loops(bytes(d), t, mo, ms, len(samples))
                new, _ = cached_convert(cache_dir, gc, samples, coefs, cap, False, loops)
                assert len(new) == total, (rel, ao, len(new), total)
                d[ao + HDR_SIZE:ao + HDR_SIZE + total] = new
                n_new += 1
                rows.append({'aram_ofs': ao, 'block': BLOCK_NAMES.get(t, 'EM%d' % (t - 8)), 'cap_hz': cap,
                             'image_bytes': total, 'samples': len(samples), 'loops': len(loops),
                             'box_fnv': '%08x' % fnv1a(old), 'aa_fnv': '%08x' % fnv1a(new)})
            if not ok:
                rep['refused'].append({'file': rel, 'blocks': rows})
                print('  %s: REFUSED %s' % (rel, rows[-1]['why']))
                continue
            dst = os.path.join(out, rel)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            with open(dst, 'wb') as f:
                f.write(d)
            rep['files'].append({'file': rel, 'mirror': src_blocks[0], 'blocks': rows,
                                 'sha256': hashlib.sha256(bytes(d)).hexdigest()})
            print('  %s: %d banks refiltered (mirror %s)' % (rel, n_new, src_blocks[0]))
    if json_out:
        with open(json_out, 'w') as f:
            json.dump(rep, f, indent=1)
    return rep


def merge(mirror, overlay, out):
    """Hardlink `mirror` into `out` (no data copied), then link the overlay files over it."""
    if os.path.exists(out):
        raise SystemExit(out + ' exists')
    n = 0
    for root, dirs, files in os.walk(mirror):
        rel = os.path.relpath(root, mirror)
        os.makedirs(os.path.join(out, rel), exist_ok=True)
        for f in files:
            os.link(os.path.join(root, f), os.path.join(out, rel, f))
    for root, dirs, files in os.walk(overlay):
        rel = os.path.relpath(root, overlay)
        for f in files:
            dst = os.path.join(out, rel, f)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            if os.path.exists(dst):
                os.unlink(dst)
            os.link(os.path.join(root, f), dst)
            n += 1
    print('merged %s + %d overlay files -> %s' % (mirror, n, out))


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    ap.add_argument('cmd', choices=('plan', 'build', 'merge', 'streams', 'disc', 'reconvert', 'fit', 'fitwep'))
    ap.add_argument('--file', help='fit: the disc file whose GC room-arena banks are prebuilt (e.g. a rebuilt st1/r103.dar)')
    ap.add_argument('--room', help='fit: the ROOMS entry whose other arena banks share the arena')
    ap.add_argument('--tail-blk', type=int, help='fit: mark this block tail-first (BGM0 slot tail; ROUTE_CH21_FULL)')
    ap.add_argument('--tail-bytes', type=int, default=0, help='fit: bytes free in the BGM0 slot tail for --tail-blk')
    ap.add_argument('--root', help='reconvert: a disc data tree whose prebuilt banks are refiltered '
                    '(--mirror may list several unconverted mirrors, comma separated, tried in order)')
    ap.add_argument('--streams', default=','.join('%d:%d' % k for k in ROUTE_STREAMS), help='blk:no list, or a preset name: ' + ', '.join(sorted(STREAM_PRESETS)))
    ap.add_argument('--call-voices', action='store_true',
                    help='add CALL_VOICE_STREAMS (the radio call voices) to --streams')
    ap.add_argument('--overlay')
    ap.add_argument('--mirror', required=True)
    ap.add_argument('--out')
    ap.add_argument('--route', default='title,r100,r101,r103')
    ap.add_argument('--fixed-route', default='', help='plan/build: rooms of --route whose caps and layout stay as '
                    'planned alone (e.g. title,r100,r101,r103); the rest fit that layout with their own banks. '
                    '";" separates nested levels: "title,r100,r101,r103;title,...,r11c" freezes the 2-2 route as '
                    'planned on the first level, then fits the remaining rooms')
    ap.add_argument('--weapons', action='store_true', help='plan/build/disc: also prebuild WEAPONS (Leon\'s other '
                    'stage-1 weapons) into the WEP slot, each at the highest cap that fits it; the layout is unchanged')
    ap.add_argument('--cache')
    ap.add_argument('--json')
    ap.add_argument('--check', action='store_true', help='decode the AICA output and report SNR')
    a = ap.parse_args()
    if a.streams in STREAM_PRESETS:   # a named list (ch21: the chapter 2-1 play disc), call voices included
        a.streams = ','.join('%d:%d' % k for k in STREAM_PRESETS[a.streams])
    if a.call_voices:
        a.streams = ','.join([k for k in a.streams.split(',') if k] + ['%d:%d' % k for k in CALL_VOICE_STREAMS])
    if a.cmd == 'merge':
        return merge(a.mirror, a.overlay, a.out)
    if a.cmd == 'fit':   # --mirror = the disc tree whose layout and other room banks are used
        if not (a.file and a.out and a.room):
            raise SystemExit('fit needs --file, --room and --out')
        fit(a.file, a.out, a.mirror, a.room, a.cache, a.check, a.json, a.tail_blk, a.tail_bytes)
        return 0
    if a.cmd == 'fitwep':   # --mirror = the disc tree whose frozen layout (WEP slot) is used
        if not (a.file and a.out):
            raise SystemExit('fitwep needs --file and --out')
        fit_wep(a.file, a.out, a.mirror, a.cache, a.check, a.json)
        return 0
    if a.cmd == 'reconvert':
        if not (a.root and a.out):
            raise SystemExit('reconvert needs --root and --out')
        rep = reconvert(a.root, [m for m in a.mirror.split(',') if m], a.out, a.cache, a.json)
        print('reconvert: %d files refiltered, %d refused' % (len(rep['files']), len(rep['refused'])))
        return 1 if rep['refused'] else 0
    if a.cmd == 'disc':
        if not (a.out and a.cache):
            raise SystemExit('disc needs --out and --cache')
        keys = [tuple(int(x) for x in k.split(':')) for k in a.streams.split(',') if k]
        return disc(a.mirror, a.out, a.cache, [r for r in a.route.split(',') if r], keys, a.json,
                    WEAPONS if a.weapons else ())
    if a.cmd == 'streams':
        keys = [tuple(int(x) for x in k.split(':')) for k in a.streams.split(',') if k]
        rep = build_streams(a.mirror, a.out, keys)
        if a.json:
            open(a.json, 'w').write(json.dumps(rep, indent=1) + '\n')
        return
    rooms = [r for r in a.route.split(',') if r]
    budget = AICA_POOL - MOVIE_RESERVE - STREAM_RING
    # 'a,b;a,b,c,d': nested freeze levels (each level's rooms planned on the levels before it); one level = as before
    fixed = [[r for r in lv.split(',') if r] for lv in a.fixed_route.split(';') if lv.strip(',')]
    assert all(set(lv) <= set(rooms) for lv in fixed), 'every --fixed-route room must be in --route'
    fixed = fixed[0] if len(fixed) == 1 else fixed
    weapons = WEAPONS if a.weapons else ()
    res, per_room, uniq, slots, arena = plan(a.mirror, rooms, budget, fixed, weapons)
    rep = report(res, per_room, uniq, slots, arena, budget)
    if a.cmd == 'build':
        if not a.out:
            raise SystemExit('build needs --out')
        rep['overlay'] = build(a.mirror, a.out, res, per_room, uniq, slots, a.cache, a.check, weapons)
    txt = json.dumps(rep, indent=1)
    if a.json:
        open(a.json, 'w').write(txt + '\n')
    print('layout %s = %d of %d bytes (headroom %d)' % (rep['slots'], rep['layout_total'], budget, rep['headroom']))
    for r, v in rep['rooms'].items():
        print('  %s: resident %d + arena %d = %d  [%s]' % (r, v['resident_bytes'], v['arena_bytes'], v['total_bytes'],
              ', '.join('%s %d@%d' % (x['bank'], x['aica_bytes'], x['cap_hz']) for x in v['banks'])))
    if 'weapons' in rep:
        print('  WEP slot %d: %s' % (rep['slots'].get('WEP', 0), ', '.join('%s %d@%d' % (x['bank'], x['aica_bytes'],
              x['cap_hz']) for x in rep['weapons'])))


if __name__ == '__main__':
    main()
