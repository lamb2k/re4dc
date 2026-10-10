#!/usr/bin/env python3
"""D367 test warp rig: write /cd/dc/warp.txt for a DBG_WARP=1 test build (README "Warp rig").

    warp.py list
    warp.py <preset> [--door] [--dump] [-o <fixtures-dir>/warp.txt]
    warp.py --room 0x100 --pos X Y Z --dir 0x8000 [--rsf ROOM:BIT,BIT] [--scenario 0:HEX] ... -o F

Each preset is a start point on the opening route with the scenario state its event needs,
derived from the room scripts (src/st1/r100.cpp, r101.cpp) and noted per preset. --door adds
the preset's door-test actions (step forward / press A at the door). A warp start is not STRICT
against continued play: use it for iteration and bring-up, and normal runs for logic proofs.
"""
import argparse
import sys

# Room save flag bits (RsfSet(G_ROOM_ID, n)) of r100 (src/st1/r100.cpp):
#   0 area 6 reached (s03/s20 preloads)   1 areas 7/8 reached   3 s03 done (the look at the house)
#   4 ambush over (gate door normal)      10 s20 done (officers dead: after state, ambush set)
#   12 battle streams faded               13 room entry event done (s40 + radio call)
#   14 ravine event done                  15 house Ganado event done
R100_AFTER_S03_S20 = [0, 1, 3, 10, 13]
# ESL entries r101's bell (r101_Event30) sets dead: the villagers who leave for the church.
R101_BELL_DEAD = [0x14, 0x15, 0x16, 0x17, 0x18, 0x19, 0x1A, 0x1B, 0x1C, 0x1E, 0x1F, 0x22, 0x23, 0x24, 0x28, 0x29,
                  0x2A, 0x2B, 0x2C, 0x2E, 0x2F, 0x30, 0x31, 0x32, 0x36, 0x37, 0x38, 0x39, 0x3A, 0x3C, 0x3D, 0x3E,
                  0x3F, 0x40, 0x41, 0x42, 0x43, 0x44, 0x45, 0x46]
