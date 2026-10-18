RE4 Dreamcast test 15.1 (hotfix), source SHA_PLACEHOLDER (2026 10 16)

See Known Issues: https://github.com/lamb2k/re4dc/blob/dreamcast-port/port/dreamcast/docs/KNOWN_ISSUES.md

Extract the gdemu folder and use its four disc files with your usual GDEMU setup.
Flycast can open gdemu/disc.gdi directly (if menu or popup text looks broken
in Flycast, use its per-pixel renderer setting). This build follows test 14
and plays to the end of chapter two, part one.

Test 15.1 is test 15 with two changes:
* The see-through haze and mist sprites around Leon are no longer drawn,
  in any room and at every Foliage setting. The distant haze is still
  drawn as fog.
* Foliage Off now really is off: it leaves out every see-through brush,
  leaf, shadow and mist card, and the r109 cabin keeps its walls and
  floor.

New in test 15:
* The cutscene at the r100 cliff (after the first house) plays again.
* Chapter 1 sounds: footsteps and ambience in the farm (r103), the r104 and
  r107 room music, the r106 battle music, the r102 music and the merchant's
  voice, the "you died" music and a few event jingles.
* The villagers take their colour from the room's lights, and so does the
  merchant.
* PS2 models replace the last GameCube ones in the released rooms: traps,
  bats, snake, fish, the boat, the r104 merchant and the r117 / r118 enemies.
* The pool, the river and the lake seen from the shore draw their water the
  PS2 way.
* Every chapter 1 room and r119 loads its pictures once when you enter it,
  and again in one go after the chapter results and save screens.
* Villagers away from the camera use lighter meshes; cutscenes keep the
  full models. The village (r101) scenery is rebuilt in larger pieces.
* Options has two new rows, both reset at every boot: View distance (Full,
  Near, Short; Full is the default) and Foliage (Full, Near, Off; Near is the
  default).
* Doors read a little less from the disc.

Please tell us about any crash, freeze or missing texture, and where. Photos
help a lot.

Source: https://github.com/lamb2k/re4dc/commit/SHA_PLACEHOLDER
