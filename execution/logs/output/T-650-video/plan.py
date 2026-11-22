import wave, json, sys, numpy as np
S=sys.argv[1]; FPS=15
wf=wave.open(f'{S}/audio44.wav'); SR=wf.getframerate()
a=np.frombuffer(wf.readframes(wf.getnframes()),dtype=np.int16).astype(np.float32)
DUR=len(a)/SR
db=np.load(f'{S}/env.npy'); H=0.02
sp=db>-55
# speech regions
regs=[];i=0;n=len(sp)
while i<n:
    if sp[i]:
        j=i
        while j<n and sp[j]: j+=1
        regs.append([i*H,j*H]); i=j
    else: i+=1
merged=[]
for r in regs:
    if merged and r[0]-merged[-1][1]<0.3: merged[-1][1]=r[1]
    else: merged.append(r)
merged=[r for r in merged if r[1]-r[0]>=0.08]
MAXGAP=1.0; KEEP_AFTER=0.45; KEEP_BEFORE=0.35
keep=[]
# lead-in
start=max(0,merged[0][0]-0.5); cur=[start,None]
for k in range(len(merged)-1):
    e=merged[k][1]; s=merged[k+1][0]
    if s-e>MAXGAP:
        cur[1]=e+KEEP_AFTER; keep.append(cur); cur=[s-KEEP_BEFORE,None]
cur[1]=min(DUR,merged[-1][1]+1.2); keep.append(cur)
# video mapping pieces (audio time ranges); default sync
PIECES=[ # (a0,a1,v0,vmax)
 (553.9,600.8,553.9,566.0),   # 'very hard case ... explainable' over cancellation tiles
 (716.48,722.6,549.3,553.7),  # 'rewards module ... budget' over rewards results
 (866.43,906.6,879.0,906.3),  # 'evaluators upload test flights' + responsible design over Test data
]
# output timeline
out=[];t=0.0
for k0,k1 in keep:
    out.append((t,k0,k1)); t+=k1-k0
TOT=t
def src_audio(to):
    for o,k0,k1 in out:
        if o<=to<o+(k1-k0): return k0+(to-o)
    return out[-1][2]
# output start of each piece
def out_of_src(ts):
    for o,k0,k1 in out:
        if k0<=ts<=k1: return o+(ts-k0)
        if ts<k0: return o
    return TOT
pstart=[out_of_src(p[0]) for p in PIECES]
NF=int(np.ceil(TOT*FPS))
srcf=[]
for f in range(NF):
    to=(f+0.5)/FPS; sa=src_audio(to); vs=None
    for p,ps in zip(PIECES,pstart):
        if p[0]<=sa<p[1]:
            vs=min(p[2]+(to-ps),p[3]); break
    if vs is None: vs=sa
    srcf.append(min(int(vs*FPS),15284))
# group into segments: continuous (+1) or freeze (+0)
segs=[];f=0
while f<NF:
    g=f+1
    if g<NF and srcf[g]==srcf[f]:
        while g<NF and srcf[g]==srcf[f]: g+=1
        segs.append((srcf[f],g-f,1))
    else:
        while g<NF and srcf[g]==srcf[g-1]+1: g+=1
        segs.append((srcf[f],g-f,0))
    f=g
# merge tiny freeze segments (1 frame) into neighbours is fine as-is
json.dump({"segs":segs,"keep":keep,"TOT":TOT,"NF":NF},open(f'{S}/plan.json','w'))
# audio: concatenate with 10ms fades
fade=int(0.01*SR); parts=[]
for k0,k1 in keep:
    x=a[int(round(k0*SR)):int(round(k1*SR))].copy()
    r=np.linspace(0,1,fade); x[:fade]*=r; x[-fade:]*=r[::-1]; parts.append(x)
y=np.concatenate(parts); need=int(round(NF/FPS*SR))
y=np.pad(y,(0,max(0,need-len(y))))[:need]
w=wave.open(f'{S}/edited_audio.wav','wb'); w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
w.writeframes(np.clip(y,-32768,32767).astype(np.int16).tobytes()); w.close()
print(f"keep intervals {len(keep)}, output {TOT:.1f}s ({int(TOT//60)}:{TOT%60:04.1f}), frames {NF}, video segments {len(segs)}, freezes {sum(s[2] for s in segs)}")
print("pieces out start:",[round(x,2) for x in pstart])
