from pathlib import Path
import ast,json,hashlib
L=Path(r'C:\Game Dev\Emulators\codex-lanes\castle18');src=L/'owned-window-recovered-j-r201-Green-Herb-use-window-ready-still.py';dst=L/'owned-window-recovered-j-r201-Green-Herb-use-board-ready-still.py';assert not dst.exists()
s=src.read_text();old="  assert cur==board and 0x8c000000<=board<0x8cfff000,('unexpected source board',hex(cur),hex(board));inhand=u32(pp+0x10);"
new="""  if cur!=board or not(0x8c000000<=board<0x8cfff000):
   transition(set());row['waiting_source_puzzle_board_initialization']={'cur':hex(cur),'board':hex(board)};time.sleep(.1);continue
  inhand=u32(pp+0x10);"""
assert s.count(old)==1;s=s.replace(old,new);ast.parse(s);dst.write_text(s,newline='\n')
(L/'resume-herb-board-ready-review.json').write_text(json.dumps(dict(source_sha256=hashlib.sha256(src.read_bytes()).hexdigest(),candidate_sha256=hashlib.sha256(dst.read_bytes()).hexdigest(),defect='Actual134 original inventory opened, source board pointer allocated while current board0 during initialization. Guard closed903HP with herb intact.135 incorrectly prepared lever; no route input; exact owned close retained menu state. Its prepared scope incorrectly claimed healing; actual immutable checkpoints override that label.',repair='Use existing original-J136 source-proven neutral board initialization wait before dereferencing or selecting. Whole guest bound, health, item selection, no item move and exact PID guards retained.',validation='AST compilation and exact one predicate replacement; runtime pending.'),indent=2)+'\n')
print(dst)
