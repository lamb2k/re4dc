# knob-off identity: the test 15 rP arm from the lane tree vs dad92dad411cc45b (ch5found16 / stress16b result, same knob set)
L=/root/probe/lanes-20261016/final16
bash "/mnt/c/Game Dev/Emulators/final16-20261016/sh/build.sh" fk rP
/opt/toolchains/dc/sh-elf/bin/sh-elf-objcopy -O binary -R .stack $L/build/out-fkrP/re4dc-game.elf /tmp/fkrP.bin 2>/dev/null
echo "fkrP image $(sha256sum < /tmp/fkrP.bin | cut -c1-16) $(stat -c %s /tmp/fkrP.bin) (base: dad92dad411cc45b 3376304) HEAD $(git -C $L/tree rev-parse --short=8 HEAD)"
(cd $L/build/out-fkrP && sha256sum *.ovl | cut -c1-8,66- | tr '\n' ' '); echo
rm -f /tmp/fkrP.bin
