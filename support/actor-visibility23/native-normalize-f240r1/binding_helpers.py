"""Native absolute path binding for this read-only WSL normalizer."""
from pathlib import Path
def native_path(value):
 value=str(value)
 if len(value)>2 and value[1]==":" and value[0].lower()=="c":value="/mnt/c/"+value[3:].replace(chr(92),"/")
 prefix=chr(92)*2+"wsl.localhost"+chr(92)+"Ubuntu-24.04"+chr(92)
 if value.startswith(prefix):value="/"+value[len(prefix):].replace(chr(92),"/")
 p=Path(value)
 if not p.is_absolute():raise ValueError("absolute pinned path required: "+value)
 return p
