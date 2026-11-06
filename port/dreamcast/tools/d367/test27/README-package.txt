RE4 Dreamcast test 27, source SHA_PLACEHOLDER

See Known Issues: https://github.com/lamb2k/re4dc/blob/dreamcast-port/port/dreamcast/docs/KNOWN_ISSUES.md

Two discs in this zip:
* gdemu/  is Disc 1 (New Game to the castle gate, end of chapter 2-3).
* disc2/  is Disc 2 (the castle).
Copy each folder's disc files into its own new numbered folder on your
GDEMU SD card. Replace any older test folders, and if your card manager
offers "Shrink GDI", leave it off. Play Disc 1 to the castle gate, then
continue on Disc 2. Flycast can open each disc.gdi directly (if menu or popup
text looks broken in Flycast, use its per-pixel renderer setting).

New in test 27:
* The PS2 sky in normal play in the outdoor rooms.
* Boss fixes: El Gigante's farm cutscenes and fade use his PS2 model, and
  Del Lago keeps his textures after he dies.
* No more El Gigante slowdown after he breaks objects.
* Reloading a save after dying in the El Gigante fight with Ashley no
  longer crashes.
* More of the castle on Disc 2: the rest of chapter 3-1, and the chapter
  3-3 and 3-4 rooms (they join normal play with chapter 3-2 in test 28).
  The castle Zealots in the lever room and the Zealot chase load cleanly.
* Smoother castle rooms, faster fights at the dam and the village, and
  smoother music streaming.
* An odd memory read when a radio call opens is gone (issue #63; not yet
  confirmed as the crash reported there).
* A QA build for testers is a separate download on the release page.

Please tell us about any crash, freeze or missing texture, and where. Photos
help a lot. If you play from a loader other than GDEMU (MODE, USB-GDROM,
DreamShell), please tell us which one and its version.

Source: https://github.com/lamb2k/re4dc/commit/SHA_PLACEHOLDER
