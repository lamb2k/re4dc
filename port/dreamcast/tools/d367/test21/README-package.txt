RE4 Dreamcast test 21, source SHA_PLACEHOLDER

See Known Issues: https://github.com/lamb2k/re4dc/blob/dreamcast-port/port/dreamcast/docs/KNOWN_ISSUES.md

Extract the gdemu folder and copy its four disc files into a new numbered
folder on your GDEMU SD card. Replace any older test folder, and if your
card manager offers "Shrink GDI", leave it off. Flycast can open
gdemu/disc.gdi directly (if menu or popup text looks broken in Flycast,
use its per-pixel renderer setting).

New in test 21 (still up to the castle gate, r200):
* Fights no longer stall reloading enemy animations (the r100 ambush,
  the village fights).
* Ashley no longer stalls the game before the El Gigante fight (r11e).
* Lighter fights: dead bodies and props cost less to run and draw.
* The night road villagers (r111) use their PS2 model (#42).
* The dam rooms use the PS2 lighting (#47).
* Steady frame pacing: Options > Frame pacing > Steady shows every frame
  for the same time. Fast stays the default.
* A QA build for testers is a separate download on the release page.

From test 20:
* The dam (r10c) and the lake's side rooms (r10d, r10e) are playable,
  and the Insignia Key is at the dam, as in the original.

From test 19:
* Quick weapon select: hold X and press the D-pad to swap weapons.
* Foliage starts Off and view distance starts at Near in Options.

Please tell us about any crash, freeze or missing texture, and where. Photos
help a lot. If you play from a loader other than GDEMU (MODE, USB-GDROM,
DreamShell), please tell us which one and its version.

Source: https://github.com/lamb2k/re4dc/commit/SHA_PLACEHOLDER
