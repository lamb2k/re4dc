"""Sparse word patches to stable slots. Sequential playback uses no decompressor dictionary."""
import struct
from array import array
from sys import byteorder
class Changes:
    def __init__(self):
        self.last = array("I")
    def encode(self, data):
        words = array("I")
        words.frombytes(data)
        if byteorder != "little":
            words.byteswap()
        old = self.last
        self.last = words
        if len(old) < len(words):
            old.extend([0]*(len(words)-len(old)))
        changes = bytearray()
        for i in range(0,len(words),32):
            mask = 0
            values = []
            for j,(a,b) in enumerate(zip(words[i:i+32],old[i:i+32])):
                if a!=b:
                    mask |= 1<<j
                    values.append(a)
            if mask:
                changes.extend(struct.pack("<2I"+"I"*len(values),i,mask,*values))
        return struct.pack("<I",len(words))+changes
