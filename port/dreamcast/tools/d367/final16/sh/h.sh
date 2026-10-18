# h.sh <arm>: clone the st3 lane harness for an arm (lane final16)
E=/mnt/c/Flycast-Evidence/re4-dreamcast/final16-20261016; mkdir -p $E
[ -d $E/h-$1 ] && rm -rf $E/h-$1/programs && rm -rf $E/h-$1.old && mv $E/h-$1 $E/h-$1.old
python3 "/mnt/c/Game Dev/Emulators/final16-20261016/py/clone_h.py" "/mnt/c/Game Dev/Emulators/re4-rfp-20261015-st3e3" $E/h-$1 $1 /root/probe/lanes-20261016/final16/build | cut -c1-200
[ -d $E/h-$1.old/scenarios ] && cp -r $E/h-$1.old/scenarios/. $E/h-$1/scenarios/ && rm -rf $E/h-$1.old
true
