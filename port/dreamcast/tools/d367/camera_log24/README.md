# Complete bounded camera log records

The old PS2CAM formatter can exceed the actual 256-byte logger. Its source call needs257 bytes at frame800 and264 atUINT_MAX, leaving a truncated viewport word and no newline. A fresh exact-source console capture and the old t2exact camera log both expose this. No missing nibble may be inferred.

Under existing PS2_PVS=1 measurement mode2 only, PS2CAM2 prints27 fixed8-digit hex words: UI frame, far float bits,12view,7projection,6viewport. Its full record is251 bytes including newline, leaving room for the NUL in the existing256-byte logger. No global logger buffer, renderer state, production knob or asset change. Existing PVS0 removes the changed region entirely. Target/off-image and new guest evidence remain separate.

camera_log_v2.py strictly parses complete new records, can expand a validated row into the old human-labelled syntax as an explicitly derived host file, and compiles the actual production formatter with its 256-byte boundary. Controls exercise0/800/UINT_MAX, exact25-word argument order, a swapped-argument mutant, old actual truncation, five malformed-row negatives and PVS0 preprocessing. No viewport reconstruction or rendered-frame/actor-pose guarantee.

Legacy estimates may consume only a subset of camera fields. The re-strip lane separately checks complete finite viewport0..3, zero offsets and positive extent; it does not use viewport4/5. That narrower proof does not turn a truncated legacy row into a complete25-float camera.

Run host controls with --tree /path/to/source --old-call old_camera_call.cpp.txt --out /dev/shm/NEW-unique-output. Input source and private captures are preserved; no SDK/guest runs from these tests. R1 forest captures/screenshots remain original, but its complete-camera data is rejected. A fresh measurement profile will explicitly disable batching because the existing PVS+batch make guard remains enforced. No speed comparison follows.
