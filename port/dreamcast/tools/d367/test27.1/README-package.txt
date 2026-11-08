RE4 Dreamcast test 27.1, source SHA_PLACEHOLDER

See Known Issues: https://github.com/lamb2k/re4dc/blob/dreamcast-port/port/dreamcast/docs/KNOWN_ISSUES.md

Two discs in this zip:
* gdemu/  is Disc 1 (New Game to the castle gate, end of chapter 2-3).
* disc2/  is Disc 2 (the castle).
Copy each folder's disc files into its own new numbered folder on your
GDEMU SD card. Replace any older test folders, and if your card manager
offers "Shrink GDI", leave it off. Play Disc 1 to the castle gate, then
continue on Disc 2. Flycast can open each disc.gdi directly (if menu or popup
text looks broken in Flycast, use its per-pixel renderer setting).

New in test 27.1 (fixes for issue #66; everything else as in test 27):
* The church graveyard dial shows its symbols again.
* The title logo shows at full strength, and START on the title menu
  starts the game with one press.
* Item pickups show their "You got" text on a plain dark panel.
* The save row shows the new save count and time right away.
* A late VMU answer no longer hangs the save screen.
* When the drive reports "not ready", the game waits up to 30 seconds
  before the DISC READ FAILED screen.
Checked on Flycast, not yet on a real console.
* A QA build for testers is a separate download on the release page.

Please tell us about any crash, freeze or missing texture, and where. Photos
help a lot. If you play from a loader other than GDEMU (MODE, USB-GDROM,
DreamShell), please tell us which one and its version.

Source: https://github.com/lamb2k/re4dc/commit/SHA_PLACEHOLDER
