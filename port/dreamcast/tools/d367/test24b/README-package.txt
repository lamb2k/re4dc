RE4 Dreamcast test 24b, source SHA_PLACEHOLDER

See Known Issues: https://github.com/lamb2k/re4dc/blob/dreamcast-port/port/dreamcast/docs/KNOWN_ISSUES.md

Extract the gdemu folder and copy its four disc files into a new numbered
folder on your GDEMU SD card. Replace any older test folder, and if your
card manager offers "Shrink GDI", leave it off. Flycast can open
gdemu/disc.gdi directly (if menu or popup text looks broken in Flycast,
use its per-pixel renderer setting).

Test 24b replaces test 24, which was pulled for missing scenery in the
first area. Still up to the castle gate (r200).

New in test 24b:
* Fixed: the first area's missing scenery is back (the door, the house
  windows, a house and the explosives in the tree).
* The custom title screen is back (it was lost in test 24).
* Window glass and bars are back in the village, farm and barn houses.
* PS2 torch flames, and explosions and candle effects are back.
* Every weapon uses its PS2 model; Leon uses the PS2 skeleton.
* PS2 radio call portraits.
* Dreamcast controller art in the Player's Manual and on the HUD.
* Faster scenery in 19 more rooms, the village square and the farm.
* Hanging cloth and flags are drawn; Leon's flashlight lights the
  ground at night.
* More PS2 props, Ganado bodies, pictures and sounds.
* A QA build for testers is a separate download on the release page.

From test 24:
* PS2 HUD, inventory screens, fonts, animation, chapter 1 sounds and music.
* Mendez has his PS2 model in the barn door animation (#57); the
  Blacktail can be equipped (#58).

Please tell us about any crash, freeze or missing texture, and where. Photos
help a lot. If you play from a loader other than GDEMU (MODE, USB-GDROM,
DreamShell), please tell us which one and its version.

Source: https://github.com/lamb2k/re4dc/commit/SHA_PLACEHOLDER
