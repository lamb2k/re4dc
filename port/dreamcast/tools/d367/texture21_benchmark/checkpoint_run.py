#!/usr/bin/env python3
"""Isolated fp_run adapter: original Flycast AutoSaveState and owned graceful close."""
import argparse
import ctypes
import importlib.util
from pathlib import Path
import re
import shutil
import subprocess
import sys

p=argparse.ArgumentParser(add_help=False);p.add_argument('--checkpoint-seed')
a,remaining=p.parse_known_args()
spec=importlib.util.spec_from_file_location('baseline_fullplay',Path(__file__).resolve().parents[1]/'fullplay/fp_run.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
original_popen=subprocess.Popen

class Guest:
    def __init__(self,process):self.process=process
    @property
    def pid(self):return self.process.pid
    @property
    def returncode(self):return self.process.returncode
    def poll(self):return self.process.poll()
    def wait(self,*args,**kwargs):return self.process.wait(*args,**kwargs)
    def kill(self):return self.process.kill()
    def terminate(self):
        # The original castle harness uses exactly this close/save mechanism.
        # Only the guest's SDL_app HWND is targeted. Outer capture pins image/PID.
        for hwnd in m.windows_of(self.pid):
            name=ctypes.create_unicode_buffer(256);m.user32.GetClassNameW(hwnd,name,256)
            if name.value=='SDL_app':m.user32.PostMessageW(hwnd,0x10,0,0)
        try:self.process.wait(timeout=2)
        except subprocess.TimeoutExpired:self.process.terminate()


def popen(command,*args,**kwargs):
    guest=Path(str(command[0])).name.lower()=='flycast.exe'
    if guest:
        cap=Path(kwargs['cwd']);cfg=cap/'emu.cfg';text=cfg.read_text()
        for key,value in [('AutoSaveState','yes'),('AutoLoadState','yes' if a.checkpoint_seed else 'no'),('SavestateSlot','0')]:
            text=re.sub(r'(?m)^Dreamcast\.'+key+r'\s*=.*\n?','',text)
            text=text.replace('[config]\n','[config]\nDreamcast.'+key+' = '+value+'\n',1)
        if a.checkpoint_seed:
            seed=Path(a.checkpoint_seed)
            if not (seed/'disc.state').is_file():raise ValueError('authenticated state absent')
            for file in seed.iterdir():
                if file.is_file():shutil.copyfile(file,cap/'data'/file.name)
        cfg.write_text(text)
    process=original_popen(command,*args,**kwargs)
    return Guest(process) if guest else process

subprocess.Popen=popen
sys.argv=[sys.argv[0]]+remaining
m.main()
