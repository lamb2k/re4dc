#!/usr/bin/env python3
"""decode_qr.py (lane qa20): read the QA disc's Diagnostics QR snapshot from photos or screenshots.

The QA menu's Diagnostics page (game/qa_menu.cpp, QA_MENU=1) shows the snapshot as QR pages, each one
"RE4DCQA <p>/<n>\\n" followed by a slice of the text: key=value lines (build, room, preset, fps, ms buckets, heap 4, KOS,
VRAM, disc, Ganados alive, live effects), then LOG and the last log lines.

Usage: decode_qr.py <image> [<image> ...]   (any order; one photo may hold one page)
Prints the joined snapshot, and the fields as "key: value". Exit 1 when a page is missing.
Needs one QR reader: `pip install zxing-cpp pillow` (preferred) or `pip install opencv-python-headless`.
"""
import re, sys


def read_codes(path):
    try:
        import zxingcpp
        from PIL import Image
        img = Image.open(path).convert('L')
        out = [r.text for r in zxingcpp.read_barcodes(img)]
        if out:
            return out
        # a photo of a CRT: try a few contrast levels
        for t in (96, 128, 160):
            out = [r.text for r in zxingcpp.read_barcodes(img.point(lambda v, t=t: 255 if v > t else 0))]
            if out:
                return out
        return []
    except ImportError:
        import cv2
        img = cv2.imread(path)
        ok, texts, _, _ = cv2.QRCodeDetector().detectAndDecodeMulti(img)
        return [t for t in texts if t] if ok else []


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    pages, total = {}, None
    for p in sys.argv[1:]:
        for text in read_codes(p):
            m = re.match(r'RE4DCQA (\d+)/(\d+)\n', text)
            if not m:
                print('%s: not a QA snapshot code' % p, file=sys.stderr)
                continue
            pages[int(m.group(1))] = text[m.end():]
            total = int(m.group(2))
            print('%s: page %s/%s' % (p, m.group(1), m.group(2)), file=sys.stderr)
    if not total:
        sys.exit('no QA snapshot page found')
    missing = [i for i in range(1, total + 1) if i not in pages]
    text = ''.join(pages.get(i, '\n[page %d missing]\n' % i) for i in range(1, total + 1))
    print(text)
    stats, _, log = text.partition('\nLOG\n')
    print('---- fields')
    for line in stats.splitlines()[1:]:
        for tok in re.findall(r'(\S+?)=(\S+)', line):
            head = line.split()[0] if '=' not in line.split()[0] else ''
            print('%s%s: %s' % (head + '.' if head else '', tok[0], tok[1]))
    print('---- %d log lines' % len(log.splitlines()))
    if missing:
        print('missing pages: %s' % missing, file=sys.stderr)
        sys.exit(1)


main()