PRESETS = {
    # r100 fresh entry: R100Init runs r100_StartEvent (s40 movie, then the radio call) because
    # room flag 13 is clear; the event itself places Leon at the gate (-99685,-484,-1343).
    "r100-spawn": dict(room=0x100, notes="fresh r100 entry: s40 + radio call run (flag 13 clear)"),
    # After the radio call: flag 13 set (the re-entry path skips r100_StartEvent), Leon where
    # r100_StartEvent leaves him (pos/ang from the source), s40 marked done (Scenario[0] 0x10).
    "r100-post-radio": dict(room=0x100, pos=(-99685, -484, -1343), ang=2.246, rsf={0x100: [13]},
                             scenario={0: 0x10}, notes="after s40 + radio call, at the gate"),
    # Before s03: flags 3/10 clear (area 0xA armed with r100_Sce_look), 13 set. Leon on the path
    # before the house; --door steps him into area 0xA.
    "r100-house-door": dict(room=0x100, pos=(-82910, 860, -38480), ang=-0.1293, rsf={0x100: [13]}, scenario={0: 0x10},
                            door=[("fwd", 30, 150)], notes="just before s03 (area 0xA armed: flags 3/10 clear)"),
    # s20 (the truck) and the ambush: r100-house-door with its door act always on (fwd -> area 0xA ->
    # r100_Sce_look -> s03, movie 0x10003), then `kill` shoots the s03 Ganado (id 0x12, R100Init's
    # EmSetEvent with the r100_Sce_zombi_dead death link) dead from room frame 400 (room frames stop
    # while a movie owns the frame, so this is after s03). Its death runs r100_Sce_zombi_dead as in
    # play: r100_em_set (the ambush), s20 (movie 0x10020), the after state, the post-house call
    # (OpeSetOpenTerm(1), stream 1:3).
    "r100-s20": dict(room=0x100, pos=(-82910, 860, -38480), ang=-0.1293, rsf={0x100: [13]}, scenario={0: 0x10},
                     acts=[("fwd", 30, 150)], kill=(0x12, 400, 0x100),
                     notes="s03, then the s03 Ganado killed at room frame 400: s20 + the ambush + the call"),
    # The same s20 path from a fresh r100 entry, as the route reaches it: s40 (movie 0x10040) and the
    # first radio call run first (close the call with a padscript: A every 90 vbl from vbl 1800,
    # README "Warp rig"), then `goto` puts Leon into area 6 (R100Main pre-reads s03/s20, room flag 0)
    # and into area 0xA (r100_Sce_look -> s03), and the s03 Ganado is shot dead from room frame 700.
    "r100-s20-route": dict(room=0x100, goto=[(400, (-86558, 0, -1243)), (460, (-83382, 1100, -34851))],
                           kill=(0x12, 700, 0x100),
                           notes="fresh r100 (s40 + call), areas 6 and 0xA, s03 Ganado killed: s20 + ambush + call"),
    # s44 (r100_EventBrige, area 0x1B, readEvent(8) = r100s44): only while flag 10 is clear.
    "r100-bridge": dict(room=0x100, pos=(-112251, -193, -4420), ang=-1.5172, rsf={0x100: [13]}, scenario={0: 0x10},
                        door=[("fwd", 30, 90)], notes="just before s44 (area 0x1B, flag 10 clear)"),
    # The r101 door with the after state (s03 + s20 done, ambush over): the gate door watcher
    # (r100_DoorCk) is normal once flags 3 and 4 are set.
    # The r100 -> r101 door (AEV area 0: DOOR -> r101, action button, no lock). Leon stands where
    # r101's door back to r100 puts him (r101 AEV no 0 dstPos/dstAngle), turned to face the door.
    # The door has no flag condition; the room is entered in the post-radio state.
    "r100-east-door": dict(room=0x100, pos=(96523, -6771, -8536), ang=2.247, rsf={0x100: [13]},
                           scenario={0: 0x10}, door=[("fwd", 30, 20), ("a", 60, 4), ("a", 150, 4), ("a", 240, 4)],
                           notes="at the r100 -> r101 door (door area 0 has no lock or flag)"),
    # The same door in the natural after state (s03 + s20 done, ambush over). Entering r100 with
    # flag 10 set spawns em2a (traps): linked since e6f65cc (was HALT main_sub.cpp(1440), warp-east-1).
    # The crow archive (em23) does not fit heap 4 in this state with Original packages.
    "r100-east-door-after": dict(room=0x100, pos=(96523, -6771, -8536), ang=2.247,
                                 rsf={0x100: R100_AFTER_S03_S20 + [4, 12, 14, 15]}, scenario={0: 0x10}, find=0x4000,
                                 door=[("fwd", 30, 20), ("a", 60, 4), ("a", 150, 4), ("a", 240, 4)],
                                 notes="r101 door, after state (crows absent: heap 4)"),
    # r101 fresh entry (first visit: typewriter + Hunnigan call via r101_execOperator2).
    "r101-entry": dict(room=0x101, notes="fresh r101 entry (first visit, Item_find 0x2000 clear)"),
    # The square before the fight: first visit done (Item_find 0x2000: no typewriter call), fight
    # not started (flag 6 clear): r101_checkFindPlayer starts it when a Ganado finds Leon.
    # Leon at the square's examine point (AEV area 09), facing the square (area 0B). The bell
    # itself (s30) needs 15 kills or 11700 fight frames counted at run time (r101_checkEmNum):
    # not a flag state, so the preset stops at the fight start.
    "r101-bell-fight": dict(room=0x101, pos=(-7914, 0, -254), ang=2.96, find=0x2000,
                            notes="r101 square, fight about to start (flags 6/7 clear, first visit done)"),
    # The same fight, then the bell: `trg 0` makes the source's developer shortcut DebugTrg(0) fire in
    # r101_checkEmNum, which starts event 30 (bell, chapter title, r101s30) as 15 kills would. About
    # 1,000 fight frames with Ganados engaged come first (the fight starts ~150-250 frames in).
    "r101-bell": dict(room=0x101, pos=(-7914, 0, -254), ang=2.96, find=0x2000, trg=(0, 1200, 0x101),
                      notes="r101 square fight, bell forced at room frame 1200 (DebugTrg(0))"),
    # r101 after the bell, at the r103 door: room flag 7 (bell done) set and 10 (post-bell call) clear,
    # so R101Init runs r101_execOperator (radio term 2, stream 1:0x33) and installs no
    # r101_DoorDontOpen103 lock. Leon stands where r103's door back puts him (r103 AEV record 0,
    # angle -1.5038), turned to face the door, with the ESL entries the bell sets dead (R101_BELL_DEAD;
    # without them a Ganado grabs Leon at the door, warp-r101-pbdoor1). --door closes the call (A:
    # it closed on the first A at room frame 800 in pbdoor1; B did not), steps forward, presses A.
    "r101-post-bell-door": dict(room=0x101, pos=(39372, 3201, -26667), ang=1.6378, rsf={0x101: [6, 7]}, find=0x2000,
                                dead=R101_BELL_DEAD,
                                door=[("a", 700, 4), ("a", 820, 4), ("fwd", 940, 25), ("a", 980, 4),
                                      ("a", 1070, 4), ("a", 1160, 4), ("a", 1250, 4)],
                                notes="r101 after the bell at the r103 door (post-bell call runs first)"),
    # r103 as the r101 door delivers Leon (r101 AEV record 2: dst -47609.06, 11.83, 7083.56, angle
    # 1.889). r103 has no events and no story flags of its own on the route (design-r103 PLAN 1.1).
    "r103-entry": dict(room=0x103, pos=(-47609, 12, 7084), ang=1.889,
                       notes="r103 from the r101 door (5 Ganados, corpses, cows, chickens, dog)"),
    # The r103 -> r106 door (r103 AEV door 1, action button, no lock or flag). Leon stands where r106's
    # door back to r103 puts him (r106 AEV door 0: dst 9470, 38, -759, angle -2.301), turned to face the door.
    "r103-r106-door": dict(room=0x103, pos=(9470, 38, -759), ang=0.8406,
                           door=[("fwd", 30, 20), ("a", 60, 4), ("a", 150, 4), ("a", 240, 4)],
                           notes="at the r103 -> r106 door (door 1 has no lock or flag)"),
    # r106 as the r103 door delivers Leon (r103 AEV door 1: dst 11141, -893, -120, angle 0.839), before the
    # closet event (Item_find_flg 0x00200000 clear: area 2 arms r106s00, chapter 1-1's end).
    "r106-entry": dict(room=0x106, pos=(11141, -893, -120), ang=0.839,
                       notes="r106 from the r103 door (hall Ganados, the closet event ahead)"),
    # The closet event (r106 AEV area 2: action button, trigger 0x88, the box (157104,-45133)..(159344,-42698) at
    # floor -9246): Leon in the box centre, A pressed a few times; r106_Event -> r106s00 movie -> chapter 1-1 end.
    "r106-closet": dict(room=0x106, pos=(158150, -9246, -44000), ang=0.0,
                        door=[("a", 60, 4), ("a", 150, 4), ("a", 240, 4), ("a", 330, 4)],
                        notes="in the closet event area (r106s00, chapter 1-1 end)"),
    # r104 as the r106 door delivers Leon (r106 AEV door 3: dst -3443, 0, 12338, angle -1.581). rsf 0x104 bit 1 is
    # R104Init's own "arrival done" flag (its DebugTrg(1) path): the s00 arrival event (QTE) is skipped and the
    # kill-count waves / patrols start at once. Room bring-up only; the first visit plays s00 (preset r104-arrival).
    "r104-entry-noevt": dict(room=0x104, pos=(-3443, 0, 12338), ang=-1.581, rsf={0x104: [1]},
                             notes="r104 from the r106 door, arrival event done (room bring-up)"),
    "r104-arrival": dict(room=0x104, pos=(-3443, 0, 12338), ang=-1.581,
                         notes="r104 from the r106 door, first visit: the s00 arrival event and its QTE"),
    # r107 (the lake path) as r104's door 0 delivers Leon (r104 AEV door 0: dst 29683, -13, -28512, angle 2.286;
    # stage_route.py). r107 has no evd events; em12 / em27 (fish) / em2a from the ESL.
    "r107-entry": dict(room=0x107, pos=(29683, -13, -28512), ang=2.286,
                       notes="r107 from the r104 door (chapter 1-2)"),
    # r105 (the farm with Ashley's rescue) as r107's door 1 delivers Leon (r107 AEV door 1: dst 72778, -2238, -37465,
    # angle -1.226; stage_route.py). First visit: area 8 runs s00 (chapter 1-2's end).
    "r105-entry": dict(room=0x105, pos=(72778, -2238, -37465), ang=-1.226,
                       notes="r105 from the r107 door (chapter 1-2)"),
    # r105's s00 (chapter 1-2's end): R105Main arms area 8 (action button, centre 7580, 6020, 5506; warp --dump of
    # route-r105b) once the key item's item_flags[0] bit 0x20000000 is set (its pickup); Leon at the centre presses A.
    "r105-event": dict(room=0x105, pos=(7580, 6020, 5506), ang=0.0, items={0: 0x20000000},
                       door=[("a", 90, 4), ("a", 180, 4), ("a", 270, 4)],
                       notes="r105 area 8 with the key item: s00, then the chapter 1-2 end"),
    # *-front: area 8's check flag is 01 (the hit test uses the point in front of Leon, no angle check; r105e2 dump):
    # Leon 700 units short of the centre on z, facing +z (angle 0), so his front point is inside.
    "r105-event-front": dict(room=0x105, pos=(7580, 6020, 4806), ang=0.0, items={0: 0x20000000},
                             door=[("a", 90, 4), ("a", 180, 4), ("a", 270, 4)],
                             notes="r105 area 8 (front point) with the key item: s00, then the chapter 1-2 end"),
    # *-pi: the same spot facing angle pi (area 8 box x 7225..7935, z 4840..6137, floor 6020 + 1484: r105e4 dump; at
    # angle 0 from z 5506 / 5060 the front point never fired, so the front is taken to be -z at angle 0).
    "r105-event-pi": dict(room=0x105, pos=(7580, 6020, 5060), ang=3.1416, items={0: 0x20000000},
                          door=[("a", 90, 4), ("a", 180, 4), ("a", 270, 4)],
                          notes="r105 area 8 facing +z with the key item: s00, then the chapter 1-2 end"),
    # *-west: r105e1/e3/e5 all drifted to x ~7942 after placement (just east of the box's 7935 edge); the west half.
    "r105-event-west": dict(room=0x105, pos=(7400, 6020, 5500), ang=0.0, items={0: 0x20000000},
                            door=[("a", 90, 4), ("a", 180, 4), ("a", 270, 4)],
                            notes="r105 area 8 (west half) with the key item: s00, then the chapter 1-2 end"),
    # The r104 -> r107 door (r104 AEV door 0, action button, no lock or flag). Leon stands where r107's door back to
    # r104 puts him (r107 AEV door 0: dst 27604, -72, -27727, angle -1.139), turned to face the door (+pi); rsf 0x104
    # bit 1 skips the arrival event (as r104-entry-noevt).
    "r104-r107-door": dict(room=0x104, pos=(27604, -72, -27727), ang=2.0026, rsf={0x104: [1]},
                           door=[("fwd", 30, 20), ("a", 60, 4), ("a", 150, 4), ("a", 240, 4)],
                           notes="at the r104 -> r107 door (door 0 has no lock or flag)"),
    # *-unlocked: the emblem gate (door 0x97) opens once door_unlock[0] bit 0x00400000 is set (r104.cpp
    # r104_checkDoor107KeyUse, the combined emblem 0xA6 used); route-r104-r107-w1 without it showed "It won't open".
    "r104-r107-door-unlocked": dict(room=0x104, pos=(27604, -72, -27727), ang=2.0026, rsf={0x104: [1]},
                                    unlock={0: 0x00400000},
                                    door=[("fwd", 30, 20), ("a", 60, 4), ("a", 150, 4), ("a", 240, 4)],
                                    notes="at the r104 -> r107 emblem gate, unlocked"),
    # World coverage lane (St2 / St4 bring-up; needs WORLD_STAGE_MODULES=1). r210 (the minecart / lift room, st2_0)
    # as r206's door 7 delivers Leon (r206 AEV: dst -8, 0, -874, angle 2.979; stage_route.py --stage 2). A fresh
    # start (room_id_prev 0xFFF) sets Status_flg[3] 0x04000000, so R210Init brings Ashley along (SubCharInit).
    "r210-entry": dict(room=0x210, pos=(-8, 0, -874), ang=2.979,
                       notes="r210 from the r206 door (St2 minecart room, Ashley follows)"),
    # r210's own door 4 arrival (GC AEV, stage_route.scan) in the main hall, turned to face the balcony and the
    # chairs (the r210-entry spot faces a near wall).
    "r210-hall": dict(room=0x210, pos=(-19155, -2000, -7554), ang=-3.097,
                      notes="r210 main hall at the door 4 arrival, facing the balcony (view fixture)"),
    # r40c (St4, st4_0) as r40a's door 2 delivers Leon (r40a AEV: dst -2119, 0, 3158, angle 2.919; --stage 4).
    "r40c-entry": dict(room=0x40c, pos=(-2119, 0, 3158), ang=2.919,
                       notes="r40c from the r40a door (St4, omake00 list, no enemies)"),
    # Follow-up 6 (WORLD_ROOM_MODULES=1 also). r219 (St2, st2_2) as r201's door 33 delivers Leon (r201 AEV: dst 35, 0,
    # 1246, angle 3.069; stage_route.scan stage 2). emleon04 list, no enemy entries.
    "r219-entry": dict(room=0x219, pos=(35, 0, 1246), ang=3.069,
                       notes="r219 from the r201 door (St2, st2_2, no enemies)"),
    # r40a (St4, st4_0 + em1f) as r40c's door 0 delivers Leon (r40c AEV: dst -9910, 4001, 5434, angle -0.008).
    # omake00 list: 11 em1f entries (enabled later / script load).
    "r40a-entry": dict(room=0x40a, pos=(-9910, 4001, 5434), ang=-0.008,
                       notes="r40a from the r40c door (St4, em1f island soldiers)"),
    # Follow-up 7, St1 (stage_route.scan stage 1, GC AEV door arrivals; default flags, not the chapter's arrival
    # state). r109 as r108's door 1 delivers Leon: em23 list.
    "r109-entry": dict(room=0x109, pos=(97246, 2251, 13320), ang=1.0,
                       notes="r109 from the r108 door (St1, em23)"),
    # r10c as r10e's door 2 delivers Leon (em12 script load / spawn). Its AICA banks do not fit the frozen arena.
    "r10c-entry": dict(room=0x10c, pos=(27865, -15316, 43935), ang=2.418,
                       notes="r10c from the r10e door (St1, em12)"),
    # r10f as r11d's door 1 delivers Leon (em13 enabled later / entry / script spawn).
    "r10f-entry": dict(room=0x10f, pos=(-25133, 4000, 16399), ang=1.351,
                       notes="r10f from the r11d door (St1, em13)"),
    # r11a as r119's door 1 delivers Leon (em12).
    "r11a-entry": dict(room=0x11a, pos=(-58032, 7346, 69783), ang=1.362,
                       notes="r11a from the r119 door (St1, em12)"),
    # r118 (route lane r118, the church; ROUTE_CH21) as r119's door 0 delivers Leon (r119 AEV: dst 94554, 2258, 12986,
    # angle -1.842), before Ashley's rescue (Item_find_flg 0x00100000 clear: no enemies, the alternate layout).
    "r118-entry": dict(room=0x118, pos=(94554, 2258, 12986), ang=-1.842,
                       notes="r118 from the r119 door (St1, before the rescue: no enemies)"),
    # At r118's door 4 (to r117): r117 door 0's arrival in r118 (dst 23412, 12026, -26482, angle -1.422) turned to face
    # the door (+pi). *-unlocked sets door_unlock[0] 0x10000000 (r118_checkDoor117KeyUse after the key 0x3C is used),
    # so door 4 is a plain door (without it, R118Init hooks the locked-door message).
    "r118-door117-unlocked": dict(room=0x118, pos=(23412, 12026, -26482), ang=1.7196, unlock={0: 0x10000000},
                                  door=[("fwd", 30, 20), ("a", 60, 4), ("a", 150, 4), ("a", 240, 4)],
                                  notes="at the r118 -> r117 door, unlocked (r117 on CH21 discs from lane r117)"),
    # r117 (St1, the chapter 2-1 end; ROUTE_CH21) as r118's door 4 delivers Leon (r118 AEV: dst 169, -1000, 6073,
    # angle 2.922), before Ashley is found (Item_find 0x00100000 clear: door 0 locked, area 7 = the s00 event).
    "r117-entry": dict(room=0x117, pos=(169, -1000, 6073), ang=2.922,
                       notes="r117 from the r118 door 4 (before Ashley is found)"),
    # Upstairs at Ashley's door (area 7, centre 6202, 3998, -3927): A starts s00 (Ashley found, Playing Manual 3);
    # the goto then puts Leon in area 6 (centre -4476, -1037, 3169): s10 (Saddler) -> chapter 2-1 end + save.
    "r117-ashley": dict(room=0x117, pos=(6202, 3998, -3700), ang=3.1416,
                        acts=[("a", 30, 4)], goto=[(400, (-4476, -1037, 3169))],
                        notes="r117 at Ashley's door: s00, then area 6: s10 and the chapter 2-1 end"),
    # A revisit after Ashley is found (Part 0): door 0 open, ESL 0x50/0x51 (em11 Ganados) spawn.
    "r117-revisit": dict(room=0x117, pos=(80, -1000, 7800), ang=0.0, find=0x00100000,
                         door=[("a", 600, 6), ("a", 660, 6), ("a", 720, 6)],
                         notes="r117 revisit (Ashley found): em11 Ganados; --door: door 0 -> r118"),
    # r40b (St4, st4_0 + em1f) as r40a's door 1 delivers Leon (r40a AEV: dst 1749, 0, 4498, angle -1.801); r40b's
    # only door arrival.
    "r40b-entry": dict(room=0x40b, pos=(1749, 0, 4498), ang=-1.801,
                       notes="r40b from the r40a door (St4, em1f)"),
}


