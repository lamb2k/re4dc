# Shared BGM bank on the final-room route

r300 and r332 both use bio4midi member 7. The existing prebuilt image was
marked for BGM0 (slot 3), so r332's BGM1 channel rejected it as the wrong
slot. Restoring the raw bank fixes that channel through AICA_SPILL's existing
runtime arena path, but loses r300's prebuilt bank. The raw diagnostic is
not a chapter-union candidate.

The existing default-off AICA_SPILL path now also accepts that shared
prebuilt image for BGM1 when both the image and actual frozen layout have
zero BGM1 reservation. Version, sample count, wavetable FNV, source ARAM size
and encoded image-size checks remain required. Placement uses the existing
high-arena block and its room-reset/room-bank priority. Empty, rounded-size
overflow, absent arena, occupied high block and insufficient capacity refuse.
The layout and bank bytes stay unchanged; no new knob or recipe change.

Host regression extracts the actual admission, map, free and prepare
functions. AICA_SPILL 0/1 passes malformed banks, legacy fixed BGM0/BGM1,
replacement/map cleanup, room reset, room-bank priority and placement
failure cases. The host stubs isolate these contracts; guest gates verify
the actual converted bank and layout.

Fresh current T15REC i18d8rP: program SHA9dbb2434 and all ten overlays are
byte-identical to frozen7d7c05ab; missing0/_end8c400eb8. New source draft
pins and actual program/overlay hashes are in the C evidence folder.

Flycast i18f2mW ELF c513756fc1903649727e0064efb26f3553d3aff301f93021803c332d4d01a1d3:
- r332/bgm1:59.28s; shared165916 B/32000Hz prebuilt at arena top1b42a0,
  original frozen arena1004192, combined arena banks811008 and193184 left;
  nine prebuilt/zero runtime banks, snd_fail0. Restored fight stream plays
  with under0 in the measured window.
- r300/bgm0:58.95s; same bank165916 B/32000Hz remains prebuilt in BGM0,
  snd_fail0; natural source movie30000 terminal1.

These are audio gates only. r332 TEX fails on source em31 pair
be2ba844-3c99990a (color97358f79-709e5890/maskf4aceca5-a8635734);
the live boss still has no NMRS draw, with later motion/texture reads.
Saddler model/material work remains boss18. r300's known source-Leon guard
knobs remain out of the recipe and its CAST/LEON checks fail. No whole-room,
full-fight, stable residency or physical-console acceptance.

Private existing CH5F stream set is now restored (41 entries, fits56):
19 existing checked payloads reused and22 missing source streams converted,
67700736 B; mirrored SHA256SUMS
6875550e0ca66211550c28475a692108429aacaee4c2010ef4b1d85d4b40ec4e.
This is a private Island fixture set, not shared disc packaging.

Evidence: C:/Flycast-Evidence/re4-dreamcast/island18-20261018/
aica-shared-prebuilt-guest-gate.json, aica-shared-prebuilt-draft/,
identity/aica-shared-prebuilt-off-identity.json, h-i18f2/scenarios/.
