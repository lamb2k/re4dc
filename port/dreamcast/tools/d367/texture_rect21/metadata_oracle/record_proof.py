from pathlib import Path
import hashlib,json,subprocess
E=Path(__file__).resolve().parent;T=Path('/root/probe/codex-texture-rect21');SOURCE='845abb1f4ad3a2721d17f64899b6dc59d4bce66c'
sha=lambda b:hashlib.sha256(b).hexdigest()
paths={
 'port/dreamcast/game/platform/native_static.cpp':[(1610,1843),(4475,4522),(4650,4715),(5160,5365),(5370,5454)],
 'port/dreamcast/game/platform/room_occl.c':[(25,85),(155,180)],
 'port/dreamcast/tools/d367/texture_rect21/world_rect_provenance.h':None,
 'port/dreamcast/tools/d367/texture_rect21/provenance_certificates.inc':None,
 'port/dreamcast/tools/d367/texture_rect21/integration_world26.json':None,
}
proof={}
for p,spans in paths.items():
 b=subprocess.check_output(['git','-C',str(T),'show',SOURCE+':'+p]);assert b==(T/p).read_bytes(),p
 lines=b.decode().splitlines();excerpts=[]
 for first,last in spans or[(1,len(lines))]:excerpts.append(dict(first=first,last=min(last,len(lines)),lines=lines[first-1:last]))
 proof[p]=dict(source=SOURCE,sha256=sha(b),bytes=len(b),excerpts=excerpts)
refs={}
for p in (E.parent/'provenance-source-01/host05/summary.json',E.parent/'provenance-source-01/qualification-final01.json',E.parent/'provenance-source-01/SHA256SUMS',E.parent/'world26-programme-01/qualification-final.json',E.parent/'world26-programme-01/independent-program-qualification.json',Path('/mnt/c/Flycast-Evidence/re4-dreamcast/texture-consumers21-provenance-review-20261021/REVIEW.txt')):
 b=p.read_bytes();refs[str(p)]=dict(sha256=sha(b),bytes=len(b))
out=dict(source=SOURCE,status='STATIC_HOLD_SOURCE_PROOF',source_files=proof,external_evidence_pins=refs,
 limits=['Existing47 host cases use actual extracted source paths at b920; target behavior not certified','Root402 world26 certificate checks remain host-only; original R4ID/R4TC/PCL/OCCL/SG bytes retained','f42 binary qualification is static/link only and its candidate CRC data is held; no guest or repaired-programme ABI claim'])
(E/'source-proof-manifest.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps(dict(source_files=len(proof),references=len(refs),bytes=(E/'source-proof-manifest.json').stat().st_size)))