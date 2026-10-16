set -e
T=/root/probe/lanes-20261016/ch2/tree/port/dreamcast/tools
W=/root/probe/lanes-20261016/ch2/em16; rm -rf $W; mkdir -p $W; cd $W
true
python3 /mnt/c/tmp/ch2/gcx.py em-src em/em16.drs
sha256sum em-src/em/em16.drs
printf 'em/em16.drs\n' > em-tex.manifest
python3 $T/prepare_native_ui.py em-src em-tex.manifest tex-em > tex-em.log 2>&1 || { tail tex-em.log; exit 1; }
tail -c 300 tex-em.log; echo; ls tex-em | wc -l
echo '{"source_complete": false, "profile": "diagnostic: no hot set (every streamed clip loads on first use; the em11 r117 recipe)", "union": {"source_arc_indices": []}}' > em16-hot.json
python3 $T/prepare_enemy_motions.py --source em-src/em/em16.drs --output prep-em16 --hot-audit em16-hot.json --diagnostic-incomplete-prefetch --textures tex-em > prep.log 2>&1 || { tail -20 prep.log; exit 1; }
tail -c 600 prep.log; echo
ls -la prep-em16 | head; ls prep-em16/mot | wc -l
python3 -c "import struct;d=open('prep-em16/em16.drs','rb').read(0x28);print('hdr24',struct.unpack_from('<I',d,0x24)[0])"
