"""Build 36: native ESL rows -> source-loader archive -> scanned model candidates.

This is an archive inventory, not an actor or draw census.  In particular,
``readEmList`` can retain a later list on a return to an earlier room.  We keep
every supplied, recognised list as an alternative and never sum its rows into
live instances.  An archive can contain many appearances/attachments; all its
successfully scanned ModelData members are potential users, not selected BINs.

The table reader follows tools/assetpipe/discover.py, but reads all player
tables, applies checkAshleyId, and tests the actual DLL field for the DRS
rewrite.  It does not infer an archive from an ESL ID or model filename.
Source-less GLP1/compiled cast packages require an explicit owner binding.
"""
from collections import defaultdict
from pathlib import Path, PurePosixPath
import re

import formats as F


ORIGIN = "native ESL archive candidate"
SELECTION = ("conditional: this ESL must be the selected or retained current list; "
             "live story, player, costume, activation and appearance selection are unknown")
LIMITS = (
    "Only native little-endian ESL files named by stage.cpp emlist_name are automatic inputs.",
    "ESL records are at most 256 x 32 bytes; embedded or other-named ESL stays unresolved.",
    "Archive identity comes from current read.cpp and dvd.cpp tables, never the numeric ESL ID alone.",
    "Non-DLL .das names are unresolved: earlier loaders can mutate the shared FileTbl extension.",
    "All model members of a resolved archive are candidates; a source BIN/appearance was not selected.",
    "Lists and player/costume variants are alternatives, not simultaneous actors or instance counts.",
    "Scripts, runtime ESL patches, spawned-event actors and source-less replacement packages are not bound here.",
)


def _without_comments(text):
    # The parsed declarations/functions contain ordinary strings without // or
    # /*.  Do not accept a changed source grammar by partially matching it.
    return re.sub(r"/\*.*?\*/|//[^\n]*", "", text, flags=re.S)


def _body(text, pattern, what):
    matches = list(re.finditer(pattern, text))
    F.require(len(matches) == 1, "room loader " + what + " declaration")
    start = matches[0].end()
    F.require(start and text[start - 1] == "{", "room loader body anchor")
    depth = 1
    for at in range(start, len(text)):
        if text[at] == "{":
            depth += 1
        elif text[at] == "}":
            depth -= 1
            if not depth:
                return text[start:at]
    raise F.Invalid("room loader unterminated " + what)


def _compact(text):
    return re.sub(r"\s+", "", _without_comments(text))


def _macro(text, name):
    matches = list(re.finditer(r"(?m)^\s*#define\s+" + name + r"\(", text))
    F.require(len(matches) == 1, "room loader " + name + " macro")
    lines = text[matches[0].start():].lstrip().splitlines()
    definition = []
    for line in lines[:16]:
        line = line.rstrip()
        definition.append(line.removesuffix("\\"))
        if not line.endswith("\\"):
            return "\n".join(definition)
    raise F.Invalid("room loader macro line limit")


def _path(value):
    F.require(isinstance(value, str) and value and "\\" not in value and "\0" not in value,
              "room loader path")
    p = PurePosixPath(value)
    F.require(not p.is_absolute() and all(x not in (".", "..") for x in value.split("/"))
              and str(p) == value and len(value.encode("ascii")) < 64,
              "room loader path extent/components")
    return value.lower()  # platform/dvd.cpp normalise lowercases DVD names.


def _number(value):
    return int(value, 0)


