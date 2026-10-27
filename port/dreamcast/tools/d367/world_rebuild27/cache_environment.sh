#!/usr/bin/env bash
# Source before Windows fp_run.py from WSL. Does not start a guest.
# WSL exports alone do not reach Windows children; reader stdout must be UTF-8.
export RE4DC_EMU=console RE4DC_CONSOLE_DYNAREC=no RE4DC_GD_PROFILE=gdemu
export RE4DC_MAX_FLYCASTS=16
export PYTHONUTF8=1 PYTHONIOENCODING=utf-8:backslashreplace
for cache_env_name in RE4DC_EMU RE4DC_CONSOLE_DYNAREC RE4DC_GD_PROFILE RE4DC_MAX_FLYCASTS PYTHONUTF8 PYTHONIOENCODING; do
    case ":${WSLENV-}:" in
        *:"${cache_env_name}":*) ;;
        *) export WSLENV="${WSLENV:+${WSLENV}:}${cache_env_name}" ;;
    esac
done
unset cache_env_name
if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
    [[ "${1-}" == --verify && "$#" == 1 ]] || { echo 'Source this file, or run --verify (host only).' >&2; exit 2; }
    cache_env_python=/mnt/c/Users/lambd/AppData/Local/Programs/Python/Python312/python.exe
    "$cache_env_python" -c 'import os,sys,json,hashlib; from pathlib import Path; keys=("RE4DC_EMU","RE4DC_CONSOLE_DYNAREC","RE4DC_GD_PROFILE","RE4DC_MAX_FLYCASTS","PYTHONUTF8","PYTHONIOENCODING"); actual={k:os.environ.get(k) for k in keys}; assert [actual[k] for k in keys]==["console","no","gdemu","16","1","utf-8:backslashreplace"],actual; exe=Path(r"C:\Flycast-Evidence\re4-dreamcast\flycast-console-bin\flycast-console.exe"); digest=hashlib.sha256(exe.read_bytes()).hexdigest(); assert digest=="8e6c49871013c25b1a1c77c789167e3aaed8193e828adb7e2bbce9248d2add4a",digest; assert sys.stdout.encoding.lower()=="utf-8",sys.stdout.encoding; print(json.dumps({"scope":"Windows host/environment only; no guest","environment":actual,"emulator_sha256":digest,"stdout_encoding":sys.stdout.encoding,"replacement_character_probe":"\ufffd"},ensure_ascii=False))'
    unset cache_env_python
fi