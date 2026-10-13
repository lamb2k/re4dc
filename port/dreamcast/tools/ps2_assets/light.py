"""Existing offline light calibration for NORMAL scenery groups."""
import math

def gx_light(l, p):
    """GX light object for scenery (obj_flag 0: brightness = Intensity), world space."""
    col = [min(255, int(c * l["col"][3] * 0.0078125)) for c in l["col"][:3]]
    obj = list(p["pos"])
    if l["xD"] == 5:      # parallel: GX position obj_pos + n, constant gain
        return dict(i=l["i"], kind="parallel", col=col, pos=[obj[k] + l["n"][k] for k in range(3)], dir=[0.0, 0.0, 1.0],
                    a=[l["intensity"], 0.0, 0.0], k=[1.0, 0.0, 0.0])
    if l["xD"] == 2:      # quadratic
        k2 = (l["intensity"] - 0.1) / 0.1 / (l["R"] * l["R"]) if l["R"] else 0.0
        return dict(i=l["i"], kind="quadratic", col=col, pos=list(l["pos"]), dir=[0.0, 0.0, 1.0],
                    a=[l["intensity"], 0.0, 0.0], k=[1.0, 0.0, k2])
    if l["xD"] == 3:      # spot: GXInitLightSpot(A0, GX_SP_COS2), GXInitLightDistAttn(5000, Intensity, GX_DA_MEDIUM)
        cut = l["A0"]
        if cut <= 0.0 or cut > 90.0:
            a = [1.0, 0.0, 0.0]
        else:
            cr = math.cos(math.radians(cut))
            a = [0.0, -cr / (1.0 - cr), 1.0 / (1.0 - cr)]
        br = l["intensity"]
        if br <= 0.0 or br >= 1.0:
            k = [1.0, 0.0, 0.0]
        else:
            k = [1.0, 0.5 * (1.0 - br) / (br * 5000.0), 0.5 * (1.0 - br) / (br * 5000.0 * 5000.0)]
        n = l["n"]
        ln = math.sqrt(sum(x * x for x in n)) or 1.0
        return dict(i=l["i"], kind="spot", col=col, pos=list(l["pos"]), dir=[-x / ln for x in n], a=a, k=k)
    return dict(i=l["i"], kind="unsupported-xD%d" % l["xD"], col=[0, 0, 0], pos=[0, 0, 0], dir=[0, 0, 1], a=[0, 0, 0], k=[1, 0, 0])
