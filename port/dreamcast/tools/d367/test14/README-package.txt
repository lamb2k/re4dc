RE4 Dreamcast test 14, source SHA_PLACEHOLDER (2026 10 15)

See Known Issues: https://github.com/lamb2k/re4dc/blob/dreamcast-port/port/dreamcast/docs/KNOWN_ISSUES.md

Extract the gdemu folder and use its four disc files with your usual GDEMU setup.
Flycast can open gdemu/disc.gdi directly (if menu or popup text looks broken
in Flycast, use its per-pixel renderer setting). This build follows test 13
and plays to the end of chapter two, part one. Its content is the same as
test 13; test 14 makes the game read the disc less and do less work per frame.

New in test 14:
* The village (r101) keeps all of its textures in graphics memory: they are
  loaded when the room starts, and the radio call no longer makes the
  on-screen display reload its pictures from the disc afterwards.
* The farm after the village (r103) reads the disc far less during play:
  the villagers' animations stay in memory instead of being read again, and
  the room's textures are loaded when it starts.
* Disc reads finish more safely on the console: a read now waits until the
  drive's transfer has really finished, and two drive hangs in the disc
  library are fixed. This may help the "stops while loading" reports.
* A few parts of each frame are quicker (fewer repeated settings and
  clears); the picture is the same.

Known issue from test 12, unchanged: the cutscene at the r100 cliff (after the
first house) is skipped; the game goes on normally after it.

Please tell us about any crash, freeze or missing texture, and where. Photos
help a lot.

Source: https://github.com/lamb2k/re4dc/commit/SHA_PLACEHOLDER
