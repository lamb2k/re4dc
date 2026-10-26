"""Extract reviewed production spans; no copied renderer implementation."""
from pathlib import Path
import re

HERE = Path(__file__).resolve().parent
DC = HERE.parents[2]
ROOT = DC.parents[1]
SOURCE = DC / "game/platform/native_static.cpp"


def function(text, signature):
    start = text.index(signature)
    brace = text.index("{", start)
    while ";" in text[start:brace]:
        start = text.index(signature, start + len(signature))
        brace = text.index("{", start)
    tokens = re.compile(r'"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'|//[^\n]*|/\*[\s\S]*?\*/|[{}]')
    depth = 0
    for match in tokens.finditer(text, brace):
        if match.group() == "{":
            depth += 1
        elif match.group() == "}":
            depth -= 1
            if not depth:
                return text[start:match.end()] + "\n"
    raise AssertionError(signature)


def pieces():
    source = SOURCE.read_text()
    helpers = source[source.index("void concat(const float*"):source.index("// Combined screen matrix", source.index("bool inverse(const float*"))]
    state = function(source, "namespace dyn {")
    binding = source[source.index('extern "C" void re4dc_ps2_dyn_bind('):]
    binding = binding[:binding.index("\n#endif\n#endif\n#if RE4DC_PS2_WORLD_ROOMS")] + "\n#endif\n"
    opening = function(source, "bool ps2_open(")
    admission = opening[opening.index("#if RE4DC_PS2_WORLD_DYNAMIC && RE4DC_PS2_WORLD_ROOMS\n") :]
    admission = admission[:admission.index("#if RE4DC_PS2_PASS_MASK\n")]
    prelude = opening[:opening.index("#if RE4DC_GC_ASSET_GATE\n")]
    prelude = prelude.replace("bool ps2_open(){", "bool fixture_open_existing(){", 1) + "return false;\n}\n"
    draw = source[source.index("        const float* affine=pl.affine;float moved_affine[12];"):]
    draw = draw[:draw.index("#if RE4DC_PS2_WORLD_LEAN\n        ++c.placements;")]
    movie = "\n".join(function(source, name) for name in (
        "bool ps2_movie_blocked(", "bool ps2_movie_current(", "bool ps2_movie_dyn_valid(",
        'extern "C" void re4dc_ps2_mesh_retire('))
    # Preserve the original same-room return and prior-room retirement order.
    assert opening.index("ps2_movie_blocked()") < opening.index("ps2_free()")
    assert opening.index("ps2w.storage)return true") < opening.index("dyn::reserve_slots(n)")
    assert admission.index("if(n && !sb)") < admission.index("dyn::slots=sb")
    assert admission.index("ps2_free();") < admission.index('re4dc_missing("root-pose witness preflight")')
    assert opening.index("dyn::reserve_slots(n)") < opening.index("ps2_movie.capture(")
    reload = function(source, "bool ps2_movie_reload(")
    assert not any(word in reload for word in ("dyn::reset", "re4dc_static_alloc", "re4dc_static_free", "dyn_parts"))
    return dict(helpers=helpers, state=state, binding=binding, admission=admission,
                prelude=prelude, draw=draw, movie=movie)


def host_source():
    p = pieces()
    fixture = (HERE / "host_fixture.cpp.in").read_text()
    for key, value in p.items():
        fixture = fixture.replace("@" + key.upper() + "@", value)
    assert not re.search(r"@[A-Z]+@", fixture)
    return fixture
