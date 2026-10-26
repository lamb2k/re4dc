cd "/c/Flycast-Evidence/re4-dreamcast/vis-census26-20261026"
S=/mnt/c/Users/lambd/AppData/Local/Temp/claude/C--Game-Dev-Emulators/3eafc4fe-ad61-4030-8af6-7352db985ae8/scratchpad
for r in $(ls pkg); do MSYS_NO_PATHCONV=1 wsl -d Ubuntu-24.04 -u root -- bash $S/noocc.sh $r; python tools/pvs/census.py eval work/$r 2>&1 | tail -1; done
