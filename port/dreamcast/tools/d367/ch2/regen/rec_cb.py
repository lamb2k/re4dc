"""Rebuild cast_bundle.py from the transcript DB: the 09-26 Write + the three recorded py patches, in order."""
import sqlite3, re, hashlib
DB = r'C:\Game Dev\Emulators\re4dc-recovery\transcripts.db'
c = sqlite3.connect(DB)
t = c.execute("select content from files where path like '%cast_bundle.py' and kind='write'").fetchone()[0]
for ts in ('2026-09-26T15:20:13.722Z', '2026-09-26T15:20:41.689Z', '2026-09-26T15:53:32.241Z'):
    cmd = c.execute("select command from commands where timestamp=? and command like '%cast_bund%'", (ts,)).fetchone()[0]
    body = cmd.split("<<'EOF'\n", 1)[1].split('\nEOF\n', 1)[0]
    body = body.replace("open(p,encoding='utf-8').read()", 'T').replace('open("cast_bundle.py", encoding="utf-8").read()', 'T')
    body = re.sub(r"open\(p,'w'[^\n]*\n", 'OUT.append(t)\n', body)
    body = re.sub(r'open\("cast_bundle.py", "w"[^\n]*\n?', 'OUT.append(s)\n', body)
    OUT = []
    exec(body, {'T': t, 'OUT': OUT, 'print': lambda *a: None, '__builtins__': __builtins__})
    t = OUT[0]
open('rec/cast_bundle.py', 'w', encoding='utf-8', newline='\n').write(t)
print('lines', t.count('\n'), 'sha', hashlib.sha256(t.encode()).hexdigest())
r = c.execute("select result from commands where timestamp='2026-10-04T00:04:19.752Z'").fetchone()[0]
open('rec/cb-1004.txt', 'w', encoding='utf-8', newline='\n').write(r)
