"""rollx.py PATTERN OUT FILES...: dump Codex rollout tool calls (and their outputs, truncated) whose text matches PATTERN, in order."""
import json, re, sys
pat = re.compile(sys.argv[1]); out = open(sys.argv[2], 'w', encoding='utf-8')
for fn in sys.argv[3:]:
    calls = {}
    for line in open(fn, encoding='utf-8', errors='replace'):
        try: o = json.loads(line)
        except Exception: continue
        p = o.get('payload') or {}
        t = p.get('type')
        if t in ('function_call', 'custom_tool_call'):
            s = p.get('arguments') or p.get('input') or ''
            if pat.search(s):
                calls[p.get('call_id')] = 1
                out.write(f"\n##CALL {o.get('timestamp')} {fn[-50:]} {p.get('name')}\n{s}\n")
        elif t in ('function_call_output', 'custom_tool_call_output') and p.get('call_id') in calls:
            s = p.get('output'); s = s if isinstance(s, str) else json.dumps(s)
            out.write(f"##OUT {o.get('timestamp')}\n{s[:1500]}\n")
