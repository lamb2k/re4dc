"""Public synthetic R4IM/R4PW and PS2 wrapper fixtures; no game asset data."""
from pathlib import Path
import struct
import sys
import zlib

TOOLS = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(TOOLS))
import convert_room_bins as fmt


def package(kind="compact", version=3):
    """Three material passes, multiple levels, seams, degenerates and sharing."""
    n = {"compact": 8, "limit": 256, "reuse": 64, "unused": 16}[kind]
    base = [(100+(i % 8)*17, 200+(i//8)*13, 300+(i % 3)*7,
             (i*8191)&65535, (i*3331)&65535, 0x8000 | ((i*1111)&0x7fff)) for i in range(n)]
    # Same XYZ with different UV/colour must remain distinct. Degenerate strip
    # occurrences also remain in the stream; the converter may not simplify.
    base[3] = base[0][:3]+(123, 456, 0x9234)
    strips = ([list(range(255)), [253, 254, 255]] if kind == "limit" else
              [list(i % n for i in range(255)), [0, 1, 1, 2, 3, 4, 5]] if kind == "reuse" else
              [[0, 1, 3, 2, 2, 4], [4, 5, 6, 7]])
    vertices, stream, lets, parts, plods, clusters, levels = [], bytearray(), [], [], [], [], []
    for part in range(3):
        start, pool = len(lets), len(vertices)
        corners = [(x+part*1000, y, z, u, v, c) for x, y, z, u, v, c in base]
        bounds = (*[min(v[a] for v in corners) for a in range(3)],
                  *[max(v[a] for v in corners) for a in range(3)])
        for level in range(2):
            indexed = level == 1 and version == 3
            if indexed:
                if len(stream) & 1:
                    stream.append(0)
                fs = len(stream)
                # Scattered pool order is deliberately distinct from local order.
                order = list(reversed(range(n)))
                stream.extend(struct.pack("<%dH" % n, *order))
                first = pool
                mapping = {old: new for new, old in enumerate(order)}
            else:
                fs = len(stream); first = len(vertices); vertices.extend(corners)
                mapping = {k: k for k in range(n)}
            s0 = len(stream)
            for strip in strips:
                stream.append(len(strip)); stream.extend(mapping[k] for k in strip)
            lets.append((first, fs, len(stream)-s0, n, len(strips)|(0x8000 if indexed else 0), *bounds))
            levels.append((len(lets)-1, 1, float(level)*0.75))
        parts.append((part*32, part*100, part, 255-part, part, 0, start, 2,
                      -0.5+part, 0.25, 1.0/65535.0, 2.0/65535.0))
        plods.append((part, 1)); clusters.append((*bounds, part*2, 2))
    mesh = (19, 0, 0x50, n, 3, 0x1234, 0, 3,
            -10.0, 20.0, -30.0, 0.125, 0.25, 0.5, 0.0, 0.0, 0.0, 5000.0, 5000.0, 5000.0)
    sections = [("mesh", fmt.MESH.pack(*mesh)),
                ("part", b"".join(fmt.PART.pack(*p) for p in parts)),
                ("meshlet", b"".join(fmt.MESHLET.pack(*l) for l in lets)),
                ("vertex", b"".join(fmt.VERTEX.pack(*v) for v in vertices)),
                ("index", bytes(stream)), ("palette", struct.pack("<I", 0xffffffff)),
                ("part_lod", b"".join(fmt.PART_LOD.pack(*p) for p in plods)),
                ("cluster", b"".join(fmt.CLUSTER.pack(*c) for c in clusters)),
                ("level", b"".join(fmt.LEVEL.pack(*l) for l in levels)),
                ("class", b"\x05"), ("rule", bytes(range(32)))]
    body = bytearray(32); offsets = {}
    for name, raw in sections:
        body.extend(bytes((-(80+len(body))) % 32))
        offsets[name] = 80+len(body); body.extend(raw)
    body.extend(bytes((-(80+len(body))) % 32))
    body[:32] = fmt.LOD_HEADER.pack(3, 6, offsets["part_lod"], offsets["cluster"], offsets["level"],
                                    offsets["class"], offsets["rule"], 0)
    head = fmt.HEADER.pack(b"R4IM", version, 80+len(body), zlib.crc32(body), 1, 3, len(lets), len(vertices),
        len(stream), 1, *[offsets[n] for n in ("mesh", "part", "meshlet", "vertex", "index", "palette")], 2, 0, 0, 0)
    # Original source placement IDs/order and mirrored/nonuniform affine data.
    side = bytearray()
    for p in range(3):
        side.extend(struct.pack("<IIHHBBBB", 0x11223344+p, 0x55667788+p, 64, 128, p, 2-p, p, 0))
    for ident, affine in ((41, (1, 0, 0, 10, 0, 1, 0, 20, 0, 0, 1, 30)),
                          (7, (-1, 0, 0, -10, 0, 2, 0, 0, 0, 0, 0.5, 50))):
        side.extend(struct.pack("<HH12f", 0, ident, *affine))
    policy = struct.pack("<4s7I", b"R4PW", 1, 2, 3, 1, zlib.crc32(side), 0, 0)+side
    return bytes(head+body), bytes(policy)


def wrapper(root):
    """Small real .r4p + the public parser's full table shape for CLI identity."""
    root.mkdir(parents=True, exist_ok=True)
    payload, spans = bytearray(), {}

    def append(name, data, count):
        payload.extend(bytes((-len(payload)) % 4))
        spans[name] = (len(payload), count); payload.extend(data)
        return spans[name]

    pos = append("position", b"".join(struct.pack("<3h", *v) for v in
        ((0, 0, 0), (200, 0, 0), (0, 200, 0), (200, 200, 0))), 4)
    uv = append("uv", b"".join(struct.pack("<2h", *v) for v in ((0, 0), (256, 0), (0, 256), (256, 256))), 4)
    attr = append("attr", bytes((128, 100, 64, 128, 64, 128, 100, 128, 100, 64, 128, 128, 128, 128, 128, 128)), 4)
    corners = []
    for order in ((0, 1, 2, 3), (1, 0, 3, 2)):
        corners.extend((v|(0x8000 if i == 3 else 0), v, i) for i, v in enumerate(order))
    corner = append("corner", b"".join(struct.pack("<3H", *v) for v in corners), 8)
    template = struct.pack("<HBB8IfII", 19, 0, 0, *pos, *uv, *attr, *corner, 1.0, 0, 0)
    append("templates", template, 1)
    append("materials", bytes(32), 2)
    append("authored_batches", b"", 0)
    ranges = b"".join(struct.pack("<4H4I", 0, 0, i, 0, i, 1, i*4, 4) for i in range(2))
    append("ordered_ranges", ranges, 2)
    placements = bytearray()
    for ident in (41, 7):
        placement = bytearray(80)
        struct.pack_into("<HH", placement, 0, ident, 0)
        struct.pack_into("<II", placement, 16, 0, 2)
        struct.pack_into("<12f", placement, 32, 1, 0, 0, ident, 0, 1, 0, 0, 0, 0, 1, 0)
        placements.extend(placement)
    append("placements", placements, 2)
    append("smd_rows", b"", 0); append("smx_rows", b"", 0)
    bounds = bytearray(40)
    for i in range(2):
        struct.pack_into("<IH", bounds, 20*i, i*4, 4)
    append("ordered_bounds", bounds, 2)
    header = bytearray(224)
    for i, name in enumerate(("templates", "materials", "authored_batches", "ordered_ranges", "placements", "smd_rows", "smx_rows", "ordered_bounds")):
        struct.pack_into("<II", header, 144+8*i, *spans[name])
    struct.pack_into("<I", header, 208, len(payload))
    mesh_path, inc_path = root/"public.r4p", root/"public.inc"
    mesh_path.write_bytes(header+payload)
    inc_path.write_text("ps2_textures[98]={{0x12345678u,0x87654321u,64,64,0,0x1p+0f,0x1p+0f,0x1p+0f},"+
        ",".join("{}" for _ in range(97))+"};\nps2_policy[342]={"+
        ",".join("{0,%d,%d}" % (2 if i == 1 else 0, 2 if i == 1 else 0) for i in range(342))+"};\n"+
        "ps2_reference_lighting[22]={"+",".join("{"+",".join("0" for _ in range(39))+"}" for _ in range(22))+"};\n"+
        "ps2_ambient[3]={0,0,0};\nps2_payload_crc=0x%08xu;\n" % zlib.crc32(payload))
    return mesh_path, inc_path


def capacity(count, split_first=False):
    """Exact Pick.let boundary: ordinary dense plain meshlets, no private data.

    With split_first, the first source meshlet has255+3 strip corners using
    three local records, so SDS1 adds one child without a large vertex pool.
    Caller may set header provenance/marker to exercise the actual C++ reader.
    """
    assert 1 <= count <= 65537
    triangle = struct.pack("<18H", 100, 100, 0, 0, 0, 0xffff,
        102, 100, 0, 1, 0, 0xffff, 100, 102, 0, 0, 1, 0xffff)
    first_stream = bytes([255, *[i % 3 for i in range(255)], 3, 0, 1, 2]) if split_first else bytes([3, 0, 1, 2])
    strips = first_stream+bytes([3, 0, 1, 2])*(count-1)
    lets = bytearray()
    for i in range(count):
        start = 0 if i == 0 else len(first_stream)+4*(i-1)
        lets.extend(fmt.MESHLET.pack(3*i, start, len(first_stream) if i == 0 else 4,
                    3, 2 if i == 0 and split_first else 1, 100, 100, 0, 102, 102, 0))
    sections = (("mesh", fmt.MESH.pack(1, 0, 0x50, 3, 1, 0, 0, 1,
                   0, 0, 0, 1, 1, 1, 100, 100, 0, 102, 102, 0)),
        ("part", fmt.PART.pack(0, 0, 0, 255, 0, 0, 0, count, 0, 0, 1, 1)),
        ("meshlet", bytes(lets)), ("vertex", triangle*count), ("index", strips),
        ("palette", struct.pack("<I", 0xffffffff)), ("part_lod", fmt.PART_LOD.pack(0, 1)),
        ("cluster", fmt.CLUSTER.pack(100, 100, 0, 102, 102, 0, 0, 1)),
        ("level", fmt.LEVEL.pack(0, count, 0)))
    body, offsets = bytearray(32), {}
    for name, raw in sections:
        body.extend(bytes((-(80+len(body))) % 32))
        offsets[name] = 80+len(body); body.extend(raw)
    body.extend(bytes((-(80+len(body))) % 32))
    body[:32] = fmt.LOD_HEADER.pack(1, 1, offsets["part_lod"], offsets["cluster"], offsets["level"], 0, 0, 0)
    head = fmt.HEADER.pack(b"R4IM", 3, 80+len(body), zlib.crc32(body), 1, 1, count, 3*count, len(strips), 1,
        *[offsets[n] for n in ("mesh", "part", "meshlet", "vertex", "index", "palette")], 2, 0, 0, 0)
    side = struct.pack("<IIHHBBBB", 0x1234, 0x5678, 64, 64, 0, 0, 0, 0)
    side += struct.pack("<HH12f", 0, 1, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0)
    policy = struct.pack("<4s7I", b"R4PW", 1, 1, 1, 1, zlib.crc32(side), 0, 0)+side
    return bytes(head+body), policy
