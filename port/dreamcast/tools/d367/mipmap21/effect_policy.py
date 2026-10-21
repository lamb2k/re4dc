"""Shared static source policy for full-frame EFF texture candidates.

EFF tags describe a file format also used by ID UI. All direct bindings,
unavailable exact inputs and custom/mixed consumers remain explicit.
"""
from __future__ import annotations
import collections
import effect_consumers

ID_UI={('etc/core.das',29):'Cockpit::roomInit HUD / ArcFile::ofs_74',
       ('st1/r101.arc',39):'r101 binocular -> CameraControl::HoldBinocular -> IdBinocular::init',
       ('st1/r10b.arc',38):'r10b binocular -> IdBinocular::init'}
for weapon in ('09','10','13','14'):
    ID_UI[('em/wep'+weapon+'.drs',4)]='IdScope::init WEP_ARC_PTR(4)'


def classify(frame,parsed,source_meta,common_ids,*,sampling_contract_version=2):
    refs=[];records=[];reasons=set();ui=set()
    for ref in frame['source_refs']:
        rel,slot=ref['path'],ref['arc_index']
        if (rel,slot) in ID_UI:ui.add(ID_UI[(rel,slot)])
        if rel not in parsed:
            reasons.add('exact-source-input-unavailable-or-unsupported');continue
        if source_meta[rel]['sha256']!=ref['file_sha256']:
            reasons.add('source-reference-hash-differs');continue
        matches=[t for block in parsed[rel]['effects'] if block['archive_entry']==slot
                 for t in block['textures'] if t['tpl_offset']==ref['tpl_offset']]
        if len(matches)!=1:
            reasons.add('reference-not-a-direct-EFF-frame-TPL');continue
        t=matches[0]
        refs.append(dict(source_path=rel,source_sha256=source_meta[rel]['sha256'],archive_entry=slot,
            tpl_offset=ref['tpl_offset'],texture_id=t['texture_id'],records=t['records']))
        records.extend(t['records'])
        if not t['records']:reasons.add('no-EST-SST-consumer-in-this-resource')
    if not frame['source_refs']:reasons.add('no-source-reference')
    contracts=[effect_consumers.record_sampling(r,common_ids,contract_version=sampling_contract_version) for r in records]
    if ui:
        decision='hold-fixed-ID-UI';reasons.add('source-proven-ID-sprite-resource')
    elif reasons:
        decision='hold-unresolved-consumer'
    elif 'hold-screen' in contracts:
        decision='hold-screen-or-mixed-effect';reasons.add('source-record-can-select-screen-parts')
    elif any(c.startswith('hold-') for c in contracts) or not any(c.startswith('common-world-sprite') for c in contracts):
        decision='hold-custom-or-generator-effect';reasons.add('custom-generator-RTT-or-shimmer-contract-needs-review')
    else:decision='world-common-sprite-source-candidate'
    return dict(key=frame['key'],package_sha256=frame['package_sha256'],decision=decision,
        reasons=sorted(reasons),direct_ID_UI_consumers=sorted(ui),source_bindings=refs,
        record_contracts=dict(collections.Counter(contracts)),
        scope='Static source record binding only; not exclusive runtime selection, actual spawn/draw or rendered acceptance.')
