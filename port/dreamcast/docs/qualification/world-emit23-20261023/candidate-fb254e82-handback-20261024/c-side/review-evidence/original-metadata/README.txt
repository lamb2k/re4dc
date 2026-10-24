RE4 Dreamcast test 22, source fb254e82

See Known Issues: https://github.com/lamb2k/re4dc/blob/dreamcast-port/port/dreamcast/docs/KNOWN_ISSUES.md

Extract the gdemu folder and copy its four disc files into a new numbered
folder on your GDEMU SD card. Replace any older test folder, and if your
card manager offers "Shrink GDI", leave it off. Flycast can open
gdemu/disc.gdi directly (if menu or popup text looks broken in Flycast,
use its per-pixel renderer setting).

New in test 22 (still up to the castle gate, r200):
* Smoother distant textures (mipmaps): far ground and walls shimmer less.
* No disc read when you shoot (ammo digits and muzzle flash).
* No stutter at in-game events.
* Faster inventory opening.
* Fixed: the crash at the dam's first villager on a real Dreamcast (#52).
* Fixed: less free memory after loading a save and resetting (#26).
* Fixed: Ganados stalling as they die.
* Fixed: pausing in the Mendez fight, and the world behind the pause
  menu (#48, #49).
* The lake island trees no longer look shredded.
* Trail and ribbon effects draw again.
* Safety guards stop a failed load from crashing the game.
* A QA build for testers is a separate download on the release page.

From test 21:
* Fights no longer stall reloading enemy animations.
* Steady frame pacing in Options > Frame pacing.

Please tell us about any crash, freeze or missing texture, and where. Photos
help a lot. If you play from a loader other than GDEMU (MODE, USB-GDROM,
DreamShell), please tell us which one and its version.

Source: https://github.com/lamb2k/re4dc/commit/fb254e82
