RE4 Dreamcast test 25, source SHA_PLACEHOLDER

See Known Issues: https://github.com/lamb2k/re4dc/blob/dreamcast-port/port/dreamcast/docs/KNOWN_ISSUES.md

Extract the gdemu folder and copy its four disc files into a new numbered
folder on your GDEMU SD card. Replace any older test folder, and if your
card manager offers "Shrink GDI", leave it off. Flycast can open
gdemu/disc.gdi directly (if menu or popup text looks broken in Flycast,
use its per-pixel renderer setting).

Test 25 brings faster fights and everything from tests 24 and 24b, which
never reached a download. Still up to the castle gate (r200).

New in test 25:
* Faster with enemies on screen: one fast lighting path for every
  character, and drawing speedups for characters, effects and scenery.
* Leon's dark clothes are no longer crushed to black.
* PS2 sounds for the partners, crows and every weapon (no silent weapons).
* Every weapon uses its PS2 model; Leon uses the PS2 skeleton.
* Window glass and bars are back in the forest, village, farm and barn
  houses.
* PS2 torch flames, and explosions and candle effects are back. Torch
  rooms such as the night road no longer draw a fire that fills the
  screen, and run faster.
* PS2 radio call portraits, and test 22's button and icon set.
* Hanging cloth and flags are drawn; Leon's flashlight lights the
  ground at night.
* PS2 HUD, inventory screens, fonts, animation, props, pictures and
  sounds. Mendez has his PS2 model in the barn door animation (#57); the
  Blacktail can be equipped (#58).
* A QA build for testers is a separate download on the release page.

Please tell us about any crash, freeze or missing texture, and where. Photos
help a lot. If you play from a loader other than GDEMU (MODE, USB-GDROM,
DreamShell), please tell us which one and its version.

Source: https://github.com/lamb2k/re4dc/commit/SHA_PLACEHOLDER
