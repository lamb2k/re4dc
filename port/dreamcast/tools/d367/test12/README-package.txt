RE4 Dreamcast test 12, source SHA_PLACEHOLDER (2026 10 15)

See Known Issues: https://github.com/lamb2k/re4dc/blob/dreamcast-port/port/dreamcast/docs/KNOWN_ISSUES.md

Extract the gdemu folder and use its four disc files with your usual GDEMU setup.
Flycast can open gdemu/disc.gdi directly (if menu or popup text looks broken
in Flycast, use its per-pixel renderer setting). This build follows test 10
(test 11 was not released; its changes are listed below too) and plays to the
end of chapter two, part one.

New in test 12:
* Fixed: a crash screen when a radio call opens on a real Dreamcast
  (MISSING sub screen pool freeze allocation), confirmed on a console.
* The controller and VMU answers at start-up are read more safely on a real
  Dreamcast.
* The village (r101) does less work each frame: its fire and smoke use the PS2 pictures, the
  distant haze is drawn as fog by the graphics chip, fewer textures are reloaded
  during the fight, and the world is drawn with less work.
* In the village fight at most 6 villagers attack at once. The others wait and
  join as villagers fall; every villager still appears, and the waves, the
  kills and the bell are unchanged.
* Leon is brighter: a soft fill light brings him close to the GameCube look,
  and his radio call portrait and inventory picture are no longer too bright.
* Leon's textures are compressed, which leaves more graphics memory for the
  rooms.
* The merchant uses his PS2 model.
* Objects in the first village (r100) and the village (r101) use their PS2
  models; the boxes and barrels you can break keep the GameCube models.
* Armed villagers hold their weapons with the PS2 grip.
* Villagers' caps, hats and glasses use their PS2 models and pictures.
* Items you can pick up, their close-ups in the inventory, and the pieces of
  broken boxes and barrels use their PS2 models and pictures on the whole
  route; the few pieces the PS2 version removed are not drawn.
* Options has a Rendering row again: Standard (the default) or FSAA, which
  smooths edges and is slower in busy scenes. Every start begins in Standard.

Known issue new in test 12: the cutscene at the r100 cliff (after the first
house) is skipped; the game goes on normally after it.

From test 11 (not released before):
* Leon is lit by the scene's lights, and Leon and the villagers cast shadows.
* Enemy placement in r100, r101, r104, r108, r11a and r11b follows the PS2
  version.
* The speed display is off unless you switch it on (hold R and press START: Off or
  On screen). It no longer uses the VMU; the VMU keeps its Leon, Ashley, call and
  Luis pages.
* Torches glow again, and r11b's rain falls as light streaks like on the PS2.
* Room effects follow the PS2 version.
* Black walls and floors in chapter 1 and 2-1 rooms are lit the way the
  GameCube lights them (not yet in r119).
* Missing pieces of the world (r117 entrance, the El Gigante fight) are drawn.
* The first village (r100) uses its PS2 colours and see-through overlays.
* Missing textures are back: the chapter 2-1 results picture, the r106 bats,
  a dark block in r119 and a texture at the village bell.
* The lake ripples stay on top of the water.

Please tell us about any crash, freeze or missing texture, and where. Photos
help a lot.

Source: https://github.com/lamb2k/re4dc/commit/SHA_PLACEHOLDER
