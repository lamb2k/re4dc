set -euo pipefail
L=/root/probe/lanes-20261018/ch4regen
mkdir -p $L/data/movies-288x192-full
cd $L/tree/port/dreamcast/tools
python3 - <<'P' > $L/data/movies.log 2>&1
import sys, json, pathlib, concurrent.futures as cf
sys.argv=['x']
import convert_route_movies as M
M.OUT=pathlib.Path('/root/probe/lanes-20261018/ch4regen/data/movies-288x192-full')
idx=M.afs_index()
names=['r212s00','r214s00','r215s00','r215s00c','r215s01','r215s02','r227s00','r227s00c','r227s01','r227s02','r228s00','r228s01','r228s02','r201s00','r203s00','r204s00','r206s00','r206s10','r206s20','r209s00','r20bs00']
with cf.ThreadPoolExecutor(3) as ex:
    res=list(ex.map(lambda n:M.one(n,idx),names))
for r in res: print(json.dumps(r)[:200])
P
cd $L/data/movies-288x192-full; sha256sum */*.seq
