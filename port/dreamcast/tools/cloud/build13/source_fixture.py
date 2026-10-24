"""Public full-wrapper-v5 / INC fixture for the actual PS2 world exporter.

No recovered package bytes or game geometry. Three independent wavy grids use
OP/PT/TR policy, ordinary source strips, prelit colours and repeated placement.
The generated wrapper obeys the current SpanPackage format, not a mocked reader.
"""
import json
from pathlib import Path
import struct
import zlib


def align(data,n=4):
    data.extend(bytes(-len(data)%n))


def generate(folder):
    folder=Path(folder);folder.mkdir(parents=True,exist_ok=True)
    positions=[];uvs=[];corners=[];batches=[];bounds=[];part_ranges=[]
    nx,nz=20,12
    for part in range(3):
        base=len(positions)
        for z in range(nz):
            for x in range(nx):
                positions.append((x*125+part*3500,((x+z)%5)*3,z*125))
                uvs.append((x*32,z*32))
        first=len(corners)
        for z in range(nz-1):
            for x in range(nx-1):
                a=base+z*nx+x;b=a+1;c=a+nx;d=c+1
                for tri in ((a,c,b),(b,c,d)):
                    # A source position's high bit ends this authored strip.
                    for k,vi in enumerate(tri):
                        corners.append((vi|(0x8000 if k==2 else 0),vi,(vi//nx)%2))
        count=len(corners)-first
        batches.append((first,count,part,part,0))
        pts=positions[base:]
        bounds.append((first,count,0,*[min(p[k] for p in pts) for k in range(3)],
                       *[max(p[k] for p in pts) for k in range(3)]))
        part_ranges.append((first,count))
    pool=bytearray();spans=[]
    for data,count in ((b''.join(struct.pack('<3h',*p) for p in positions),len(positions)),
                       (b''.join(struct.pack('<2h',*v) for v in uvs),len(uvs)),
                       (bytes([128,128,128,128,100,120,110,128]),2)):
        align(pool);spans.append((len(pool),count));pool.extend(data)
    align(pool);pool.extend(struct.pack('<f',1.0))
    align(pool);spans.append((len(pool),len(corners)))
    pool.extend(b''.join(struct.pack('<3H',*v) for v in corners));align(pool)
    pool_bytes=len(pool)
    template=struct.pack('<HBB8IfII',7,0,0,*[x for span in spans for x in span],1.0,0,3)
    materials=b''.join(struct.pack('<HH12s',7,i,bytes(12)) for i in range(3))
    authored=b''.join(struct.pack('<IIHHI',*b) for b in batches)
    ranges=[];placed_bounds=[];placements=[]
    for placement in range(2):
        for part,(first,count) in enumerate(part_ranges):
            ranges.append((placement,0,part,0,len(placed_bounds),1,first,count))
            placed_bounds.append(bounds[part])
        affine=[1.,0.,0.,float(placement*15000),0.,1.,0.,0.,0.,0.,1.,0.]
        placements.append(struct.pack('<6H5I12f',placement,0,placement,placement,0,0,
                                      0,placement*3,3,0xffffffff,0,*affine))
    tables=[(template,1),(materials,3),(authored,3),
            (b''.join(struct.pack('<4H4I',*r) for r in ranges),len(ranges)),
            (b''.join(placements),len(placements)),(bytes(2*64),2),(bytes(2*144),2),
            (b''.join(struct.pack('<IHH6h',*r) for r in placed_bounds),len(placed_bounds))]
    table_spans=[]
    for data,count in tables:
        align(pool);table_spans.append((len(pool),count));pool.extend(data)
    header=bytearray(224)
    struct.pack_into('<8sII',header,0,b'RE4DCRM\0',5,224)
    struct.pack_into('<I',header,92,zlib.crc32(pool))
    triangles=3*2*(nx-1)*(nz-1)*2  # parts * quads' triangles * placements
    struct.pack_into('<I',header,124,triangles)
    struct.pack_into('<4I',header,128,0x123,0x50,len(pool),8)
    for i,span in enumerate(table_spans):struct.pack_into('<II',header,144+8*i,*span)
    struct.pack_into('<I',header,208,pool_bytes)
    wrapper=folder/'public-world.r4p';wrapper.write_bytes(header+pool)
    # ps2src.load_tables deliberately expects the current production array
    # counts. Unused rows are explicit; the fixture does not weaken that reader.
    textures=['{0x%08xu,0x%08xu,64,64,0,{0x1p+0f,0x1p+0f,0x1p+0f}}'%(0x100+i,0x200+i)
              if i<3 else '{}' for i in range(98)]
    policy=['{%d,%d,%d}'%(i%3,i%3,i%3) for i in range(342)]
    lighting=['{'+','.join(['0x0p+0f']*39)+'}' for _ in range(22)]
    text='// Public synthetic fixture; no recovered game data.\n'
    text+='ps2_textures[98] = {'+','.join(textures)+'};\n'
    text+='ps2_policy[342] = {'+','.join(policy)+'};\n'
    text+='ps2_reference_lighting[22] = {'+','.join(lighting)+'};\n'
    text+='ps2_ambient[3] = {0x0p+0f,0x0p+0f,0x0p+0f};\n'
    text+='ps2_payload_crc=0x%08xu;\n'%zlib.crc32(pool)
    inc=folder/'public-world.inc';inc.write_text(text)
    return dict(wrapper=wrapper,inc=inc,positions=len(positions),source_corner_records=len(corners),
                source_triangles=triangles,placements=2,parts=3,grid=[nx,nz])


if __name__=='__main__':
    import argparse
    ap=argparse.ArgumentParser();ap.add_argument('out',type=Path)
    print(json.dumps(generate(ap.parse_args().out),default=str))
