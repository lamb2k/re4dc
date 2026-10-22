from pathlib import Path
import subprocess,tarfile,io,shutil,sys
pin="33fa4850cacb30dd0ad35485ef035526ec4ce782"
source=Path(sys.argv[1]).resolve();dest=Path(sys.argv[2]).resolve()
if dest.exists():raise SystemExit("destination exists; preserve it")
if subprocess.check_output(["git","-C",str(source),"rev-parse","HEAD"],text=True).strip()!=pin:raise SystemExit("wrong SDK pin")
if subprocess.check_output(["git","-C",str(source),"status","--porcelain"],text=True).strip():raise SystemExit("SDK source dirty")
data=subprocess.check_output(["git","-C",str(source),"archive",pin])
dest.mkdir()
with tarfile.open(fileobj=io.BytesIO(data)) as tf:tf.extractall(dest,filter="data")
p=Path(__file__).resolve().parent
shutil.copyfile(p/"shz_bounds.h",dest/"include/sh4zam/shz_bounds.h")
shutil.copyfile(p/"shz_bounds.c",dest/"source/shz_bounds.c")
f=dest/"source/shz_bounds.c";f.write_text(f.read_text().replace('#include "shz_bounds.h"','#include "sh4zam/shz_bounds.h"'))
f=dest/"CMakeLists.txt";s=f.read_text().replace("set(SHZ_SOURCES\n","set(SHZ_SOURCES\n    source/shz_bounds.c\n",1).replace("set(SHZ_INCLUDES\n","set(SHZ_INCLUDES\n    include/sh4zam/shz_bounds.h\n",1);f.write_text(s)
print("Materialized clean SDK pin",pin,"with generic bounds addition",dest)
