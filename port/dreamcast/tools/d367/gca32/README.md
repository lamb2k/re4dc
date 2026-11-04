# gca32: Disc 2 chapter 3-2 GC-ASSET (cgca32, cpic32b)

Generator: `gen.sh` (objects, Ashley partner, pictures) then `mk.py` (stores `cgca32-20261103`, `cpic32b-20261103`).

- et1400 / et0c00 emptied in r205 r20a r20b: "drop it where the PS2 dropped it" (no look check needed, coordinator 11-04).
  Neither model is in any PS2 room's ETM (r20a r20b r205 r209 r113 r201 r200 r20c r20d; r113 is the room whose GameCube
  et0c00 the shipped bytes mirror). Evidence: `python3 etm_names.py <dir of PS2 .dat files>/ r20a r20b r205 r209 r113 r201 r200 r20c r20d`
  (PS2 USA ISO BIO4DAT.AFS members, extracted by `afsx.py`).
