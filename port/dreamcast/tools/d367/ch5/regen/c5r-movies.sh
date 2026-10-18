set -euo pipefail
# ch4regen movies.sh method for the st3 movies (convert_route_movies.one), tools at game-249effe5
S=/mnt/c/Users/lambd/AppData/Local/Temp/claude/C--Game-Dev-Emulators/c357f0f1-ecb5-45e4-b858-3f1d8ec8cd20/scratchpad/ch5regen
L=/root/probe/lanes-20261018/ch5regen
NAMES=$(grep 'movies-288x192-full' $S/missing-src.tsv | cut -f5 | tr -d '\r' | xargs -n1 basename | sed 's/[.]seq$//' | sort -u | tr '\n' ' ')
echo "$NAMES"
mkdir -p $L/movies/movies-288x192-full
cd $L/game-249effe5/port/dreamcast/tools
PYTHONDONTWRITEBYTECODE=1 python3 - $NAMES <<'P' > $L/movies/movies.log 2>&1 || tail -5 $L/movies/movies.log
import sys, json, pathlib, concurrent.futures as cf
names=sys.argv[1:]; sys.argv=['x']
import convert_route_movies as M
M.OUT=pathlib.Path('/root/probe/lanes-20261018/ch5regen/movies/movies-288x192-full')
idx=M.afs_index()
with cf.ThreadPoolExecutor(3) as ex:
    res=list(ex.map(lambda n:M.one(n,idx),names))
for r in res: print(json.dumps(r)[:200])
P
tail -3 $L/movies/movies.log
python3 $S/c5r_verify.py $S/missing-src.tsv $L/found.tsv $L/movies
