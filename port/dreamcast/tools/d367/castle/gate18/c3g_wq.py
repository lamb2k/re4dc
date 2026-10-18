"""c3g_wq.py: find recorded warp text bodies ('name <warpname>' ... 'dump') in transcripts commands/results."""
import sqlite3, re, sys
db = sqlite3.connect(r"C:\Game Dev\Emulators\re4dc-recovery\transcripts.db")
names = sys.argv[1:]
for nm in names:
    found = {}
    for t, c, r in db.execute("select timestamp,command,result from commands where command like ? or result like ? order by timestamp",
                              ('%name ' + nm + '%', '%name ' + nm + '%')):
        for txt in (c or "", r or ""):
            txt = txt.replace("\\n", "\n")
            for m in re.finditer(r"name " + re.escape(nm) + r"\b.*?\n\s*dump\b", txt, re.S):
                body = m.group(0)
                if len(body) < 1500: found.setdefault(body, t)
    print("=====", nm, len(found))
    for b, t in sorted(found.items(), key=lambda x: x[1]): print("--", t); print(b)
