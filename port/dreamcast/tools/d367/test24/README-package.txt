RE4 Dreamcast test 24, source SHA_PLACEHOLDER

See Known Issues: https://github.com/lamb2k/re4dc/blob/dreamcast-port/port/dreamcast/docs/KNOWN_ISSUES.md

Extract the gdemu folder and copy its four disc files into a new numbered
folder on your GDEMU SD card. Replace any older test folder, and if your
card manager offers "Shrink GDI", leave it off. Flycast can open
gdemu/disc.gdi directly (if menu or popup text looks broken in Flycast,
use its per-pixel renderer setting).

New in test 24 (still up to the castle gate, r200):
* PS2 weapons: Leon's guns, in his hands and in the inventory.
* PS2 HUD, inventory screens and English fonts.
* PS2 animation for Leon, the Ganados and the weapons.
* PS2 sounds and music in chapter 1.
* PS2 props in chapter 2: breakable boxes and barrels; the torches and
  window panes the PS2 removed are gone.
* Leon's PS2 textures (jacket and chapter 2 outfit).
* PS2 church candles.
* Fixed: Mendez has his PS2 model in the barn door animation (#57).
* Fixed: the Blacktail can be equipped (#58).
* The GameCube cutscene files no longer load; about 13 MB came off the disc.
* A QA build for testers is a separate download on the release page.

From test 23:
* PS2 river water and trap explosions; Mendez no longer freezes.
* No hang on slow disc reads (DreamShell and similar loaders, #28).

Please tell us about any crash, freeze or missing texture, and where. Photos
help a lot. If you play from a loader other than GDEMU (MODE, USB-GDROM,
DreamShell), please tell us which one and its version.

Source: https://github.com/lamb2k/re4dc/commit/SHA_PLACEHOLDER
