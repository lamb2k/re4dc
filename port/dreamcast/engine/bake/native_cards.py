"""Far props as flat cards (eng-look, content step P), baked from the PS2-path model the bench draws.

For each prop model (catalogue role-2 models), the model is skinned with the first recorded pose in which it
appears and expressed in its root's frame; then drawn from 8 directions around the root's vertical axis (yaw
k x 45 degrees, orthographic, z-buffered, texture colour only: the runtime lights the card with one colour) into a
256 x 128 atlas of 64 x 64 views (4 x 2), alpha 255 where covered. The runtime draws a cylindrical billboard of the
nearest view, punch-through, with the actor's light at its centre.
Card row: model, header, then the centre in the root frame (3 floats), half width, half height."""
import struct
import numpy as np
from geometry import actor_strips  # noqa: F401  (format reference)

VIEW = 64


def _model_arrays(raw):
    bones, nw, npos, nnrm, nparts, nstrip = struct.unpack_from("<6I", raw)
    at = 24
    binds = np.frombuffer(raw, "<f4", 12 * bones, at).reshape(bones, 3, 4); at += 48 * bones
    w = [struct.unpack_from("<4B3f", raw, at + 16 * i) for i in range(nw)]; at += 16 * nw
    pos = np.frombuffer(raw, "<i2", 4 * npos, at).reshape(npos, 4)
    ws = np.frombuffer(raw, "<u2", 4 * npos, at).reshape(npos, 4)[:, 3]; at += 8 * npos
    at += 8 * nnrm
    parts = [struct.unpack_from("<4I", raw, at + 16 * i) for i in range(nparts)]; at += 16 * nparts
    strips = raw[at:at + nstrip]
    return bones, binds, w, pos[:, :3].astype(np.float32) / 16, ws, parts, strips


def _affine(m):
    a = np.eye(4, dtype=np.float64); a[:3, :] = np.asarray(m, np.float64).reshape(3, 4); return a


def bake(raw, pose, header_texture):
    """raw: model blob; pose: [root world 12 floats, bone 1 .. n world 12 floats]; header_texture(header) -> RGBA
    array. Returns (atlas RGBA 128 x 256, centre (3), half width, half height) or None."""
    bones, binds, w, p, ws, parts, strips = _model_arrays(raw)
    if len(pose) < bones + 1: return None
    root_inv = np.linalg.inv(_affine(pose[0]))
    mats = np.stack([(root_inv @ _affine(pose[b + 1]) @ _affine(binds[b]))[:3] for b in range(bones)])
    wsm = np.zeros((len(w), 3, 4))
    for i, (b0, b1, b2, cnt, w0, w1, w2) in enumerate(w):
        for b, x in list(zip((b0, b1, b2), (w0, w1, w2)))[:max(1, cnt)]: wsm[i] += x * mats[b]
    hp = np.concatenate([p, np.ones((len(p), 1), np.float32)], 1)
    v = np.einsum("nij,nj->ni", wsm[ws], hp)                 # positions in the root frame
    tris = []
    for role, hdr, at, size in parts:
        tex = header_texture(hdr)
        q = at; end = at + size
        while q < end:
            n = struct.unpack_from("<I", strips, q)[0]; q += 4
            c = np.frombuffer(strips, "<u2", 4 * n, q).reshape(n, 4); q += 8 * n
            for k in range(2, n):
                a, b, d = (c[k - 2], c[k - 1], c[k]) if k % 2 == 0 else (c[k - 1], c[k - 2], c[k])
                tris.append((a, b, d, tex))
    if not tris: return None
    lo, hi = v.min(0), v.max(0); centre = (lo + hi) / 2
    radius = float(np.sqrt(((v[:, [0, 2]] - centre[[0, 2]]) ** 2).sum(1)).max()) * 1.02 + 1
    half_h = float(hi[1] - lo[1]) / 2 * 1.02 + 1
    atlas = np.zeros((2 * VIEW, 4 * VIEW, 4), np.uint8)
    ys, xs = np.mgrid[0:VIEW, 0:VIEW]; px = (xs + .5) / VIEW * 2 - 1; py = 1 - (ys + .5) / VIEW * 2
    for k in range(8):
        yaw = k * np.pi / 4
        d = np.array([np.sin(yaw), 0, np.cos(yaw)])           # towards the viewer
        right = np.array([np.cos(yaw), 0, -np.sin(yaw)])
        rel = v - centre
        sx = rel @ right / radius; sy = rel[:, 1] / half_h; sz = rel @ d
        img = np.zeros((VIEW, VIEW, 4), np.uint8); zb = np.full((VIEW, VIEW), -1e30)
        for a, b, c, tex in tris:
            ia, ib, ic = int(a[0]), int(b[0]), int(c[0])
            x0, y0, x1, y1, x2, y2 = sx[ia], sy[ia], sx[ib], sy[ib], sx[ic], sy[ic]
            den = (y1 - y2) * (x0 - x2) + (x2 - x1) * (y0 - y2)
            if abs(den) < 1e-9: continue
            gx0 = int(max(0, np.floor((min(x0, x1, x2) + 1) / 2 * VIEW))); gx1 = int(min(VIEW, np.ceil((max(x0, x1, x2) + 1) / 2 * VIEW)))
            gy0 = int(max(0, np.floor((1 - max(y0, y1, y2)) / 2 * VIEW))); gy1 = int(min(VIEW, np.ceil((1 - min(y0, y1, y2)) / 2 * VIEW)))
            if gx0 >= gx1 or gy0 >= gy1: continue
            X = px[gy0:gy1, gx0:gx1]; Y = py[gy0:gy1, gx0:gx1]
            l0 = ((y1 - y2) * (X - x2) + (x2 - x1) * (Y - y2)) / den
            l1 = ((y2 - y0) * (X - x2) + (x0 - x2) * (Y - y2)) / den
            l2 = 1 - l0 - l1
            inside = (l0 >= -1e-4) & (l1 >= -1e-4) & (l2 >= -1e-4)
            if not inside.any(): continue
            z = l0 * sz[ia] + l1 * sz[ib] + l2 * sz[ic]
            zone = zb[gy0:gy1, gx0:gx1]; take = inside & (z > zone)
            if not take.any(): continue
            u = (l0 * a[2] + l1 * b[2] + l2 * c[2]) / 32768.0; vv = (l0 * a[3] + l1 * b[3] + l2 * c[3]) / 32768.0
            th, tw = tex.shape[:2]
            tx = (np.floor(u * tw).astype(np.int64)) % tw; ty = (np.floor(vv * th).astype(np.int64)) % th
            col = tex[ty, tx]
            zone[take] = z[take]
            sub = img[gy0:gy1, gx0:gx1]; sub[take, :3] = col[take, :3]; sub[take, 3] = 255
        ox, oy = (k % 4) * VIEW, (k // 4) * VIEW
        atlas[oy:oy + VIEW, ox:ox + VIEW] = img
    # bleed covered colours one texel into the clear area so bilinear filtering does not darken the outline
    rgb = atlas[..., :3].astype(np.int32); a = atlas[..., 3] > 0
    for dy, dx in ((0, 1), (0, -1), (1, 0), (-1, 0)):
        sh = np.roll(np.roll(a, dy, 0), dx, 1); src = np.roll(np.roll(rgb, dy, 0), dx, 1)
        fill = ~a & sh; rgb[fill] = src[fill]
    atlas[..., :3] = rgb.astype(np.uint8)
    return atlas, centre.astype(np.float32), radius, half_h
