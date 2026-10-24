from pathlib import Path
r=Path('/root/work/lanes/world-emit23-census')
p=r/'port/dreamcast/tools/d367/world_emit23/test_census.py';s=p.read_text()
s=s.replace('"header_sha256":hashlib.sha256(HEADER.read_bytes()).hexdigest(),"checks":checks,',
'''"header_sha256":hashlib.sha256(HEADER.read_bytes()).hexdigest(),
             "parser_sha256":hashlib.sha256((HERE/"census.py").read_bytes()).hexdigest(),
             "test_sha256":hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
             "integration_review_profile":{"SCENERY_SUBMIT_BATCH":1,"PS2_PVS":0,"selected_affine":"unapplied/unadmitted"},
             "checks":checks,''')
p.write_text(s)
p=r/'port/dreamcast/tools/d367/world_emit23/README.md';s=p.read_text()
s=s.replace('Room-code or other selected-affine', 'Room-code or other selected-affine')
s+='''\n## Ordered capture protocol repair\n\nIndependent review of2adba1332 found that the original parser checked a bag of\nrows without enforcing source event order. Reversed rows, a completed flush\nmoved after FRAME_END, a flush relabeled into the wrong active pass, and a\nthreshold above the captured frame could pass. This tools-only successor\nconsumes BEGIN, passes0/1/2, scoped flush/part/count closures and terminal\nFRAME_END in order. Flush IDs are globally contiguous from1 across passes.\nThreshold must be1..10000000 and not exceed the captured UI frame. Missing,\nunknown, duplicate and unsigned-out-of-range fields are refused.\n\nThe actual generated host log supplies twelve protocol mutations, all rejected,\nand a valid cross-pass flush positive. Earlier aggregate/safety controls remain.\nRuntime/header/make files are unchanged by this repair. Source integration\nreview is bounded to the actual SUBMIT_BATCH1/PVS0 profile; the selected-affine\nproposal is unapplied and unadmitted. No compatibility or qualification of that\nfuture patch follows from this census milestone. No SDK/guest gate has run.\n'''
p.write_text(s)
