set -e
L=/root/probe/lanes-20261016/final16
python3 "/mnt/c/Game Dev/Emulators/final16-20261016/py/ed8.py"
cd $L/snd; rm -rf str-f
nice python3 $L/tree/port/dreamcast/tools/aica_banks.py streams --mirror /root/probe/lanes-20261014/ch22/snd/mirror-c23 --out str-f --streams ch5f > str-f.log 2>&1 || { tail str-f.log; exit 1; }
tail -3 str-f.log; ls -la str-f/bgm/aica_str.dat /root/probe/lanes-20261016/ch5found/snd/str-c5/bgm/aica_str.dat
python3 - <<'PY'
a=open('/root/probe/lanes-20261016/ch5found/snd/str-c5/bgm/aica_str.dat','rb').read()
b=open('/root/probe/lanes-20261016/final16/snd/str-f/bgm/aica_str.dat','rb').read()
# entries after the 2048-byte header: the ch5 data region must be a prefix of the new file's data region
print('ch5 data region identical prefix:', b[2048:len(a)]==a[2048:])
PY
