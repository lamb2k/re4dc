"""Synthetic FORMAT controls only; no fixture certifies a real runtime."""
import copy
import hashlib
import json
import unittest
from pathlib import Path
import parse_owner_witness as p


def word(value):
 return p.struct.unpack("<I", p.struct.pack("<f", value))[0]

def row(name, **kw):
 d = {spec.split(":")[0]: 0 for spec in p.SCHEMA[name].split()}
 d.update(kw)
 return name, d

def render(records):
 lines = []
 for name, values in records:
  fields = []
  for spec in p.SCHEMA[name].split():
   key, _, kind = spec.partition(":"); value = values[key]
   if kind.startswith("w"): value = ",".join(f"{v:08x}" for v in value)
   elif kind == "p": value = f"0x{value:x}"
   elif kind == "h8": value = f"{value:08x}"
   elif kind == "h": value = f"{value:x}"
   fields.append(key + "=" + str(value))
  lines.append("native-prefix: " + name + " " + " ".join(fields))
 return ("\n".join(lines) + "\n").encode()

def fixture(mode=2, roles=(True, True), keep=True):
 records = [row("AV23WINDOW", event=1, frame=100, mode=mode, mask=0x40 if mode == 2 else 0x20, left=599, once=1)]
 for n in range(1, 601):
  records.extend([row("AV23", frame=99+n, mode=mode, n=n, query=4 if n == 1 else 0, sections=4 if n == 1 else 0, hidden=2 if n == 1 else 0, would=20 if n == 1 else 0, skip=20 if n == 1 and mode == 2 else 0, tri=10 if n == 1 and mode == 2 else 0), row("AV23WORK", frame=99+n)])
 records.extend([row("AV23WINDOW", event=3, frame=700, mode=0, mask=0x40 if mode == 2 else 0x20, left=0, once=1),
                 row("AV23OWNER", complete=1, qualified=1, mode=mode, binds=600, owner=0x8c010000, id=0x2b, serial=4, epoch=5, life=6, samples=4, maxlines=39)])
 for role in range(2):
  on = roles[role]
  records.append(row("AV23OWNER_PART", role=role, info=0x8c020000+role*0x100 if on else 0,
                     query=(2 if keep else 1) if on else 0, bound=(2 if keep else 1) if on else 0,
                     potential=int(on), would=10 if on else 0, skip=int(on and mode == 2),
                     positions=10 if on and mode == 2 else 0, triangles=5 if on and mode == 2 else 0))
 for role in range(2):
  if not roles[role]: continue
  for potential in ((0, 1) if keep else (1,)):
   slot = role*2+potential
   records.extend([
    row("AV23OWNER_SAMPLE", slot=slot, token=slot+1, workspace=100+slot, mode=mode, owner=0x8c010000, id=0x2b, serial=4, epoch=5, life=6, role=role, info=0x8c020000+role*0x100),
    row("AV23OWNER_SOURCE", slot=slot, flags=1, room=0x119, game=7, ui=888, lod=role, meshlet=9, path=role, nv=10, nt=5, potential=potential, committed=int(mode == 2 and potential)),
    row("AV23OWNER_ADDR", slot=slot, positions=0x8c030000, blob=0x8c040000, records=0x8c050000),
    row("AV23OWNER_BOX", slot=slot, words=[word(1)]*3+[word(2)]*3),
    row("AV23OWNER_VIEW", slot=slot, words=[word(1)]*25),
    row("AV23OWNER_WORLD", slot=slot, stage=5 if potential else 3, field=5 if role == 0 else 7, result=potential, storage=1, current_storage=1, metadata=2, current_metadata=2),
    row("AV23OWNER_RECEIPT", slot=slot, owner=1, complete=1, epoch=4, stamp=4, frame=888, current_frame=888, scene=9, current_scene=9),
    row("AV23OWNER_COVER", slot=slot, coverage=0xd80, required=0xd80, room=0x119, bytes=1376, version=2),
    row("AV23OWNER_RANGE", slot=slot, near=word(10), far=word(25000), current_near=word(10), current_far=word(20000))])
 return records

def get(records, name, slot=None):
 return next(v for n, v in records if n == name and (slot is None or v.get("slot") == slot))

