"""Source-linked QA auto-menu chain; no guest execution or evidence replacement."""
import re
PATTERNS=[r'^room lifecycle: phase=enter room=101 generation=1\b',r'^qa: 33 presets in 6 chapters$',r'^qa: auto diagnostics \([1-9][0-9]* bytes, [1-9][0-9]* QR pages\)$',r'^qa: auto teleport /cd/dc/qa/r103\.txt$',r'^warp: qa: teleport: soft reset requested\b',r'^--SOFT_RESET START!!$',r'^warp: qa fixture /cd/dc/qa/r103\.txt \([1-9][0-9]* bytes\)$',r'^warp: qa: preset armed at soft reset\b',r'^--SOFT_RESET END!!$',r'^room lifecycle: phase=enter room=103 generation=2\b']
def observe(text):
 positions=[];at=0
 for pattern in PATTERNS:
  m=re.search(pattern,text[at:],re.M)
  if not m:return dict(ordered_auto_menu_chain=False,matched_prefix=len(positions),expected=pattern,positions=positions)
  at+=m.end();positions.append(at)
 return dict(ordered_auto_menu_chain=True,matched_prefix=len(PATTERNS),positions=positions,label='Automated QA menu-warp fixture; not manual human progression')

def controls(text):
 assert observe(text)['ordered_auto_menu_chain']
 mutants={
 'wrong_file':text.replace('/cd/dc/qa/r103.txt','/cd/dc/qa/r102.txt'),
 'missing_reset_request':re.sub(r'^warp: qa: teleport: soft reset requested.*\n','',text,flags=re.M),
 'missing_reset_arm':re.sub(r'^warp: qa: preset armed at soft reset.*\n','',text,flags=re.M),
 'old_room103_only': 'room lifecycle: phase=enter room=103 generation=2 frames=0\n'+re.sub(r'^room lifecycle: phase=enter room=103 generation=2.*\n','',text,flags=re.M),
 'wrong_generation':text.replace('phase=enter room=103 generation=2','phase=enter room=103 generation=1'),
 'missing_ui':re.sub(r'^qa: auto diagnostics.*\n','',text,flags=re.M)}
 result={k:observe(v)['ordered_auto_menu_chain'] for k,v in mutants.items()};assert all(not x for x in result.values());return result

