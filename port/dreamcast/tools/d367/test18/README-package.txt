RE4 Dreamcast test 18, source SHA_PLACEHOLDER

See Known Issues: https://github.com/lamb2k/re4dc/blob/dreamcast-port/port/dreamcast/docs/KNOWN_ISSUES.md

Extract the gdemu folder and copy its four disc files into a new numbered
folder on your GDEMU SD card. Replace any older test folder, and if your
card manager offers "Shrink GDI", leave it off. Flycast can open
gdemu/disc.gdi directly (if menu or popup text looks broken in Flycast,
use its per-pixel renderer setting).

New in test 18 (still up to the castle gate, r200):
* Fix: chapter 2-1 can now be finished (#40). The Insignia Key for the
  church is given at the gate to the dam, which isn't in the game yet.
* A lighter El Gigante in both fights.
* Leon and El Gigante keep their PS2 models for the whole first El
  Gigante fight (r119).
* Leon keeps his PS2 model after a chainsaw kill, for the whole death
  scene.
* Effect pictures are there right after loading a save in r102 (#33).
* A little faster in play: Leon's jacket movement is worked out only for
  pictures that are shown.
* A little faster in the village and at the farm: mist sheets the PS2
  version never shows are no longer moved, and more scenery stays ready
  in memory.
* No more disc reads for pictures in the first house fight (r100) and at
  the night lake shore (r11b).
* No sound gap in cutscenes (#38).
* The world picture and effect pictures on the way to the castle gate
  are back (#39). For about a second in r200 some effect sprites can
  still be skipped (#41).

From test 17.1 (hotfix):
* Coming Soon returns you to the room, so you can take the other exit.

From test 17:
* Chapters 2-2 and 2-3 are playable, up to the castle gate (r200): the
  cabin siege with Luis, Mendez, the second El Gigante and the truck ride,
  with the PS2 enemy lists. At most 4 Ganados at once.
* Ashley uses her PS2 model in every room she follows Leon.
* The night lake has rain again (#30).

Please tell us about any crash, freeze or missing texture, and where. Photos
help a lot. If you play from a loader other than GDEMU (MODE, USB-GDROM,
DreamShell), please tell us which one and its version.

Source: https://github.com/lamb2k/re4dc/commit/SHA_PLACEHOLDER
