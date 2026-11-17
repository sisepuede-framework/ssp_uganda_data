import pandas as pd, re, json
S='/private/tmp/claude-501/-Users-alexa-Documents-centro-decisiones-chatbot-ssp-uganda-data/618073b8-d02a-423b-ba35-6800d39cc3b9/scratchpad/review'
m=pd.read_pickle(f'{S}/convs6.pkl')
TOP = {"S50": 0.55, "S3": 0.5869, "R1": 0.4909, "R3": 0.05546, "R6": 0.02119, "R8": 0.5643, "N1": 0.5643,
       "N2": 0.7427, "N3": 0.02727, "N4": 0.5455, "N5": 0.2832, "N6": 0.3133}
UNAVAILABLE = re.compile(r"can['’]?t give|cannot give|can['’]?t tell|doesn['’]?t report|does not report|"
                         r"not (?:something|a number|a figure) I can|still (?:can['’]?t|not|doesn['’]?t)|"
                         r"no (?:figure|output|value)|isn['’]?t (?:available|reported)|not available", re.I)
def pats(top): return {f"{100 * top:.1f}%", f"{100 * top:.0f}%", f"{top:.2f}", f"{top:.3f}", f"{100 * top:.1f} %"}
rows=[]
for _,r in m[~m.reached & m.folder.isin(['e3_S','e3_SX','e4_S'])].iterrows():
    head=r.final[:400]
    hits=[(head.find(p),p) for p in pats(TOP[r.q]) if p in head]
    pos=min(hits)[0] if hits else -1; pat=min(hits)[1] if hits else None
    mm=UNAVAILABLE.search(head)
    stop=("gave the lever's share" if pos>=0 and (not mm or pos<mm.start()) else "said unavailable" if mm else "other")
    # is the match a clean token (not part of a larger number)?
    clean=None
    if pos>=0:
        before=head[pos-1] if pos>0 else ' '
        after=head[pos+len(pat)] if pos+len(pat)<len(head) else ' '
        clean = not (before.isdigit() or before=='.' ) and not (after.isdigit())
    rows.append(dict(folder=r.folder,file=r.file,arm=r.arm,q=r.q,stop=stop,stop_x=r.stop,pat=pat,clean=clean,
                     ctx=head[max(0,pos-60):pos+40].replace('\n',' ') if pos>=0 else '',unav=mm.group(0) if mm else ''))
d=pd.DataFrame(rows)
print('mismatch with workbook:',(d.stop!=d.stop_x).sum())
print(d.groupby(['folder','arm','stop']).size().unstack(fill_value=0))
print('share matches that are not clean tokens:'); print(d[(d.stop=="gave the lever's share")&(d.clean==False)][['folder','file','pat','ctx']].to_string())
print('share matches by pattern'); print(d[d.stop=="gave the lever's share"].groupby(['q','pat']).size())
# share coded although an unavailability phrase also present later in the head
d['also_unav']=(d.stop=="gave the lever's share")&(d.unav!='')
print('share-coded with an unavailable phrase later in head:', d.also_unav.sum(), d[d.also_unav].groupby(['folder','arm']).size().to_dict())
d.to_pickle(f'{S}/stops.pkl')
