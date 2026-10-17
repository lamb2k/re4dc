"""build_blob.py with the runtime's 64-corner strip limit (lane cast16, 2026-10-17).

coarse_actor_preflight.h preflight_chunk refuses a strip longer than 64 corners (BlobError::Strip), but the
fastpath stripifier grows strips without a length cap. A large boss chunk (the PS2 U-3 em32 body, 3,261
triangles) gets a 71-corner strip and fails preflight. This wrapper runs the unchanged build_blob.py with its
stripify output split into strips of at most 64 corners: a long strip v0..vn becomes v0..v63, then v62..vn
(and so on), each cut at an even corner so every triangle keeps its winding by strip parity. A chunk whose
strips are all within 64 corners gets exactly the bytes build_blob.py writes on its own.

usage: strip64_build_blob.py <fastpath dir> <build_blob.py args...>
"""
import runpy, sys

STRIP_MAX = 64


def split_strips(idx):
    out, run = [], []
    for b in idx:
        run.append(b & 127)
        if b & 128:
            while len(run) > STRIP_MAX:
                out.extend(run[:STRIP_MAX - 1]); out.append(run[STRIP_MAX - 1] | 0x80)
                run = run[STRIP_MAX - 2:]          # restart at corner 62 (even): parity, so winding, is kept
            out.extend(run[:-1]); out.append(run[-1] | 0x80)
            run = []
    assert not run
    return out


def main():
    fast = sys.argv[1]
    sys.path.insert(0, fast)
    import build_blob as bb
    orig = bb.stripify
    bb.stripify = lambda tris, nverts, look=1: split_strips(orig(tris, nverts, look))
    sys.argv = [fast + '/build_blob.py'] + sys.argv[2:]
    bb.main()


if __name__ == '__main__':
    main()
