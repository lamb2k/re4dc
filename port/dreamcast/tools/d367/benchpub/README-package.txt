RE4 DREAMCAST BENCHMARK DISC (2026-10 DEFINITIVE) - THIS IS NOT THE GAME
========================================================================

This disc only measures how fast the RE4 Dreamcast port runs on your
console. It cannot be played: there is no title menu and no New Game, and
it saves nothing (it does not touch your VMU). To play, use the current test
release: https://github.com/lamb2k/re4dc/releases

Build SHA_PLACEHOLDER: the test 12.1 game data and program, with the
benchmark's own measuring code, and the scripted scenes listed below. The
definitive benchmark has up to seven scenes; a disc carries some of them
(the others show "NOT ON THIS DISC"). Scenes 1 and 2 are the same scenes as
on benchmark versions 1 and 2, so old and new results compare directly.

Scenes on this disc
SCENES_PLACEHOLDER

All scenes of the definitive benchmark
1  R101 CROSS    the village: Leon stands by the burning cross while the
                 villagers attack (at most 6 at once), with fire, haze and
                 torches. 30 seconds are measured.
2  R100 HOUSE    the first house: a short cutscene plays, then Leon waits at
                 the back window while the villagers close in. About 17
                 seconds are measured.
3  R10B DELLAGO  the lake (Del Lago): Leon in the boat, pulled along by the
                 lake monster, then aiming the harpoon. A cutscene plays
                 first. 30 seconds are measured.
4  R103 FARM     the farm: a wide outdoor view (barn, windmill, fences, fog)
                 with five villagers far off at its end. 30 seconds are
                 measured.
5  R209 CASTLE*  PREVIEW of unreleased content (see below).
6  R101 CROSS    the village again, as a geometry sweep (page 4 and on).
7  R103 FARM     the farm again, as a geometry sweep.

What it does (no input needed)
1. A start screen says what the disc is. Press START (or wait 20 seconds),
   then put the controller down until the results screen.
2. The scenes run one after the other, each from a fresh start.
3. The results appear on several pages (3 plus one per sweep scene). Press
   B (or Y) for the next page.
4. Press A on any page to run all the scenes again (optional).

A red banner "BENCHMARK DISC - NOT THE GAME" stays at the top of the screen
the whole time. Every results page shows the build, the run number and the
pacing mode the game ran with (FAST is the game's normal setting: when a
picture takes too long, the game runs its next tick without drawing it).

How to report
Open a new issue named "Benchmark results" at
https://github.com/lamb2k/re4dc/issues and include:
- a photo of each results page (sharp, straight on, all text readable)
- the CODE line of each page, typed out (a code may wrap onto two or three
  lines on screen; type it as one line)
- your console region (NTSC-U, NTSC-J or PAL)
- how you ran it: GDEMU, another optical drive emulator (say which), or a
  burned disc
- your video cable (VGA, S-Video, composite, RGB SCART, HDMI adapter)
If it crashes or hangs, photograph the screen and say which scene it was in.

Setup
Copy the four files in the gdemu folder (disc.gdi, track01.bin, track02.raw,
track03.bin) to a new folder on your SD card, the same way as any GDEMU
game. The menu lists it as "RE4DC BENCHMARK (NOT THE GAME)". Flycast can
open gdemu/disc.gdi as well, but emulator numbers are not console numbers,
and the cache counters stay empty there.

Results page 1: how fast each scene ran
FPS         average frames drawn per second
MIN1S       the lowest one-second window
CPU         milliseconds of game work per game tick (30 ticks a second)
GPU         milliseconds the graphics chip needs to draw one frame
SPD%        game speed (100 = real time; lower means slow motion)
READS/S     disc reads per second
WAIT MS/S   milliseconds per second the game waited for the disc
KOS MIN KB  the lowest free system memory during the scene, in KB (this
            disc gives the system 64 KB more than the game disc does)
CODE        the numbers above in one line: A for scene 1, B for scene 2 and
            so on, then a check value. Scenes 1 and 2 alone give the same
            code format as versions 1 and 2.
