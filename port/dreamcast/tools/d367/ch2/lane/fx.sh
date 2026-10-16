# fx.sh <name> <warp file> [pad file]: fixture k/fix/<name>-$L.json (T15_DATA + ch2)
T=/root/probe/lanes-20261016/ch2/tree/port/dreamcast/tools/d367; K=/root/probe/lanes-20261016/ch2/k
L=${L:-c2rW}
D=$(python3 -c "import importlib.util as u;s=u.spec_from_file_location('t','$T/test11/t11-fix.py');m=u.module_from_spec(s);s.loader.exec_module(m);print(m.T15_DATA)")
P=""; [ -n "${3:-}" ] && P="--pad $3"
python3 $T/test11/t11-fix.py $L $K/fix/$1-$L.json --data $D,${DATA_EXTRA:-ch2} --warp $2 $P | tail -c 100
