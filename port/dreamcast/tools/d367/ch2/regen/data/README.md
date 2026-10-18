# ch2 / cast16 data sets: final assembly and gates (lane ch2regen, 2026-10-17)
- pakmatch.py / discscan.py: match target files in surviving paks and GD discs (raw or 2048, fp_iso reader).
- pakrec2.py: dc/tex.pak 13340bfa = texpack.build(16.x pak ae84c909 + pak17's entries for vq16-ch2 (3afc9415),
  vq16-c31 (c45c1bee), vq16-r200t, vq16-r200k and the ps2lib wep keys): byte-exact.
- asm.sh: dc/resident.bin cfcc77d6 = resident_keys pack + water_resident pack of the lists at 7711ec04 (byte-exact),
  then assemble.py: /root/re4data/private/ch2data-20261016 (1755/1778; the 23 missing loose 16-bit files are shadowed by
  tex.pak keys and absent from the base) and cast16data-20261016 (20/20), each file sha-checked against the
  n3-c4w-r10f payload manifest. dscopy.sh: bulk copy to re4-assets-private\ch2regen-20261018\datasets.
- build.sh / build2.sh: ch2-build.sh mW at origin/t15/int b5537823 (labels crmW, crcmW = census period 30).
- fx.sh / fx2.sh + fxov.py: t11-fix fixtures --data ch2,cast16 on the 16.3 base template; fxov.py adds every overlay of
  the arm (the template lists 6; t15/int's ch2 build also needs em35 em3b pl14 st1_0..3 st2_0).
- cr-run.sh: stage (harness stager) + run + delete disc; gates.py: gate table (TEX_CHECK, CAST-GC, shadowed keys).
