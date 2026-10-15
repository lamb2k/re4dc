RE4 DREAMCAST BENCHMARK DISC POC101 (2026-10) - THIS IS NOT THE GAME
=====================================================================

This disc only measures how fast the RE4 Dreamcast port could run at the
busy r101 village cross with every planned speed-up stacked. It cannot be
played: there is no title menu and no New Game, and it saves nothing (it
does not touch your VMU). To play, use the current test release:
https://github.com/lamb2k/re4dc/releases

Build SHA_PLACEHOLDER: the test 14 game data and program (with SH4ZAM
render only), the benchmark's own measuring code, and the POC101 layers.
Every speed-up layer is a switch inside ONE program, so the rows below
differ only in which switches are on. Rows marked * change the picture
(an approximation, or a labelled stand-in); judge them on the still sheet,
not on speed alone.

Each row is the same 30 second scene: Leon stands by the burning cross
while the villagers attack (at most 6 at once), with fire, haze and
torches. Each row starts from a soft reset. The banner on screen names the
row being run ("NOT THE GAME - POC ...").

Rows and sweeps on this disc
SCENES_PLACEHOLDER

ALL OFF is test 14 as it ships. ALL OFF 2 repeats it at the end, so the
difference between the two shows the run-to-run noise. ALL ON is every
layer except the alternative Leon rung (LEON U70), which has its own row.

The last scene freezes the game at one room frame and draws it with each
layer alone, then all on; its page shows the CPU and GPU change of each.

How to run it
1. Copy the four files in the gdemu folder (disc.gdi, track01.bin,
   track02.raw, track03.bin) to a new folder on your SD card, the same way
   as any GDEMU game. The menu lists it as "RE4DC BENCHMARK (NOT THE GAME)".
2. A start screen says what the disc is. Press START (or wait 20 seconds),
   then put the controller down until the results screen. The rows run one
   after the other, each from a fresh start.
3. The results appear on several pages. Press B (or Y) for the next page.
   Press A on any page to run everything again (optional).
4. Photograph every page (sharp, straight on, all text readable) and type
   out each page's CODE line. Send them with the build number above.

The pages: 1 speed per row (FPS, CPU and GPU ms), 2 CPU per picture by
part, 3 drawn and skipped ticks, 4 the frozen sweep, 5 the skipped tick by
part, 6 what each row turns on.