def lines_for(p, door=False, dump=False, name=None):
    out = []
    if name:
        out.append("name %s" % name)
    out.append("# %s" % p.get("notes", ""))
    out.append("room 0x%03x" % p["room"])
    if p.get("pos"):
        out.append("pos %d %d %d" % tuple(p["pos"]))
    if p.get("ang") is not None:
        out.append("ang %.4f" % p["ang"])
    for room, bits in sorted((p.get("rsf") or {}).items()):
        out.append("rsf 0x%03x %s" % (room, " ".join(str(b) for b in bits)))
    for i, v in sorted((p.get("scenario") or {}).items()):
        if v:
            out.append("scenario %d 0x%08x" % (i, v))
    if p.get("find"):
        out.append("find 0x%08x" % p["find"])
    for i, v in sorted((p.get("unlock") or {}).items()):
        out.append("unlock %d 0x%08x" % (i, v))
    for i, v in sorted((p.get("items") or {}).items()):
        out.append("items %d 0x%08x" % (i, v))
    dead = list(p.get("dead") or [])
    for i in range(0, len(dead), 10):   # the rig reads at most 12 tokens per line
        out.append("dead " + " ".join("0x%02x" % n for n in dead[i:i + 10]))
    out.append("inv default")
    acts = list(p.get("acts") or [])   # the preset's own actions: always on
    if door:
        acts += p.get("door", [])
    for kind, frame, hold in sorted(acts, key=lambda a: a[1]):
        out.append("act %d %s %d" % (frame, kind, hold))
    if p.get("trg"):
        no, frame, room = (tuple(p["trg"]) + (0,))[:3]
        out.append("trg %d %d" % (no, frame) + (" 0x%03x" % room if room else ""))
    if p.get("kill"):
        em_id, frame, room = (tuple(p["kill"]) + (0,))[:3]
        out.append("kill 0x%02x %d" % (em_id, frame) + (" 0x%03x" % room if room else ""))
    for g in p.get("goto") or []:
        frame, pos = g[0], g[1]
        out.append("goto %d %d %d %d" % ((frame,) + tuple(pos)) + (" %.4f" % g[2] if len(g) > 2 else ""))
    if dump:
        out.append("dump")
    if p.get("late") is not None:
        mask, tick, room = (tuple(p["late"]) + (1400, 0x100))[:3]
        # fixed width: the arms of a pair differ only in the mask's two digits (same warp.txt length)
        out.append("late 0x%02x %d 0x%03x" % (mask, tick, room))
    return "\n".join(out) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("preset", nargs="?")
    ap.add_argument("--door", action="store_true")
    ap.add_argument("--dump", action="store_true")
    ap.add_argument("--room", type=lambda s: int(s, 0))
    ap.add_argument("--pos", type=float, nargs=3)
    ap.add_argument("--ang", type=float)
    ap.add_argument("--rsf", action="append", default=[], help="ROOM:BIT[,BIT...]")
    ap.add_argument("--scenario", action="append", default=[], help="0|1:HEX")
    ap.add_argument("--find", type=lambda s: int(s, 0))
    ap.add_argument("--act", action="append", default=[], help="KIND:FRAME:HOLD")
    ap.add_argument("--trg", help="NO:FRAME[:ROOM] make DebugTrg(NO) return 1 once (r101 bell: 0)")
    ap.add_argument("--kill", help="ID:FRAME[:ROOM] shoot the first live enemy with model id ID dead from that "
                                   "room frame (r100 s03 Ganado: 0x12)")
    ap.add_argument("--late", help="MASK[:TICK[:ROOM]] same-binary A/B switches from global tick TICK (default 1400) "
                                   "in ROOM (default 0x100); bits: 1 world LOD 20 px, 2 actor LOD 8 px, 4 no draw, "
                                   "8 r100 cap, 10 Leon source path (warp_late.h)")
    ap.add_argument("-o", "--output")
    a = ap.parse_args(argv)
    if a.preset == "list":
        for k, p in PRESETS.items():
            print("%-18s %s" % (k, p.get("notes", "")))
        return 0
    if a.preset:
        if a.preset not in PRESETS:
            ap.error("unknown preset %s (warp.py list)" % a.preset)
        p = dict(PRESETS[a.preset])
        if p.get("pos", 0) is None:
            ap.error("preset %s has no verified position yet" % a.preset)
    elif a.room is not None:
        p = dict(room=a.room, notes="explicit")
    else:
        ap.error("a preset or --room")
    if a.pos:
        p["pos"] = a.pos
    if a.ang is not None:
        p["ang"] = a.ang
    rsf = {k: list(v) for k, v in (p.get("rsf") or {}).items()}
    for r in a.rsf:
        room, bits = r.split(":")
        rsf.setdefault(int(room, 0), []).extend(int(b) for b in bits.split(","))
    p["rsf"] = rsf
    sc = dict(p.get("scenario") or {})
    for s in a.scenario:
        i, v = s.split(":")
        sc[int(i)] = sc.get(int(i), 0) | int(v, 16)
    p["scenario"] = sc
    if a.find is not None:
        p["find"] = (p.get("find") or 0) | a.find
    door = list(p.get("door", []))
    for act in a.act:
        kind, frame, hold = act.split(":")
        door.append((kind, int(frame), int(hold)))
    p["door"] = door
    if a.trg:
        f = a.trg.split(":")
        p["trg"] = (int(f[0], 0), int(f[1], 0), int(f[2], 0) if len(f) > 2 else 0)
    if a.kill:
        f = a.kill.split(":")
        p["kill"] = (int(f[0], 0), int(f[1], 0), int(f[2], 0) if len(f) > 2 else 0)
    if a.late:
        f = a.late.split(":")
        p["late"] = (int(f[0], 0), int(f[1], 0) if len(f) > 1 else 1400, int(f[2], 0) if len(f) > 2 else 0x100)
    text = lines_for(p, door=a.door or bool(a.act), dump=a.dump, name=a.preset or "explicit")
    if a.output:
        open(a.output, "w").write(text)
    else:
        sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