def loader_tables(repo=None):
    """Read bounded initializers and current dispatch from public production source.

    Unknown syntax refuses the automatic mapping.  The Ashley and filename
    rewrites and DVD normalization have narrow checked contracts; table entries and player case
    groups are read afresh rather than copied into this tool.
    """
    repo = Path(repo) if repo is not None else Path(__file__).resolve().parents[5]
    names = ("src/game/read.cpp", "src/game/dvd.cpp", "src/game/stage.cpp",
             "port/dreamcast/game/platform/dvd.cpp")
    raw = {name: (repo / name).read_bytes() for name in names}
    read, dvd, stage, platform = (_without_comments(raw[name].decode("utf-8")) for name in names)
    files_text = _body(dvd, r"\bFileTblEntry\s+FileTbl\s*\[\s*\]\s*=\s*\{", "FileTbl")
    file_re = re.compile(r'\{\s*"([^"\\]*)"\s*,\s*0\s*\}\s*,?')
    file_matches = list(file_re.finditer(files_text))
    F.require(file_matches and not file_re.sub("", files_text).strip(), "room loader FileTbl syntax")
    files = [_path(m[1]) for m in file_matches]
    F.require(len(files) <= 8192, "room loader FileTbl count")

    table_names = ("EmFileTbl", "EmFileTbl_Ada", "EmFileTbl_Wesker", "EmFileTbl_Klauser")
    tables = {}
    row_re = re.compile(r"\{\s*(0[xX][0-9a-fA-F]+|[0-9]+)\s*,\s*"
                        r"(0[xX][0-9a-fA-F]+|[0-9]+)\s*,\s*"
                        r"(0[xX][0-9a-fA-F]+|[0-9]+)\s*\}\s*,?")
    for name in table_names:
        body = _body(read, r"\bReadFile\s+" + name + r"\s*\[\s*64\s*\]\s*=\s*\{", name)
        rows = [tuple(_number(m[i]) for i in (1, 2, 3)) for m in row_re.finditer(body)]
        F.require(len(rows) == 64 and not row_re.sub("", body).strip(), "room loader " + name + " rows")
        F.require(all(f < len(files) and d < len(files) and flag <= 0xffffffff for f, d, flag in rows),
                  "room loader file/DLL index")
        tables[name] = rows

    function = _body(read, r"\bint\s+readEmData\s*\([^;{}]*\)\s*\{", "readEmData")
    dispatch = _body(function, r"\bswitch\s*\(\s*pG->pl_type\s*\)\s*\{", "player dispatch")
    arm_re = re.compile(r"((?:\s*(?:case\s+[0-9]+\s*:|default\s*:))+?)\s*"
                        r"e\s*=\s*&\s*(EmFileTbl(?:_Ada|_Wesker|_Klauser)?)\s*\[\s*id\s*\]\s*;\s*break\s*;")
    arms = list(arm_re.finditer(dispatch))
    F.require(arms and not arm_re.sub("", dispatch).strip(), "room loader player dispatch syntax")
    player_variants = {}
    seen_players, defaults = set(), 0
    for arm in arms:
        player_types = [int(x) for x in re.findall(r"case\s+([0-9]+)\s*:", arm[1])]
        default = bool(re.search(r"\bdefault\s*:", arm[1]))
        F.require(not seen_players.intersection(player_types) and arm[2] not in player_variants,
                  "room loader duplicate player dispatch")
        seen_players.update(player_types)
        defaults += default
        player_variants[arm[2]] = dict(player_types=player_types, default_player_type=default)
    F.require(defaults == 1 and set(player_variants) == set(tables), "room loader player alternatives")

    ashley = _body(read, r"\bstatic\s+int\s+checkAshleyId\s*\(\s*int\s+id\s*\)\s*\{", "Ashley remap")
    F.require(_compact(ashley) == _compact("""
        if (id == 3 || id == 5) {
            if (pG->game_costume == 0) { id = 3; } else { id = 5; }
        }
        return id;
    """), "room loader unsupported Ashley remap")
    search = _body(read, r"\bvoid\s*\*\s*EmReadSearch\s*\([^;{}]*\)\s*\{", "EmReadSearch")
    search_compact = _compact(search)
    F.require(search_compact.startswith("ReadModule*m;id=checkAshleyId(id);m=SearchEmModule(id);")
              and search_compact.endswith("returnreadEm(id,addr,size);")
              and len(re.findall(r"\bid\s*(?:[+\-*/%&|^]?=(?!=)|\+\+|--)", search)) == 1
              and not re.search(r"(?:\+\+|--)\s*id\b|&\s*id\b", search),
              "room loader unsupported Ashley call/load ordering")
    F.require(re.search(r"if\s*\(\s*e->dll\s*!=\s*0\s*\)\s*\{\s*SET_DRS_NAME\(name\)\s*;", function),
              "room loader unsupported DRS admission")
    F.require(_compact(_macro(read, "SET_DRS_NAME")) == _compact("""
        #define SET_DRS_NAME(p)
            while (*(p) != '.') { (p)++; }
            (p)[1] = 'd'; (p)[2] = 'r'; (p)[3] = 's'
    """), "room loader unsupported DRS extension")
    normalise = _body(platform, r"\bstatic\s+void\s+normalise\s*\([^;{}]*\)\s*\{", "DVD normalise")
    F.require(_compact(normalise) == _compact(r"""
        size_t i = 0;
        while (*in == '/' || *in == '\\') in++;
        for (; *in && i + 1 < n; in++) {
            char c = *in;
            if (c == '\\') c = '/';
            out[i++] = (char) tolower((unsigned char) c);
        }
        out[i] = 0;
    """), "room loader unsupported DVD name normalization")

    list_text = _body(stage, r"\bstatic\s+const\s+char\s*\*\s*emlist_name\s*\[\s*11\s*\]\s*=\s*\{",
                      "ESL names")
    list_re = re.compile(r'"([^"\\]*)"\s*,?')
    lists = [_path(m[1]) for m in list_re.finditer(list_text)]
    F.require(len(lists) == 11 and len(set(lists)) == 11 and not list_re.sub("", list_text).strip()
              and all(re.fullmatch(r"etc/(?:emleon|omake)[0-9]{2}\.esl", x) for x in lists),
              "room loader ESL names syntax/count")
    return dict(files=files, tables=tables, players=player_variants, lists=lists,
                source_inputs=[dict(path=name, sha256=F.sha(raw[name]), bytes=len(raw[name]),
                                    format="room-membership-source") for name in names])