* PREVIEW: the castle scene is unreleased content. Its Zealots still draw
through the GameCube path and it uses 8-9 GameCube effect textures, so its
numbers are pessimistic. It is not part of any test release.

Results page 2: where the processor's time goes
The time of each picture split into parts, in milliseconds, one row per
scene. "Per picture" means one drawn frame plus the game ticks the game ran
without drawing before the next one.
LOGIC       the game itself: enemies, Leon, the camera, scripts
APREP       getting the characters ready to draw: animation results,
            skinning, lighting, choosing what is visible
ADRAW       sending the characters to the graphics chip
WORLD       sending the scenery (village, house, farm, lake, castle) to the
            graphics chip
OTHER       everything else: effects, fire, haze, text, sound and disc
            checks
WAIT        the processor has nothing to do until the next picture
TOTAL       all parts together (the time between two pictures)
The second table, MEM WAIT%, uses the processor's built-in counters: the
share of each part's time the processor stood still waiting for data from
memory (data cache misses). A high number means that part is slowed down by
memory, not by the amount of math. ALL is for the working parts together.
CODE 2      per scene (P for scene 1, Q for scene 2 ...) the six part times
            times ten, then the five MEM WAIT% values, then a check value
The counters take turns: each picture counts one kind of event, so each
number comes from about a fifth of the pictures. On an emulator the
counters do not count; the page then says so and shows times only.

Results page 3: ticks, caches and geometry
DRAWN       processor milliseconds of the tick that draws
SKIPS       ticks run without drawing per picture
SKIP        processor milliseconds of each of those ticks
VERTK       thousands of corner points (vertices) sent to the graphics chip
            per picture
HDRS        polygon headers per picture (one per part of a model or piece
            of scenery with its own texture or settings)
D-ST%       share of the time stalled on data cache misses
DMISK       thousands of data cache misses per picture (reads plus writes)
I-ST%       share of the time stalled on instruction cache misses
IMISK       thousands of instruction cache misses per picture
CODE 3      per scene (K for scene 1 ...) DRAWN.SKIPS.SKIP / I-ST%.IMISK /
            DMISK / VERTK.HDRS (tenths where the page shows one decimal),
            then a check value

Sweep pages (page 4 and on): what geometry and effects cost
A sweep scene goes back to a scene's view. After a set time (with villagers
on screen in the village) the game stands still: nothing moves, nothing
thinks, the same picture is drawn every tick (the game's frame skipping is
off for this) and the disc draws that one picture in up to nine ways, 6.5
seconds each (the sweep page lists the ways this disc draws; the village
sweep of part 1 draws the first seven, without the two effect rows):
AS SHIPPED   as the game draws it
HALF GANADO  every other villager left out
NO GANADOS   no villagers drawn
NO LEON      Leon left out
WORLD 18.8M  the scenery drawn only up to 18.75 m (normally 25 m)
WORLD 12.5M  the scenery drawn only up to 12.5 m
NO WORLD     no scenery at all (the characters, effects and text are still
             drawn): the whole cost of the scenery, its fixed set-up and its
             vertices together
NO EFFECTS   no fire, haze, smoke or spark sprites drawn (the effects still
             run; only their drawing is left out)
NO WORLD+FX  neither scenery nor effects drawn
The line above the table says how many villagers were drawn as shipped.
For each way the page shows:
VERTK       thousands of vertices sent to the graphics chip per picture
CPU         milliseconds of processor work per picture
ACTOR       of that, the characters
WORLD       of that, the scenery
GPU         milliseconds the graphics chip needs per picture
ST%         as on page 2 (waiting for memory)
C/1K, G/1K  the difference against AS SHIPPED divided by the vertices left
            out: processor and graphics chip milliseconds per 1000 vertices.
            Leaving a model out also saves its fixed work (its skeleton, its
            set-up), so for the characters this is the most a simpler model
            could save.
CODE        S (the village) or F (the farm), then for each way: vertices in
            hundreds, CPU and GPU milliseconds times ten; then a check value
The game stands still only during these sweeps; it is never saved and the
disc starts each scene fresh.

SHA256SUMS.txt lists the sha256 of the zip and of each file in the gdemu
folder; the track03.bin line is the image the checks ran on.
