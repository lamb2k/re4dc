RE4 DREAMCAST BENCHMARK DISC (VERSION 2) - THIS IS NOT THE GAME
================================================================

This disc only measures how fast the RE4 Dreamcast port runs on your
console. It cannot be played: there is no title menu and no New Game, and
it saves nothing (it does not touch your VMU). To play, use the current test
release: https://github.com/lamb2k/re4dc/releases

Build SHA_PLACEHOLDER: the test 12.1 program and data, plus the two scripted
benchmark scenes. Version 2 runs the same two scenes as version 1 and shows
the same first results page, so old and new results compare directly. It
adds a second results page that shows where the console's processor spends
its time, and a third scene and page that measure what drawing more or less
detail costs.

What it does (about 5 minutes, no input needed)
1. A start screen says what the disc is. Press START (or wait 20 seconds),
   then put the controller down until the results screen.
2. Scene 1, the village (r101): Leon stands by the burning cross while the
   villagers attack (at most 6 at once), with fire, haze and torches.
   30 seconds are measured.
3. Scene 2, the first house (r100): a short cutscene plays, then Leon waits
   at the back window while the villagers close in. About 17 seconds are
   measured.
4. Scene 3, the village again: the picture freezes and is drawn six
   different ways (about 40 seconds; see page 3 below).
5. The results appear on three pages. Press B (or Y) for the next page.
6. Press A on any page to run all the scenes again (optional).

A red banner "BENCHMARK DISC - NOT THE GAME" stays at the top of the screen
the whole time.

How to report
Open a new issue named "Benchmark results" at
https://github.com/lamb2k/re4dc/issues and include:
- a photo of each of the three results pages (sharp, straight on, all text
  readable)
- the CODE line from page 1, CODE 2 from page 2 and CODE 3 from page 3,
  typed out (CODE 2 may wrap onto two lines on screen; type it as one line)
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
and page 2 stays mostly empty there (see below).

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
CODE        the numbers above in one line, with a check value at the end

Results page 2: where the processor's time goes
The Dreamcast's processor has built-in counters. This page uses them to
split each drawn frame into parts and shows, for each part and scene:
MS          milliseconds the processor spent in that part, per drawn frame
ST%         the share of that time the processor stood still waiting for
            data from memory (data cache misses). A high number means that
            part is slowed down by memory, not by the amount of math.
RD K, WR K  thousands of data cache misses per drawn frame, on reads and on
            writes
The parts:
LOGIC       the game itself: enemies, Leon, the camera, scripts
ACTOR PREP  getting the characters ready to draw: animation results,
            skinning, lighting, choosing what is visible
ACTOR DRAW  sending the characters to the graphics chip
WORLD DRAW  sending the village or house scenery to the graphics chip
OTHER       everything else: effects, fire, haze, text, sound and disc
            checks
WAIT        the processor has nothing to do until the next frame
TOTAL       all parts together (the time between two drawn frames); its
            ST% is for the working parts only
Below the table one line per scene sums up the characters: how many
milliseconds they take and how much of that is waiting for memory.
CODE 2      the page 2 numbers in one line, with its own check value: for
            each scene the milliseconds of the six parts, the ST% of the
            five working parts, and their read plus write misses in
            thousands
The counters take turns: each drawn frame counts one kind of event, so each
number comes from about a quarter of the frames. On an emulator the counters
do not count; page 2 then says so and shows times only.

Results page 3: what geometry costs
Scene 3 goes back to the village view of scene 1. After 20 seconds the game
stands still (nothing moves, nothing thinks; the same picture is drawn over
and over) and the disc draws that one picture six ways, 6.5 seconds each:
AS SHIPPED   as the game draws it
HALF GANADO  every other villager left out
NO GANADOS   no villagers drawn
WORLD 18.8M  the village scenery drawn only up to 18.75 m (normally 25 m)
NO LEON      Leon left out
WORLD 12.5M  the scenery drawn only up to 12.5 m
For each way the page shows:
VERTK       thousands of corner points (vertices) sent to the graphics
            chip per frame
CPU         milliseconds of processor work per frame
ACTOR       of that, the characters
WORLD       of that, the scenery
GPU         milliseconds the graphics chip needs per frame
ST%, MISSK  as on page 2 (waiting for memory, cache misses in thousands)
The lower rows divide the difference against AS SHIPPED by the number of
vertices left out: milliseconds per 1000 vertices, for the processor and for
the graphics chip. Leaving a model out also saves its fixed work (its
skeleton, its set-up), so for the characters this is the most a simpler
model could save.
CODE 3      for each of the six ways: vertices (in hundreds), CPU and GPU
            milliseconds times ten, then a check value
The game stands still only during these 39 seconds; it is never saved and
the disc starts each scene fresh.

SHA256SUMS.txt lists the sha256 of each file in the gdemu folder.
