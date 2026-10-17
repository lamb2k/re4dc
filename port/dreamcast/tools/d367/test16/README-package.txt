RE4 Dreamcast test 16.3 (third hotfix of test 16), source SHA_PLACEHOLDER

See Known Issues: https://github.com/lamb2k/re4dc/blob/dreamcast-port/port/dreamcast/docs/KNOWN_ISSUES.md

Extract the gdemu folder and copy its four disc files into a new numbered
folder on your GDEMU SD card. Flycast can open gdemu/disc.gdi directly (if
menu or popup text looks broken in Flycast, use its per-pixel renderer
setting).

New in test 16.3 (hotfix), for the village and farm fights:
* Fewer disc reads during fights: the Ganado animations the fights in the
  village (r101), the farm (r103), r104, r108 and r118 use are loaded
  when you enter the room instead of from the disc in the middle of a
  fight.
* The village (r101) keeps all of its pictures in video memory: two
  Ganado texture sheets there load at half resolution (a small loss of
  detail on the villagers up close), and pictures pack more tightly.
  r103, r104, r108 and r118 also load their pictures when you enter.
The disc data is test 16.2's with new Ganado animation tables and a new
room picture list; the program changed.

New in test 16.2 (hotfix):
* Fixed: in 16.1, a fifth Ganado could appear for a moment in some village
  areas.
* In r108 the Ganados holding a weapon use their PS2 model (they used the
  GameCube model).

New in test 16.1 (hotfix):
* At most 4 Ganados at once (was 6); more arrive as you kill them. Every
  villager still appears, and the waves, kills and events are unchanged.
* The ambient farm animals are removed for speed: the cows, the chickens
  and the farm dog (no eggs from chickens). The dog in the bear trap and
  the dog that helps against El Gigante are still there.
* Scripted Ganado waves in r10a no longer start early. A Ganado still
  waiting for its turn under the limit was counted as dead (test 16 too).
The disc data is test 16's plus one r108 model file; the program changed.

New disc format: from test 16 the disc is a standard GD-ROM image, laid
out the way the community tool mkdcdisc writes one and pressed GD-ROMs are:
the full-size data track (track03.bin is about 1.2 GB, about 213 MB more
than test 15 on the SD card), the table of contents real GD-ROMs carry, and
the program as the last file. Users reported freezes and crashes on GDEMU
only (#27); a GDEMU console test of the test 14 game in this format ran
fine. Please replace the old folder (don't mix test 15 and test 16 track
files), and if your card manager offers "Shrink GDI", leave it off.

New in test 16:
* The disc format above (for the GDEMU freezes, #27).
* Disc reads: if a fast disc read fails, times out or comes back empty,
  the game switches to plain sector reads for the rest of the session
  and keeps playing (DreamShell and other loaders, #28).
* Radio call subtitles follow the voice instead of falling behind it.
* The lake draws its water the PS2 way out on the water too: the Del
  Lago boat fight and the lake shore at night.
* The village (r101) is back to its full-detail world: the burning
  stake, the pyre and the fence by the house are complete again.

From test 15.1 (hotfix):
* The see-through haze and mist sprites around Leon are no longer drawn,
  in any room and at every Foliage setting. The distant haze is still
  drawn as fog.
* Foliage Off leaves out every see-through brush, leaf, shadow and mist
  card, and the r109 cabin keeps its walls and floor.

Still open: in r102, right after loading a save, a few effect pictures
can be missing for a moment (#33).

Please tell us about any crash, freeze or missing texture, and where. Photos
help a lot. If you play from a loader other than GDEMU (MODE, USB-GDROM,
DreamShell), please tell us which one and its version.

Source: https://github.com/lamb2k/re4dc/commit/SHA_PLACEHOLDER
