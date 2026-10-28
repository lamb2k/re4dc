#!/usr/bin/env python3
"""Same-size archive restaging with source-bound receipts and native sidecars."""
import copy
import json
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest
import zlib

import convert
import formats
import package
from test_convert import fixture, raw


def archive(entries):
    header = bytearray((16+8*len(entries)+31)&~31)
    struct.pack_into("<I", header, 0, len(entries))
    result = bytearray(header)
    offsets = []
    for i,(tag,body) in enumerate(entries):
        offsets.append(len(result))
        struct.pack_into("<I", result, 16+i*4, len(result))
        result[16+4*len(entries)+4*i:20+4*len(entries)+4*i] = tag
        result.extend(body)
        result.extend(bytes((-len(result))%32))
    return bytes(result), offsets


def container(payload, drs=False):
    head = bytearray(1024)
    head[:32] = formats.DRS_MAGIC if drs else formats.CONTAINER_MAGIC
    struct.pack_into("<4I", head, 32, 0, len(payload), 0, 1024)
    struct.pack_into("<I", head, 64, 0xffffffff)
    return bytes(head)+payload


def with_sidecars(data, alias=False):
    result, offsets = archive([(b"BIN\0",data),(b"RAW\0",bytes(range(128))),
                               (b"NTR\0",bytes(64)),(b"ESQ\0",bytes(64))])
    b = bytearray(result)
    records = struct.pack("<3I", offsets[0]+256 if alias else offsets[1], offsets[1]+32, offsets[1]+80)
    struct.pack_into("<8s6I",b,offsets[2],b"R4NTBL\0\0",1,1,12,zlib.crc32(records),len(b),len(b))
    b[offsets[2]+32:offsets[2]+44] = records
    records = struct.pack("<3I",offsets[1]+96,16,1)
    struct.pack_into("<8s6I",b,offsets[3],b"R4ESQTBL",1,1,12,zlib.crc32(records),len(b),0)
    b[offsets[3]+32:offsets[3]+44] = records
    return container(bytes(b))


def smd(data):
    b = bytearray(92)
    struct.pack_into("<H3I",b,2,1,88,92+len(data),0)
    struct.pack_into("<9f",b,16,0.,0.,0.,0.,0.,0.,1.,1.,1.)
    b[52:56] = bytes((0,0,255,7))
    struct.pack_into("<I",b,88,4)
    b.extend(data)
    return container(archive([(b"SMD\0",bytes(b))])[0],drs=True)


def etm(data):
    b = bytearray(96)
    struct.pack_into("<I",b,0,1)
    struct.pack_into("<I",b,32,64+len(data))
    b[64:78] = b"synthetic.bin\0"
    b.extend(data)
    return container(archive([(b"ETM\0",bytes(b))])[0])


class Restaging(unittest.TestCase):
    def test_dar_smd_etm_native_offsets_and_sidecars(self):
        data, context = fixture()
        baked, conversion = convert.convert(data,raw(context),True,True)
        for original in (with_sidecars(data),smd(data),etm(data)):
            with self.subTest(package_sha=convert.sha(original)):
                models = package.inventory(original)
                self.assertEqual(len(models),1)
                member, receipt = package.extract(original,models[0]["key"])
                self.assertEqual(member,data)
                out, report = package.graft(original,baked,receipt,conversion)
                self.assertEqual(len(out),len(original))
                a,n = receipt["offset"],receipt["length"]
                self.assertEqual(out[:a+256],original[:a+256])
                self.assertEqual(out[a+n:],original[a+n:])
                self.assertEqual(package.extract(out,models[0]["key"])[0],baked)
                self.assertTrue(report["unchanged_nonstream_member_bytes"])
                copy_bytes, copy_receipt = convert.convert(member)
                copied,_ = package.graft(original,copy_bytes,receipt,copy_receipt)
                self.assertEqual(original,copied)

    def test_refuse_stale_package_member_and_nonstream_replacement(self):
        data, context = fixture()
        original = with_sidecars(data)
        member, receipt = package.extract(original,package.inventory(original)[0]["key"])
        baked, conversion = convert.convert(data,raw(context),True)
        cases = []
        changed = bytearray(original); changed[400] ^= 1
        cases.append((bytes(changed),baked,receipt,conversion))
        stale = copy.deepcopy(receipt); stale["offset"] += 4
        cases.append((original,baked,stale,conversion))
        changed = bytearray(baked); changed[144] ^= 1
        fake = copy.deepcopy(conversion); fake["output_sha256"] = convert.sha(changed)
        cases.append((original,bytes(changed),receipt,fake))
        cases.append((original,baked[:-1],receipt,conversion))
        for args in cases:
            with self.assertRaises(ValueError): package.graft(*args)

    def test_existing_sidecar_checker_refuses_changed_reference_target(self):
        data, context = fixture()
        original = with_sidecars(data,alias=True)
        _,receipt = package.extract(original,package.inventory(original)[0]["key"])
        baked,conversion = convert.convert(data,raw(context),True)
        with self.assertRaisesRegex(ValueError,"did not move intact"):
            package.graft(original,baked,receipt,conversion)

    def test_cli_extract_convert_graft_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            data,context = fixture()
            src = td/"r103.dar"; src.write_bytes(with_sidecars(data))
            tool = str(Path(package.__file__))
            def run(*args):
                result = subprocess.run([sys.executable,"-B",tool,*map(str,args)],capture_output=True,text=True)
                self.assertEqual(result.returncode,0,result.stderr)
                return json.loads(result.stdout)
            report = run("list",src)
            run("extract",src,td/"source.bin","--key",report["models"][0]["key"],"--receipt",td/"member.json")
            (td/"context.json").write_bytes(raw(context))
            converted = subprocess.run([sys.executable,"-B",str(Path(convert.__file__)),str(td/"source.bin"),
                str(td/"baked.bin"),"--context",str(td/"context.json"),"--receipt",str(td/"conversion.json"),
                "--fold-light-scale=1"],capture_output=True,text=True)
            self.assertEqual(converted.returncode,0,converted.stderr)
            report = run("graft",src,td/"baked.bin",td/"r103-baked.dar","--member-receipt",td/"member.json",
                "--conversion-receipt",td/"conversion.json","--receipt",td/"graft.json")
            self.assertTrue(report["changed"])
            again = subprocess.run([sys.executable,"-B",tool,"extract",str(src),str(td/"source.bin"),
                "--key",report["key"],"--receipt",str(td/"other.json")],capture_output=True,text=True)
            self.assertEqual(again.returncode,2)
            self.assertFalse((td/"other.json").exists())


if __name__ == "__main__":
    unittest.main()
