set -e
L=/root/probe/lanes-20261016/ch4found; T=$L/tree/port/dreamcast/tools; W=$L/snd; cd $W
C23=/root/probe/lanes-20261014/ch22/snd/mirror-c23
rm -rf str-castle str-c4chk
nice python3 $T/aica_banks.py streams --mirror $C23 --out str-castle --streams castle > str-castle.log 2>&1 || { tail str-castle.log; exit 1; }
nice python3 $T/aica_banks.py streams --mirror $C23 --out str-c4chk --streams ch4 > str-c4chk.log 2>&1
ls -l str-castle/bgm/aica_str.dat; sha256sum str-c4/bgm/aica_str.dat str-c4chk/bgm/aica_str.dat | cut -c1-16
python3 - <<'P'
import struct
d=open('str-castle/bgm/aica_str.dat','rb').read(8192)
m,n=struct.unpack_from('<2I',d,0); print(hex(m),n)
e=[struct.unpack_from('<8I',d,16+32*i) for i in range(n)]
print('first a_ofs', e[0][6], 'last', e[-1][6])
c3=open('/root/probe/lanes-20261016/ch3found/snd/str-ch3/bgm/aica_str.dat','rb').read(16+32*55)
e3=[struct.unpack_from('<8I',c3,16+32*i) for i in range(55)]
print('ch3 entries same except offsets', all(a[:6]==b[:6] and a[6]==b[6]+2048 and (b[7]==0 or a[7]==b[7]+2048) for a,b in zip(e,e3)))
P
rm -rf str-c4chk
