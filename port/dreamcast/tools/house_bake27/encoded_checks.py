"""Independent native VQ decode and texel-error checks over occupied atlas pixels."""
import argparse,hashlib,importlib.util,json
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw
ap=argparse.ArgumentParser();ap.add_argument('--dir',type=Path,required=True);ap.add_argument('--decoder',type=Path,required=True);a=ap.parse_args()
spec=importlib.util.spec_from_file_location('independent_native_decoder',a.decoder);decoder=importlib.util.module_from_spec(spec);spec.loader.exec_module(decoder)
atlas=json.loads((a.dir/'ATLAS-EXCHANGE.json').read_text());rows=[]
for role in ('wall','roof'):
    pixels,metadata=decoder.decode(a.dir/(role+'-baked.re4tex'));Image.fromarray(pixels).save(a.dir/(role+'-native-decoded.png'))
    preview=np.asarray(Image.open(a.dir/(role+'-vq-preview.png')).convert('RGBA'));difference=np.abs(pixels.astype(int)-preview.astype(int))
    # pvrtex expands bit channels using bit replication while the independent
    # decoder uses integer scaling; tolerate that documented <=1LSB rounding.
    assert difference.max()<=1
    mask=Image.new('L',(512,512),0);draw=ImageDraw.Draw(mask)
    for t in atlas[role]['target_triangles']:draw.polygon([(u*512,v*512) for u,v in t['baked_uv_top_left']],fill=255)
    occupied=np.asarray(mask)>0;source=np.asarray(Image.open(a.dir/(role+'-baked.png')).convert('RGB')).astype(float);output=pixels[:,:,:3].astype(float)
    errors=output[occupied]-source[occupied];mse=float((errors**2).mean())
    rows.append(dict(role=role,native_decode=metadata,independent_decoder_sha256=hashlib.sha256(a.decoder.read_bytes()).hexdigest(),native_vs_pvrtex_max_channel_difference=int(difference.max()),occupied_atlas_pixels=int(occupied.sum()),mean_absolute_channel_error=float(np.abs(errors).mean()),max_channel_error=float(np.abs(errors).max()),psnr_db=float(10*np.log10(255**2/mse)) if mse else None))
(a.dir/'ENCODED-IMAGE-CHECKS.json').write_text(json.dumps(rows,indent=2)+'\n');print(json.dumps(rows,indent=2))
