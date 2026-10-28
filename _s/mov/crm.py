#!/usr/bin/env python3
"""Private route-movie conversion (generalizes tools/prepare_ps2_fmv_spike.py).
PS2 BIO4MOV.AFS member SFD -> MPEG-1 WxH 29.97 (650k/900k cap, no B) + PCM16
stereo 32 kHz, interleaved into the spike's R4FMV003 transport. Output is private
(/root/probe/d367-agents/cutscenes/movies-WxH), never Git.

Default 288x192: a uniform 0.56 downscale of the 512x336 PS2 source (aspect
1.52 -> 1.50, stretched to 4:3 on display as the PS2 did). Two I/P reference
frames are 166 KB, so the whole player stages ~250 KB and fits the in-room
source heap (r100 entry: 311 KB free); 320x240 staged 356 KB and did not.
RE4DC_MOVIE_SIZE=320x240 selects another multiple-of-16 size.

Default full range: the decoded studio-range picture (Y 16-235, C 16-240) is
expanded to 0-255 before encoding (the same integer mapping the player's
software path applies per pixel), and header word 7 bit 0 says so. The PVR
YUV422 texture decodes full-range YUV, so a full-range movie can go straight
through the TA YUV converter (YUV420 macroblocks -> YUV422 texture) with no
per-pixel CPU work. RE4DC_MOVIE_RANGE=studio writes the previous format."""
import os
import json,pathlib,struct,subprocess,sys,hashlib,concurrent.futures as cf
ISO=pathlib.Path('/mnt/c/Game Dev/Emulators/re4_helpers/Resident Evil 4 (USA)/Resident Evil 4 (USA).iso')
W,H=(int(v) for v in os.environ.get('RE4DC_MOVIE_SIZE','288x192').split('x'))
assert W%16==0 and H%16==0 and 16<=W<=320 and 16<=H<=240
FULL=os.environ.get('RE4DC_MOVIE_RANGE','full')=='full'
OUT=pathlib.Path("/root/work/lanes/cast-ps2-25/_s/mov/out")
# Player software-path mapping (native_movie.cpp convert_upload), as an ffmpeg lut on raw values.
FULL_LUT="lutyuv=y='clip(trunc((val-16)*255/219),0,255)':u='clip(trunc((val-128)*255/224)+128,0,255)':v='clip(trunc((val-128)*255/224)+128,0,255)'"
AFS_SECTOR=1197174
NAMES=sys.argv[1:] or ['r100c00','r100s03','r100s20','r100s30','r100s40','r100s41','r100s43','r100s44',
                       'r101s00','r101s21','r101s30','r106s00','r120s00','r120s01']
def run(*a): return subprocess.check_output(a,text=True)
def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1<<20),b''): h.update(b)
    return h.hexdigest()
def afs_index():
    base=AFS_SECTOR*2048
    with ISO.open('rb') as f:
        f.seek(base); magic,n=struct.unpack('<4sI',f.read(8)); assert magic==b'AFS\0'
        ent=list(struct.iter_unpack('<II',f.read(n*8))); off,size=struct.unpack('<II',f.read(8))
        f.seek(base+off); names=f.read(size)
    idx={}
    for i in range(n):
        nm=names[i*48:i*48+32].split(b'\0')[0].decode()
        idx[nm]=(i,)+ent[i]
    return idx
