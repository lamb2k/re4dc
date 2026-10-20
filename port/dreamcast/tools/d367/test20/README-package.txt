RE4 Dreamcast test 19.1, source SHA_PLACEHOLDER

See Known Issues: https://github.com/lamb2k/re4dc/blob/dreamcast-port/port/dreamcast/docs/KNOWN_ISSUES.md

Extract the gdemu folder and copy its four disc files into a new numbered
folder on your GDEMU SD card. Replace any older test folder, and if your
card manager offers "Shrink GDI", leave it off. Flycast can open
gdemu/disc.gdi directly (if menu or popup text looks broken in Flycast,
use its per-pixel renderer setting).

New in test 19.1 (a hotfix of test 19):
* The r100 cliff cutscene plays all 340 frames again (#45).
* No skipped effect sprites in r117 after the Saddler scene starts (#46).
* Back to the earlier character drawing: test 19's new path for Leon and
  the enemies measured slower. The picture is the same.

From test 19 (still up to the castle gate, r200):
* Quick weapon select: hold X and press the D-pad to swap weapons, like
  the RE4 remake. Up handguns, right shotguns, down grenades, left
  rifles. The game pauses for a moment while the weapon loads.
* New Options defaults: foliage starts Off and view distance starts at
  Near. The lake keeps its long view. You can still change both.
* The Player's Manual shows the Dreamcast pages, not the GameCube ones
  (#44).
* Enemies hidden behind walls are no longer drawn.
* Faster scenery drawing, with the same picture.

From test 18:
* Chapter 2-1 can be finished (#40): the Insignia Key is given at the
  dam gate.
* A lighter El Gigante, and PS2 models for Leon and El Gigante in r119.

From test 17:
* Chapters 2-2 and 2-3 are playable, up to the castle gate (r200).
  At most 4 Ganados at once.

Please tell us about any crash, freeze or missing texture, and where. Photos
help a lot. If you play from a loader other than GDEMU (MODE, USB-GDROM,
DreamShell), please tell us which one and its version.

Source: https://github.com/lamb2k/re4dc/commit/SHA_PLACEHOLDER
