"""c3g_gates.py SCENARIO_DIR... (WSL): ch3gate gate table - rooms entered, HALT/FAULT/MISSING, TEX_CHECK, CAST-GC
(tools/d367/cast_gc.py), LEON-GC (rfp result), and every log line naming a shadowed key (loads / texchk reads)."""
import json, re, subprocess, sys, os
CG = '/root/probe/lanes-20261018/ch3gate/tree/port/dreamcast/tools/d367/cast_gc.py'
KEYS = '3e3b16c1 35300dbb 69936e52 7035a62f b70cb3fd 628a66ab 1d5445c8'.split()
rows = []
for d in sys.argv[1:]:
    lp = d + '/capture/run-output.txt'
    log = open(lp, 'rb').read().decode('latin1')
    r = dict(run=os.path.basename(d.rstrip('/')))
    r['rooms'] = ','.join(dict.fromkeys(re.findall(r'room enter ([0-9a-f]+)', log)))
    for k, pat in (('halt', 'HALT'), ('missing', 'RE4DC MISSING'), ('fault', 'FAULT'), ('absent', 'package absent')):
        r[k] = log.count(pat)
    r['halt_lines'] = [l[:160] for l in log.splitlines() if 'HALT' in l or 'FAULT' in l or 'RE4DC MISSING' in l][:4]
    t = re.findall(r'texchk: frame=(\d+) fails=(\d+) skips=(\d+) meta_changes=(\d+) vram_changes=(\d+) binds=(\d+)', log)
    r['texchk'] = 'frame=%s fails=%s skips=%s meta=%s vram=%s binds=%s' % t[-1] if t else 'NO COVERAGE'
    r['texchk_fail_lines'] = [l[:160] for l in log.splitlines() if 'texchk: FAIL' in l][:4]
    p = subprocess.run(['python3', CG, lp], capture_output=True, text=True)
    r['castgc'] = {0: 'PASS', 1: 'FAIL', 2: 'NO CENSUS'}.get(p.returncode, 'rc%d' % p.returncode)
    r['castgc_detail'] = [l for l in p.stdout.splitlines() if ' GC' in l or 'MIXED' in l or 'FAIL' in l][:6]
    r['shadowed'] = {k: [l[:150] for l in log.splitlines() if k in l][:3] for k in KEYS if k in log}
    fp = d + '/cx-firstpass-check.json'
    if os.path.exists(fp):
        g = json.load(open(fp)); r['firstpass'] = g.get('overall')
    rf = d + '/rfp-result.json'
    if os.path.exists(rf):
        rr = json.load(open(rf)); r['leon_gc'] = rr.get('checks', {}).get('leon_gc'); r['discs_removed'] = rr.get('discs_removed')
    r['frames'] = (re.findall(r'frame[= ](\d+)', log) or ['?'])[-1]
    rows.append(r); print(json.dumps(r))
