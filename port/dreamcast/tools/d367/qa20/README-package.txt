RE4DC QA TEST TN_PLACEHOLDER - QA build for testers (source: see SHA256SUMS.txt)
=====================================================================

This is a test tool, not the game release. It is the Test TN_PLACEHOLDER release program plus a QA menu that
teleports you to places in the story, puts the main guns in your case, and shows diagnostics.
Use the normal Test release for real play.

Put the gdemu folder on your SD card like any GDEMU game (disc.gdi + track files).


The menu
--------
- At power-on the QA menu appears first.
  - "Start the game normally" goes to the title screen.
  - "Teleport..." picks a chapter, then a place.
- In the game: hold L and R fully, then press D-pad Down.
  - It opens only in free play. During a cutscene, the inventory, a door load or a scripted
    event it does nothing; try again when Leon is free.
  - The game pauses while the menu is open.
- Buttons: D-pad chooses, A selects or switches, B goes back (B or Start on the top page resumes).


What is in the menu (in game)
-----------------------------
- Resume
- Teleport...: chapter, then place.
- Diagnostics: live numbers and the last log lines (see below).
- Refill health: Leon and the partner.
- Leon invincible: Off / On. Default Off, so deaths and the game-over screen work as normal.
- Partner invincible: Off / On (Ashley, Luis, any companion). Default Off.
- Enemies invincible: Off / On. Enemies still react, bleed and lose parts, but do not die. Default Off.
  A single huge hit can still kill one; turn it off to finish a fight.
- Speed display: Off / On (frames per second, game speed %, CPU %, top right).
- Lake shore view: 45 m / 30 m. How far you see on the night lake shore (r11a / r11b).
- Quit to the title screen.
The invincibility switches are also on the power-on menu. They stay set across teleports.


Teleport places
---------------
"STORY" places set the story progress for that spot, and the room loads its own enemies as in normal
play (at most 4 Ganados at once, the rest arrive as others die). "BARE JUMP" places only move Leon
there: enemies may be missing.

Chapter 1-1: village
- R100 forest path (house, after the s20 cutscene)
- R101 village square (fight start)
- R101 village square, by the cross
- R102, R103 farm (entry), R103 farm fight (one Ganado already down), R104, R105, R106, R107
Chapter 1-2
- R108, R109, R10A, R117, R118, R119 El Gigante (fight)
Chapter 1-3: lake
- R10B lake path, boat start
- R10B Del Lago fight. Leon boards and is moved to the lake middle by script, then the Del Lago
  cutscene plays. Do not touch the pad for the first ~10 seconds.
- R11A
Chapter 2-1: night lake and dam
- R11B night shore after Del Lago. Scripted: Del Lago is fought and ended by the tool (Leon is
  protected during this part), then the end-of-chapter screens (press A), then the night shore arrival.
- R11B night shore (walk), R10C dam, R10D dam side room, R10E dam, R10F
Chapter 2-2
- R111, R112, R113, R11C cabin
Chapter 2-3
- R11D, R11E El Gigante (fight), R11F, R200 castle gate
A teleport always starts a fresh new game at that spot, with the kit below.


Weapon kit
----------
Every teleport and every new game on this disc starts with the large case and: handgun, shotgun,
rifle, TMP, 3 hand grenades, and ammo for each. Quick switch: hold X and press the D-pad.


Diagnostics
-----------
Shows: fps, game speed, CPU; time per part of the frame (logic, effects, models, scenery, waiting),
in 0.1 ms; memory (heap 4, KOS), video memory free and largest block; Ganados alive; live effects;
room, preset and build; the last 20 log lines.
Press X for a QR snapshot of all of it (several pages: X for the next page). Take a photo of each
page. B goes back. The menu can stay open as long as you like; play resumes when it closes.


Reporting a problem
-------------------
Please send:
1. A photo of the screen with the speed display on.
2. The preset name (shown in Diagnostics) and what you did.
3. Photos of the Diagnostics QR pages, if you can.
Report on the RE4DC GitHub issues page.


Saves
-----
Saves made after a teleport can hold odd story states. Do not use them for normal play.


Not in this build
-----------------
- Disc 2 (castle) places: later.
- Disc read numbers show "NA" (the disc meter is not in this build).
