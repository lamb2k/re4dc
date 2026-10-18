import re, sys
t = open(sys.argv[1], encoding='utf-8').read().split('\n##CALL ')[1:]
t.sort(key=lambda b: b[:24])
for b in t:
    h, body = b.split('\n', 1)
    body = body.split('\n##OUT', 1)[0]
    if re.search(r'Get-Content|rg -n|git -C \S+ (show|diff|log|status)|Select-String', body[:400]) and not re.search(r'--output|mkdir|write_text|copy|cp |apply_patch|\*\*\* ', body[:4000]):
        continue
    print(h[:24], body[:300].replace('\\\\', '\\').replace('\n', ' '))