class ParserControls(unittest.TestCase):
 def good(self, records):
  r = p.parse(render(records)); self.assertTrue(r["format_complete"], r); self.assertFalse(r["qualified"]); return r
 def bad(self, records):
  r = p.parse(render(records)); self.assertFalse(r["format_complete"], r); self.assertFalse(r["qualified"]); self.assertIn("error", r)
 def test_full_mode2_four_slots(self):
  r = self.good(fixture()); self.assertEqual(r["reported_owner2b_pre_position_skips"], 2); self.assertEqual(len(r["samples"]), 4)
 def test_mode1_potential_is_not_actual(self):
  r = self.good(fixture(1)); self.assertEqual(r["reported_owner2b_potential_sections"], 2); self.assertEqual(r["reported_owner2b_pre_position_skips"], 0)
 def test_one_role_still_requires_both_role_rows(self):
  self.assertEqual(len(self.good(fixture(roles=(True, False)))["samples"]), 2)
 def test_potential_only_expected_slots(self):
  self.assertEqual([s["slot"] for s in self.good(fixture(keep=False))["samples"]], [1, 3])
 def test_shorter_current_far_is_valid(self):
  self.good(fixture())  # Actual ready accepts requested_far<=retained far.
 def test_refused_draw_never_claims_skip(self):
  r = self.good(fixture()); self.assertEqual(r["refused_draw_samples"], 2); self.assertFalse(r["samples"][0]["actual_pre_position_skip"])
 def test_every_continuation_must_exist(self):
  for name in p.ROWS:
   with self.subTest(name=name):
    a = fixture(); a.pop(next(i for i, x in enumerate(a) if x[0] == name)); self.bad(a)
 def test_every_continuation_duplicate_rejected(self):
  for name in p.ROWS:
   with self.subTest(name=name):
    a = fixture(); i = next(i for i, x in enumerate(a) if x[0] == name); a.insert(i, copy.deepcopy(a[i])); self.bad(a)
 def test_missing_either_role(self):
  for role in (0, 1):
   a = fixture(); a.pop(next(i for i, (n, v) in enumerate(a) if n == 'AV23OWNER_PART' and v['role'] == role)); self.bad(a)
 def test_raw_word_counts_exact(self):
  for name in ('AV23OWNER_BOX', 'AV23OWNER_VIEW'):
   for delta in (-1, 1):
    a = fixture(); v = get(a, name)['words']; v.pop() if delta < 0 else v.append(0); self.bad(a)
 def test_range_width_exact(self):
  d = render(fixture()).replace(b'near=41200000', b'near=1200000', 1); self.assertFalse(p.parse(d)['format_complete'])
 def test_truncated_or_extra_field(self):
  for transform in (lambda d: d.replace(b' life=6', b'', 1), lambda d: d.replace(b' life=6', b' life=6 spare=1', 1)):
   self.assertFalse(p.parse(transform(render(fixture())))['format_complete'])
 def test_summary_qualification_and_failures(self):
  for key, value in [('complete', 0), ('qualified', 0), ('fail', 2), ('binds', 599), ('id', 0x2a), ('life', 0), ('unattributed', p.MAX)]:
   a = fixture(); get(a, 'AV23OWNER')[key] = value; self.bad(a)
 def test_counters_and_overflow(self):
  for key, value in [('query', p.MAX), ('bound', 0), ('potential', 3), ('would', 0), ('skip', 0), ('positions', 9), ('triangles', 0)]:
   a = fixture(); get(a, 'AV23OWNER_PART')[key] = value; self.bad(a)
 def test_window_600_and_complete_required(self):
  for n in ('AV23', 'AV23WORK', 'AV23WINDOW'):
   a = fixture(); a.pop(next(i for i, x in enumerate(a) if x[0] == n)); self.bad(a)
  a = fixture(); a[-1][1]['current_far'] = word(30000); self.bad(a)
 def test_cancel_or_mode0_refuses(self):
  for key, value in [('event', 4), ('left', 1), ('mode', 2)]:
   a = fixture(); ends = [v for n, v in a if n == 'AV23WINDOW']; ends[1][key] = value; self.bad(a)
  a = fixture(); get(a, 'AV23WINDOW')['mode'] = 0; self.bad(a)
 def test_owner_lifetime_and_slot_token(self):
  for key, value in [('owner', 0), ('serial', 99), ('epoch', 0), ('life', 99), ('role', 1), ('workspace', 9999), ('token', 0)]:
   a = fixture(); get(a, 'AV23OWNER_SAMPLE')[key] = value; self.bad(a)
  a = fixture(); get(a, 'AV23OWNER_SAMPLE', 1)['token'] = 1; self.bad(a)
 def test_potential_requires_actual_ready_receipt(self):
  for name, key, value in [('WORLD', 'result', 0), ('WORLD', 'stage', 4), ('WORLD', 'field', 6), ('WORLD', 'current_storage', 9), ('WORLD', 'current_metadata', 9), ('RECEIPT', 'owner', 0), ('RECEIPT', 'active', 1), ('RECEIPT', 'current_frame', 7), ('RECEIPT', 'stamp', 9), ('RECEIPT', 'current_scene', 7), ('COVER', 'current_fpscr', 1), ('COVER', 'coverage', 0), ('COVER', 'required', 0), ('COVER', 'version', 1), ('COVER', 'bytes', 0), ('COVER', 'room', 0)]:
   a = fixture(); get(a, 'AV23OWNER_'+name, 1)[key] = value; self.bad(a)
 def test_source_path_and_commit(self):
  for key, value in [('flags', 0x4001), ('room', 0x101), ('path', 2), ('nv', 0), ('potential', 0), ('committed', 0)]:
   a = fixture(); get(a, 'AV23OWNER_SOURCE', 1)[key] = value; self.bad(a)
  a = fixture(1); get(a, 'AV23OWNER_SOURCE', 1)['committed'] = 1; self.bad(a)
 def test_bad_float_or_box(self):
  for name, value in [('AV23OWNER_VIEW', 0x7fc00000), ('AV23OWNER_BOX', word(3))]:
   a = fixture(); get(a, name)['words'][0] = value; self.bad(a)
 def test_missing_unexpected_slot_or_role_alias(self):
  a = fixture(); get(a, 'AV23OWNER_BOX')['slot'] = 3; self.bad(a)
  a = fixture(); [v.update(info=0x8c020000) for n, v in a if n == 'AV23OWNER_PART' and v['role'] == 1]; self.bad(a)
 def test_log_truncation_overrun_unknown_duplicate(self):
  data = render(fixture())
  for d in (data[:-12], data+b'LOG RING OVERRUN\n', data+b'AV23OWNER_FUTURE x=1\n', data+data):
   self.assertFalse(p.parse(d)['format_complete'])
 def test_owner_counts_cannot_exceed_global_ceiling(self):
  a = fixture(); get(a, "AV23")["hidden"] = 0; self.bad(a)
 def test_aggregate_never_attributes_owner(self):
  a = fixture(); a = [(n, v) for n, v in a if not n.startswith('AV23OWNER')]; self.bad(a)
 def test_assertions_are_not_evidence_or_acceptance(self):
  d = render(fixture()); assertion = dict(source='a'*40, source_parent=p.SOURCE_PARENT, format_source_sha256=p.FORMAT_SOURCE_SHA256, log_sha256=hashlib.sha256(d).hexdigest(), programme_sha256='a'*64, reader_complete=True, log_overflow=False)
  r = p.parse(d, assertion); self.assertTrue(r['format_complete']); self.assertFalse(r['qualified']); self.assertIn('PENDING', r['runtime_qualification'])
  for key, value in [('source_parent', '0'*40), ('log_sha256', '0'*64), ('reader_complete', False), ('log_overflow', True)]:
   changed = {**assertion, key: value}; self.assertFalse(p.parse(d, changed)['format_complete'])
 def test_no_accepted_synthetic_fixture(self):
  self.assertFalse(self.good(fixture())['qualified'])
 def test_all_material_refused_is_never_positive_cut(self):
  a = fixture()
  a = [(n,v) for n,v in a if n not in p.ROWS]
  for n,v in a:
   if n == 'AV23OWNER_PART':
    v.update(bound=0,potential=0,would=0,skip=0,positions=0,triangles=0,refused=2,refuse=2052)
  r = self.good(a); self.assertEqual(r['reported_owner2b_material_refusals'],4); self.assertEqual(r['reported_owner2b_potential_sections'],0); self.assertEqual(r['reported_owner2b_pre_position_skips'],0)
 def test_refusal_reason_count_and_provenance_strict(self):
  for key,value in [('refused',1),('refuse',4),('refuse',64),('refuse',8192)]:
   a=fixture();get(a,'AV23OWNER_PART')[key]=value;self.bad(a)
 def test_old_part_schema_is_not_silently_accepted(self):
  d=render(fixture()).replace(b' refused=0 refuse=0',b'');self.assertFalse(p.parse(d)['format_complete'])
 def test_exact_source_format_schema(self):
  source = Path(__file__).resolve().parents[3]/'platform/actor_visibility23.cc'
  if not source.exists(): self.skipTest('optional frozen-source readback unavailable')
  data = source.read_bytes(); self.assertEqual(hashlib.sha256(data).hexdigest(), p.FORMAT_SOURCE_SHA256)
  strings = p.re.findall(r're4dc_log\("(AV23[^"\\]*)', data.decode())
  seen = {}
  for s in strings:
   tokens = s.split(); seen[tokens[0]] = [v.split('=')[0] for v in tokens[1:]]
  self.assertEqual({n: [s.split(':')[0] for s in f.split()] for n, f in p.SCHEMA.items()}, seen)

if __name__ == '__main__':
 unittest.main(verbosity=2)
