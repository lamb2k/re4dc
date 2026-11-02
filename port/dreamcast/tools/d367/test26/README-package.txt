RE4 Dreamcast test 26, source SHA_PLACEHOLDER

See Known Issues: https://github.com/lamb2k/re4dc/blob/dreamcast-port/port/dreamcast/docs/KNOWN_ISSUES.md

Two discs in this zip:
* gdemu/  is Disc 1 (New Game to the castle gate, end of chapter 2-3).
* disc2/  is Disc 2 (the castle, chapters 3-1 and 3-2).
Copy each folder's disc files into its own new numbered folder on your
GDEMU SD card. Replace any older test folders, and if your card manager
offers "Shrink GDI", leave it off. Play Disc 1 to the castle gate, then
continue on Disc 2. Flycast can open each disc.gdi directly (if menu or popup
text looks broken in Flycast, use its per-pixel renderer setting).

New in test 26:
* The castle starts on Disc 2 (chapters 3-1 and 3-2), with PS2 data for
  its rooms, characters and animations.
* The PS2 sky outdoors in normal play and in cutscenes.
* Leon's lighting is back to the test 23/24 look, his pistol included.
* Faster farmhouse cutscenes.
* QA build only: the QA link connects reliably again.
* A QA build for testers is a separate download on the release page.

Please tell us about any crash, freeze or missing texture, and where. Photos
help a lot. If you play from a loader other than GDEMU (MODE, USB-GDROM,
DreamShell), please tell us which one and its version.

Source: https://github.com/lamb2k/re4dc/commit/SHA_PLACEHOLDER
