"""Build 36 texture selection for an explicitly composed disc, never game I/O.

The existing formats readers remain the admission boundary. A physical pack
must have the unique, sorted index accepted by texpack_index.inc; layers do
not make duplicate keys inside that index legal. t11-fix.py replaces the
whole dc/tex.pak file in --data order. Only positive, explicitly supplied
layer numbers express that order here. A directory walk does not.

native_ui.cpp chooses a packed member before the canonical loose path when
TEX_PACK is enabled, except for current-room Standard texlow selection. The
recipe and that current-room selection remain conditional when unknown.
These are static file-availability/palette predicates, not runtime residency,
upload admission, transient I/O, draw frequency, or texture-cache predictions.
"""
import re

import formats


KEY = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{8}$")
LOOSE = re.compile(r"^dc/(tex|texlow)/(?:([0-9a-f])/)?([0-9a-f]{8}-[0-9a-f]{8})\.re4tex$")


def _public(record):
    return {k: v for k, v in record.items() if not k.startswith("_")}


def _same(values):
    """Return the shared tri-state value; differing possibilities are unknown."""
    first = values[0]
    return first if all(v is first for v in values) else None


class Resolver:
    """Collect parsed inputs, then resolve declared final-disc lookup choices.

    add_pack/add_loose/failed_pack return ordinary scanner coverage rows.
    Content failures are recorded, not raised. An invalid explicit final
    layer takes authority away from earlier layers; its bytes are unknown.
    API misuse (duplicate identity/layer, invalid key) raises formats.Invalid.
    finish() is cached until another input is added. predicate(key) also works
    for references not found in any input, without adding inventory counts.
    """

    def __init__(self, knobs=None):
        self.knobs = dict(knobs or {})
        self._sources = []
        self._coverage = []
        self._variants = {}
        self._packs = {}
        self._loose = {}
        self._identities = set()
        self._cache = None
        self._warnings = []
        self._modes = self._recipe_modes()

    def _flag(self, name):
        value = self.knobs.get(name)
        try:
            parsed = int(value, 0) if isinstance(value, str) else value
        except ValueError:
            parsed = None
        if type(parsed) is int and parsed in (0, 1):
            return (parsed,)
        self._warnings.append(name + " is unknown; file selection remains conditional")
        return (0, 1)

    def _recipe_modes(self):
        packs = self._flag("TEX_PACK")
        residents = self._flag("TEX_RESIDENT")
        qualities = self._flag("QUALITY_ASSETS")
        modes = []
        for resident in residents:
            for pack in packs:
                # game30.mk: TEX_PACK=1 requires TEX_RESIDENT=1.
                if pack and not resident:
                    continue
                # Quality selection is room state, not evidence from a loose
                # filename. Original and Standard may both occur with it on.
                low_modes = (False, True) if resident and 1 in qualities else (False,)
                for low in low_modes:
                    mode = (bool(resident), bool(pack), low)
                    if mode not in modes:
                        modes.append(mode)
        if not modes:
            self._warnings.append("TEX_PACK=1 with TEX_RESIDENT=0 is not an admitted recipe; selection is unknown")
        return modes

    def _begin(self, source, kind, data, layer, role):
        formats.require(isinstance(source, str) and source, "texture source identity")
        identity = (source, layer)
        formats.require(identity not in self._identities, "duplicate texture input identity " + source)
        self._identities.add(identity)
        self._cache = None
        record = dict(source=source, format=kind, layer=layer, role=role,
                      sha256=formats.sha(data) if data is not None else None,
                      bytes=len(data) if data is not None else None, status="pending", message="")
        self._sources.append(record)
        return record

    def _cover(self, record, status, message):
        record.update(status=status, message=message)
        row = dict(source=record["source"], format=record["format"], status=status, models=0, message=message)
        self._coverage.append(row)
        return dict(row)

    def _pack_slot(self, source, layer):
        if layer is not None:
            formats.require(type(layer) is int and layer > 0, "explicit tex.pak layer must be a positive integer")
            slot = layer
        else:
            slot = 0 if source == "dc/tex.pak" else None
        formats.require(slot is None or slot not in self._packs, "duplicate tex.pak layer " + str(slot))
        return slot

    def _variant(self, source, key, value, kind, offset=None):
        variant = dict(source=source["source"], source_sha256=source["sha256"],
                       sha256=value["sha256"], bytes=value["bytes"], kind=kind,
                       layer=source["layer"], offset=offset, role=source["role"],
                       _value=value, _source=source)
        self._variants.setdefault(key, []).append(variant)
        return variant

    def add_pack(self, source, data, layer=None):
        slot = self._pack_slot(source, layer)
        record = self._begin(source, "tex.pak", data, layer,
                             "pack-layer" if layer is not None else "canonical-pack" if slot == 0 else "unselected-pack")
        record["_entries"] = None
        if slot is not None:
            # Register before parsing. A failed final file does not uncover an
            # older file that staging has already replaced.
            self._packs[slot] = record
        try:
            parsed = formats.parse_texpak(data)
        except (ValueError, UnicodeError) as exc:
            return self._cover(record, "rejected", str(exc))
        entries = {}
        for index, (key, value) in enumerate(parsed.items()):
            _crc, _fnv, offset, size = formats.unpack("<4I", data, 2048 + index * 16)
            formats.require(size == value["bytes"], "parsed texture member size")
            entries[key] = self._variant(record, key, value, "pack", offset)
        record["_entries"] = entries
        record["keys"] = len(entries)
        if slot is None:
            return self._cover(record, "unsupported", "pack has no declared dc/tex.pak destination/order; not selected")
        return self._cover(record, "scanned", "validated whole-file pack candidate; final declared layer selects it")

    def failed_pack(self, source, message, layer=None):
        """Record unreadable/missing input without using a previous pack."""
        slot = self._pack_slot(source, layer)
        record = self._begin(source, "tex.pak", None, layer,
                             "pack-layer" if layer is not None else "canonical-pack" if slot == 0 else "unselected-pack")
        record["_entries"] = None
        if slot is not None:
            self._packs[slot] = record
        return self._cover(record, "rejected", str(message))

    def add_loose(self, source, data):
        match = LOOSE.fullmatch(source)
        key_match = re.fullmatch(r"([0-9a-f]{8}-[0-9a-f]{8})\.re4tex", source.rsplit("/", 1)[-1].lower())
        key = key_match[1] if key_match else None
        canonical = bool(match and (match[2] is None and match[1] == "tex" or match[2] == match[3][0]))
        role = "loose-" + ("low" if match and match[1] == "texlow" else "bucket" if match and match[2] else "flat") if canonical else "unselected-loose"
        record = self._begin(source, "texture", data, None, role)
        record["_entry"] = None
        if canonical:
            self._loose[source] = record
        try:
            formats.require(key is not None, "loose texture key filename")
            value = formats.parse_texture(data)
        except (ValueError, UnicodeError) as exc:
            # Keep a malformed canonical key in inventory so a later lookup
            # reports unknown rather than silently calling it absent.
            if canonical and key:
                self._variants.setdefault(key, [])
            return self._cover(record, "rejected", str(exc))
        record["_entry"] = self._variant(record, key, value, "loose")
        if not canonical:
            return self._cover(record, "unsupported", "loose package is outside the canonical runtime paths; not selected")
        return self._cover(record, "scanned", "validated loose candidate; pack/recipe/room selection determines use")

    def _selected_pack(self):
        return self._packs[max(self._packs)] if self._packs else None

    def _lookup(self, key, mode):
        resident, use_pack, low = mode
        pack = self._selected_pack()
        if use_pack and not low and pack is not None:
            entries = pack["_entries"]
            if entries is None:
                # The existing combined reader can refuse either the index or
                # a member payload. Only the former makes runtime use loose;
                # without that distinction neither loose nor an old layer is
                # authoritative. Preserve the uncertainty and coverage error.
                return None, None
            if key in entries:
                return True, entries[key]
        if resident:
            path = "dc/" + ("texlow" if low else "tex") + "/" + key[0] + "/" + key + ".re4tex"
        else:
            path = "dc/tex/" + key + ".re4tex"
        record = self._loose.get(path)
        if record is None:
            return False, None
        if record["_entry"] is None:
            return None, None
        return True, record["_entry"]

    def _resolve_key(self, key):
        outcomes = [self._lookup(key, mode) for mode in self._modes] or [(None, None)]
        present = _same([item[0] for item in outcomes])
        possible = []
        for _state, variant in outcomes:
            if variant is not None and all(variant is not p for p in possible):
                possible.append(variant)
        palette = _same([any(e["palette"] for e in v["_value"]["entries"]) for v in possible]) if present is True else None
        payloads = {v["sha256"] for v in possible}
        selected_payload = next(iter(payloads)) if present is True and len(payloads) == 1 else None
        selected_source = possible[0]["source"] if present is True and len(possible) == 1 else None
        candidates = self._variants.get(key, [])
        shadowed = [v for v in candidates if all(v is not p for p in possible)]
        return dict(key=key, present=present, palette=palette, selected_source=selected_source,
                    selected_sha256=selected_payload,
                    possible_sources=[_public(v) for v in possible], shadowed=[_public(v) for v in shadowed],
                    candidates=[_public(v) for v in candidates],
                    possible_absent=any(state is False for state, _v in outcomes),
                    unresolved=any(state is None for state, _v in outcomes),
                    selection="selected" if selected_payload is not None else "absent" if present is False else "conditional")

    def predicate(self, key):
        formats.require(isinstance(key, str) and KEY.fullmatch(key), "texture reference key")
        if self._cache is not None and key in self._cache["keys"]:
            return self._cache["keys"][key]
        return self._resolve_key(key)

    def finish(self):
        if self._cache is not None:
            return self._cache
        keys = {key: self._resolve_key(key) for key in sorted(self._variants)}
        textures = {}
        for key, row in keys.items():
            if row["selected_sha256"] is not None:
                textures[key] = next(v["_value"] for v in self._variants[key] if v["sha256"] == row["selected_sha256"])
        selected_pack = self._selected_pack()
        sources = []
        for record in self._sources:
            row = _public(record)
            if record["format"] == "tex.pak":
                row["selected_file"] = record is selected_pack
                row["shadowed_file"] = any(record is other for other in self._packs.values()) and record is not selected_pack
            sources.append(row)
        summary = dict(definite_keys=sum(row["present"] is True for row in keys.values()),
                       conditional_keys=sum(row["present"] is None for row in keys.values()),
                       absent_keys=sum(row["present"] is False for row in keys.values()),
                       physical_variants=sum(len(row["candidates"]) for row in keys.values()),
                       possible_variants=sum(len(row["possible_sources"]) for row in keys.values()),
                       shadowed_variants=sum(len(row["shadowed"]) for row in keys.values()))
        self._cache = dict(textures=textures, keys=keys, sources=sources,
                           coverage=[dict(row) for row in self._coverage], warnings=list(self._warnings), summary=summary)
        return self._cache
