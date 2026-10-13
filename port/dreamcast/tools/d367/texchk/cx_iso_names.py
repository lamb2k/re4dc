#!/usr/bin/env python3
"""Fix primary ISO aliases in an owned harness copy; preserve RR/Joliet names."""
import argparse
import hashlib
import inspect
import json
from pathlib import Path


def iso_primary_name(name, directory=False):
    if not name or name in ('.', '..') or any(c in name for c in '/\\;'):
        raise ValueError('expected one filesystem name: ' + repr(name))
    def clean(part):
        return ''.join(c if ('A' <= c <= 'Z' or '0' <= c <= '9' or c == '_') else '_'
                       for c in part.upper())
    if directory or '.' not in name:
        return clean(name)
    stem, ext = name.rsplit('.', 1)
    return clean(stem) + '.' + clean(ext)


def ensure_free_primary(iso, path):
    import pycdlib
    try:
        iso.get_record(iso_path=path)
    except pycdlib.pycdlibexception.PyCdlibInvalidInput:
        return
    raise ValueError('new primary ISO alias collides with an existing entry: ' + path)


def adapt_stage(text):
    """Only alter new primary aliases; source names in RR/Joliet stay exact."""
    directory = "iso.add_directory(iso_path=base+'/'+name.upper().replace('-','_'),rr_name=name,joliet_path=path)"
    file = "name.upper().replace('-','_')+';1'"
    if text.count(directory) != 1 or text.count(file) != 1:
        raise ValueError('unrecognized stage adapter; review before patching')
    text = text.replace(directory, "ip=base+'/'+iso_primary_name(name, directory=True)\n            ensure_free_primary(iso,ip)\n            iso.add_directory(iso_path=ip,rr_name=name,joliet_path=path)")
    text = text.replace(file, "iso_primary_name(name)+';1'")
    text = text.replace("        stream=source.open('rb');streams.append(stream)", "        ensure_free_primary(iso,ip)\n        stream=source.open('rb');streams.append(stream)")
    return text.replace('def ensure_dir(', inspect.getsource(iso_primary_name) + '\n' +
                        inspect.getsource(ensure_free_primary) + '\ndef ensure_dir(', 1)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    raw = args.input.read_bytes()
    text = adapt_stage(raw.decode())
    compile(text, str(args.output), 'exec')
    with args.output.open('x') as stream:
        stream.write(text)
    report = dict(input=str(args.input), input_sha256=hashlib.sha256(raw).hexdigest(),
                  output=str(args.output), output_sha256=hashlib.sha256(args.output.read_bytes()).hexdigest(),
                  change='Primary ISO aliases only; exact RR and Joliet filenames preserved, including .evd.evq')
    args.output.with_suffix('.provenance.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