def archive_alternatives(tables, enemy_id):
    """Loader paths/unknown name states, preserving player/costume alternatives.

    SET_DRS_NAME modifies FileTbl storage in place.  A non-DLL row therefore
    does not establish that its initial .das name survives earlier loads.
    ReadPlayerData, for example, unconditionally rewrites file 6 (normal Leon),
    also used by EmFileTbl[1].  Do not guess either current extension.
    """
    F.require(type(enemy_id) is int and 0 <= enemy_id <= 255, "room membership enemy ID")
    if enemy_id >= 64:
        return []  # Core props / unsupported IDs are not guessed as emXX files.
    identities = ((3, "game_costume == 0"), (5, "game_costume != 0")) if enemy_id in (3, 5) else (
        (enemy_id, "any costume"),)
    result = []
    for actual_id, costume in identities:
        for table in sorted(tables["tables"]):
            file_index, dll_index, flag = tables["tables"][table][actual_id]
            if not file_index:
                continue
            original = tables["files"][file_index]
            path = original
            if dll_index:
                # SET_DRS_NAME stops at the FIRST dot; current runtime table
                # names have one.  Reject a changed contract rather than guess.
                F.require(path.count(".") == 1 and len(path.rsplit(".", 1)[1]) == 3,
                          "room loader DRS source extension")
                path = path.split(".", 1)[0] + ".drs"
            mutable = not dll_index and original.endswith(".das")
            result.append(dict(path=path, requested_path=original, table=table,
                mapped_id=actual_id, file_index=file_index, dll_index=dll_index, file_flag=flag,
                binding_supported=not mutable,
                filename_state="mutable-unresolved" if mutable else "rewritten-to-drs" if dll_index else "initial-name",
                costume_condition=costume, **tables["players"][table]))
    return result


