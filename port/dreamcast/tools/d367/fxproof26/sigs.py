"""Picture signatures for content matching (lane fxproof26, pure Python + PIL).

sig = the picture premultiplied by alpha (PIL RGBa), box-filtered to 16x16, 1024 bytes. dist(a, b) = RMS over the 4
channels (0..255), min over the 8 rotations/flips of b (a renumbered/re-oriented picture still matches).
"""
from PIL import Image, ImageChops, ImageStat
S = 16
DIH = [None, Image.FLIP_LEFT_RIGHT, Image.FLIP_TOP_BOTTOM, Image.ROTATE_90, Image.ROTATE_180, Image.ROTATE_270,
       Image.TRANSPOSE, Image.TRANSVERSE]


def sig_image(im):
    return im.convert('RGBA').convert('RGBa').resize((S, S), Image.BOX).tobytes()


def sig_rgba(w, h, rgba):
    im = Image.new('RGBA', (w, h)); im.putdata([tuple(p) for p in rgba])
    return sig_image(im)


def img(s):
    return Image.frombytes('RGBA', (S, S), s)


def variants(s):
    i = img(s)
    return [i if t is None else i.transpose(t) for t in DIH]


def dist_img(a, b):
    st = ImageStat.Stat(ImageChops.difference(a, b))
    return (sum(x * x for x in st.rms) / 4) ** 0.5