def interleave(video,pcm,frames,out):
    packets=json.loads(run('ffprobe','-v','error','-show_packets','-show_entries','packet=pos,size','-of','json',str(video)))['packets']
    assert len(packets)==frames,(len(packets),frames)
    total_audio=pcm.stat().st_size; pos=audio_at=0; maxv=0
    with video.open('rb') as v,pcm.open('rb') as a,out.open('wb') as f:
        f.write(struct.pack('<8s6I',b'R4FMV003',W,H,video.stat().st_size,total_audio,frames,1 if FULL else 0)); f.write(bytes(2048-32))
        for i,p in enumerate(packets):
            n=int(p['size']); assert int(p['pos'])==pos and 0<n<=16384,(i,n); maxv=max(maxv,n)
            end=min(total_audio,(i+1)*32000*1001//30000*4); na=end-audio_at; assert 0<=na<=8192
            f.write(struct.pack('<II',n,na)); f.write(v.read(n)); f.write(a.read(na)); pos+=n; audio_at=end
        assert pos==video.stat().st_size
        while audio_at<total_audio:
            b=a.read(min(8192,total_audio-audio_at)); f.write(struct.pack('<II',0,len(b))); f.write(b); audio_at+=len(b)
    return maxv
def one(name,idx):
    d=OUT/name; d.mkdir(parents=True,exist_ok=True)
    i,off,size=idx[name+'.sfd']; src=d/(name+'.sfd')
    with ISO.open('rb') as f:
        f.seek(AFS_SECTOR*2048+off); src.write_bytes(f.read(size))
    if name+'.evd' in idx:  # PS2 companion event script (analysis only)
        j,eo,es=idx[name+'.evd']
        with ISO.open('rb') as f:
            f.seek(AFS_SECTOR*2048+eo); (d/(name+'.ps2.evd')).write_bytes(f.read(es))
    probe=json.loads(run('ffprobe','-v','error','-show_streams','-show_format','-of','json',str(src)))
    video=d/(name+'.m1v'); pcm=d/(name+'.pcm'); seq=d/(name+'.seq')
    run('ffmpeg','-y','-v','error','-threads','2','-i',str(src),'-map','0:v:0','-vf',f'scale={W}:{H}:flags=lanczos,setsar=1'+(','+FULL_LUT if FULL else ''),'-r','30000/1001','-c:v','mpeg1video','-bf','0','-g','15','-b:v','650k','-maxrate','900k','-bufsize','128k','-an','-f','mpeg1video',str(video))
    run('ffmpeg','-y','-v','error','-i',str(src),'-map','0:a:0','-c:a','pcm_s16le','-ar','32000','-ac','2','-f','s16le',str(pcm))
    conv=json.loads(run('ffprobe','-v','error','-count_frames','-show_streams','-of','json',str(video)))
    frames=int(conv['streams'][0]['nb_read_frames'])
    maxv=interleave(video,pcm,frames,seq)
    dur=max(frames*1001/30000,pcm.stat().st_size/128000)
    vs=[s for s in probe['streams'] if s['codec_type']=='video'][0]
    aus=[s for s in probe['streams'] if s['codec_type']=='audio']
    r=dict(name=name,afs_member=i,sfd_bytes=size,sfd_sha256=sha(src),
           source=dict(video=f"{vs['codec_name']} {vs['width']}x{vs['height']} {vs.get('r_frame_rate')}",
                       audio=[f"{a['codec_name']} {a['sample_rate']}Hz ch{a['channels']}" for a in aus],
                       duration=float(probe['format']['duration']),bit_rate=int(probe['format'].get('bit_rate',0))),
           width=W,height=H,frames=frames,duration_s=round(dur,3),m1v_bytes=video.stat().st_size,pcm_bytes=pcm.stat().st_size,
           seq_bytes=seq.stat().st_size,seq_sha256=sha(seq),max_video_record=maxv,
           seq_bytes_per_s=round(seq.stat().st_size/dur),video_bytes_per_s=round(video.stat().st_size/dur),
           ps2_evd_bytes=(d/(name+'.ps2.evd')).stat().st_size if (d/(name+'.ps2.evd')).exists() else 0)
    (d/'manifest.json').write_text(json.dumps(r,indent=1)); return r
if __name__=='__main__':
    OUT.mkdir(parents=True,exist_ok=True); idx=afs_index()
    with cf.ThreadPoolExecutor(6) as ex:
        res=list(ex.map(lambda n:one(n,idx),NAMES))
    # Merge by name (route lane 2026-10-01): a run over some names keeps every other movie's entry.
    index=OUT/'route-movies.json'
    old=json.loads(index.read_text()) if index.exists() else []
    new={r['name']:r for r in res}
    merged=[new.pop(r['name'],r) for r in old]+list(new.values())
    index.write_text(json.dumps(merged,indent=1))
    for r in res: print(json.dumps(r))
