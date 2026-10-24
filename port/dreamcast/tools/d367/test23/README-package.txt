RE4 Dreamcast test 23, source SHA_PLACEHOLDER

See Known Issues: https://github.com/lamb2k/re4dc/blob/dreamcast-port/port/dreamcast/docs/KNOWN_ISSUES.md

Extract the gdemu folder and copy its four disc files into a new numbered
folder on your GDEMU SD card. Replace any older test folder, and if your
card manager offers "Shrink GDI", leave it off. Flycast can open
gdemu/disc.gdi directly (if menu or popup text looks broken in Flycast,
use its per-pixel renderer setting).

New in test 23 (still up to the castle gate, r200):
* River water: the cave river, the dam river and the merchant cave pool
  draw their PS2 water (#55).
* Trap explosions: tree and door traps explode with fire (#55).
* Mendez no longer freezes after grabbing Leon (#55).
* Steady barn lights; effects in busy rooms stop dropping out (#41).
* No hang on slow disc reads (DreamShell and similar loaders, #28).
* Mipmaps on bushes and cut-out pictures.
* Fewer see-through effects: mist, glows and dust are cut.
* Faster inventory, and a better-looking El Gigante up close.
* Fixed: the lever gears, the castle gate texture, the boat weapon display.
* A QA build for testers is a separate download on the release page.

From test 22:
* Smoother distant textures (mipmaps).
* No disc read when you shoot, and no stutter at in-game events.

Please tell us about any crash, freeze or missing texture, and where. Photos
help a lot. If you play from a loader other than GDEMU (MODE, USB-GDROM,
DreamShell), please tell us which one and its version.

Source: https://github.com/lamb2k/re4dc/commit/SHA_PLACEHOLDER