def build_memberships(tree, models, sources, spawns, rooms, repo=None):
    """Return auto memberships and a separate, JSON-safe provenance inventory.

    Inputs are the successful scan_tree model/source/ESL records.  No mutation
    of them occurs.  ``memberships`` uses internal ``(source, model_key)`` tuple
    keys; the other fields are JSON safe.  Merge these candidates BEFORE the
    existing package/context/explicit room-list entries, so owner information
    remains strongest.  Keep ``inventory`` even when an explicit override wins.
    """
    tree = Path(tree).resolve()
    F.require(tree.is_dir(), "room membership disc tree")
    selected = set(rooms)
    F.require(all(re.fullmatch(r"r[0-9a-f]{3,4}", x) for x in selected), "room membership room names")
    result = dict(memberships={}, inventory=[], coverage=[], source_inputs=[], limits=list(LIMITS))
    try:
        tables = loader_tables(repo)
    except (ValueError, UnicodeError, OSError) as exc:
        result["coverage"].append(dict(source="source-loader-tables", format="room-membership",
            status="rejected", models=0, message=str(exc)))
        return result
    result["source_inputs"] = tables["source_inputs"]
    by_path = defaultdict(list)
    for source in sources:
        if not source.startswith("@input/"):
            try:
                by_path[_path(source)].append(source)
            except (ValueError, UnicodeError):
                continue
    by_source = defaultdict(list)
    for model in models:
        by_source[model["source"]].append(model)
    bound = defaultdict(lambda: defaultdict(list))
    coverage_seen = set()

    def gap(source, status, message):
        key = (source, status, message)
        if key not in coverage_seen:
            result["coverage"].append(dict(source=source, format="room-membership", status=status,
                                            models=0, message=message))
            coverage_seen.add(key)

    native_lists_seen = set()
    for spawn in sorted(spawns, key=lambda s: (s["source"], s["location"], s["index"])):
        room = f"r{spawn['room']:03x}"
        if room not in selected:
            continue
        source = spawn["source"]
        source_fact = sources.get(source, {})
        item = dict(room=room, list_source=source, list_sha256=spawn.get("source_sha256"),
                    location=spawn["location"], list_index=spawn["index"],
                    record_offset=spawn["index"] * 32, enemy_id=spawn["enemy_id"],
                    type=spawn.get("type"), set=spawn.get("set"), be_flag=spawn.get("be_flag"),
                    selection=SELECTION, instances=None)
        try:
            native_path = _path(source)
        except (ValueError, UnicodeError):
            native_path = None
        if native_path not in tables["lists"] or spawn["location"] != source:
            result["inventory"].append(dict(item, status="unresolved", message="not a native named stage ESL input"))
            gap(source, "unresolved", "ESL candidates have no supported stage-list identity")
            continue
        native_lists_seen.add(source)
        item["list_number"] = tables["lists"].index(native_path)
        if len(by_path[native_path]) != 1:
            result["inventory"].append(dict(item, status="ambiguous", message="multiple input paths normalize to this ESL"))
            gap(source, "rejected", "ambiguous case-normalized native ESL identity")
            continue
        if source_fact.get("format") != "ESL" or source_fact.get("sha256") != spawn.get("source_sha256"):
            result["inventory"].append(dict(item, status="rejected", message="ESL source/hash binding mismatch"))
            gap(source, "rejected", "ESL source/hash binding mismatch")
            continue
        try:
            size = source_fact.get("bytes", 0)
            F.require(type(size) is int and 0 < size <= 8192 and size % 32 == 0,
                      "ESL extent outside native list contract")
            F.require(type(spawn["index"]) is int and 0 <= spawn["index"] < size // 32,
                      "ESL record outside source extent")
            F.require((tree / source).resolve().is_relative_to(tree), "ESL symlink escapes disc tree")
            alternatives = archive_alternatives(tables, spawn["enemy_id"])
        except (ValueError, UnicodeError) as exc:
            result["inventory"].append(dict(item, status="rejected", message=str(exc)))
            gap(source, "rejected", str(exc))
            continue
        if not alternatives:
            result["inventory"].append(dict(item, status="unresolved", message="no supported external archive loader row"))
            gap(source, "unresolved", "one or more ESL IDs use core objects or have no supported archive row")
            continue
        targets = defaultdict(list)
        for alternative in alternatives:
            targets[alternative["path"]].append(alternative)
        for target in sorted(targets):
            record = dict(item, target_path=target, loader_alternatives=targets[target], model_keys=[])
            if any(not a["binding_supported"] for a in targets[target]):
                record.update(status="unresolved", message="initial non-DLL .das FileTbl name may have been rewritten by an earlier loader; current path unknown")
                gap(target, "unresolved", record["message"])
                result["inventory"].append(record)
                continue
            matches = by_path.get(target, [])
            if len(matches) > 1:
                record.update(status="ambiguous", message="multiple input paths normalize to loader target", sources=matches)
                gap(target, "rejected", "ambiguous case-normalized archive identity")
            elif not matches:
                record.update(status="missing", message="exact loader target was not scanned")
                gap(target, "missing", "native ESL references this exact archive target; missing or unsupported input")
            else:
                actual = matches[0]
                fact = sources[actual]
                candidates = by_source.get(actual, [])
                record.update(source=actual, source_sha256=fact.get("sha256"))
                valid = (fact.get("format") == "archive" and candidates
                         and all(m.get("kind") == "ModelData" and m.get("file_sha256") == fact.get("sha256")
                                 for m in candidates)
                         and len({m["key"] for m in candidates}) == len(candidates))
                if not valid:
                    record.update(status="unresolved", message="target lacks an unambiguous hash-bound scanned ModelData inventory")
                    gap(actual, "unresolved", record["message"])
                elif not (tree / actual).resolve().is_relative_to(tree):
                    record.update(status="rejected", message="archive symlink escapes disc tree")
                    gap(actual, "rejected", record["message"])
                else:
                    record.update(status="candidate", message="archive-load potential; BIN/appearance and activation unselected",
                                  model_keys=sorted(m["key"] for m in candidates))
                    ordinal = len(result["inventory"])
                    for model in candidates:
                        bound[(actual, model["key"])][room].append(ordinal)
            result["inventory"].append(record)

    # Empty valid lists still count as supplied.  Missing other story/mode lists
    # are not guessed as mandatory; no supplied list yields one explicit gap.
    native_lists_seen.update(source for source, fact in sources.items()
        if source.lower() in tables["lists"] and fact.get("format") == "ESL")
    if not native_lists_seen:
        gap("native-room-lists", "missing", "no named native stage ESL supplied; automatic global archive membership unavailable")
    for key, room_records in sorted(bound.items()):
        result["memberships"][key] = [dict(room=room, instances=None, origin=ORIGIN,
            status="candidate", selection=SELECTION, evidence=ordinals)
            for room, ordinals in sorted(room_records.items())]
    result["coverage"].sort(key=lambda x: (x["source"], x["status"], x["message"]))
    return result
