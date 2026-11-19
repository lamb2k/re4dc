S="/mnt/c/Game Dev/Emulators/final16-20261016/sh/strict.sh"
while [ $# -ge 2 ]; do echo "== $1 vs $2"; bash "$S" $1 $2; shift 2; done
