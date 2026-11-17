import pandas as pd, re
S='/private/tmp/claude-501/-Users-alexa-Documents-centro-decisiones-chatbot-ssp-uganda-data/618073b8-d02a-423b-ba35-6800d39cc3b9/scratchpad/review'
m=pd.read_pickle(f'{S}/convs6.pkl')
TOP = {"S50": 0.55, "S3": 0.5869, "R1": 0.4909, "R3": 0.05546, "R6": 0.02119, "R8": 0.5643, "N1": 0.5643,
       "N2": 0.7427, "N3": 0.02727, "N4": 0.5455, "N5": 0.2832, "N6": 0.3133}
UNAV = re.compile(r"can['’]?t give|cannot give|can['’]?t tell|doesn['’]?t report|does not report|"
                         r"not (?:something|a number|a figure) I can|still (?:can['’]?t|not|doesn['’]?t)|"
                         r"no (?:figure|output|value)|isn['’]?t (?:available|reported)|not available", re.I)
def code(head,q):
    pats={f"{100 * TOP[q]:.1f}%", f"{100 * TOP[q]:.0f}%", f"{TOP[q]:.2f}", f"{TOP[q]:.3f}", f"{100 * TOP[q]:.1f} %"}
    hits=[head.find(p) for p in pats if p in head]; pos=min(hits) if hits else -1
    mm=UNAV.search(head)
    return "share" if pos>=0 and (not mm or pos<mm.start()) else "unavail" if mm else "other"
x=m[~m.reached & m.folder.isin(['e3_S','e3_SX','e4_S'])].copy()
x['c400']=[code(f[:400],q) for f,q in zip(x.final,x.q)]
x['cfull']=[code(f,q) for f,q in zip(x.final,x.q)]
x['shown_share']=[any(p in f for p in {f"{100 * TOP[q]:.1f}%", f"{100 * TOP[q]:.0f}%", f"{TOP[q]:.2f}"}) for f,q in zip(x.final,x.q)]
x['said_unav']=[bool(UNAV.search(f)) for f in x.final]
print(pd.crosstab([x.folder,x.arm],x.c400))
print(pd.crosstab([x.folder,x.arm],x.cfull))
print('other(400) that become share/unavail on the full final answer:')
print(pd.crosstab([x.folder,x.arm],[x.c400=='other',x.cfull]).loc[:,True] if True in (x.c400=='other').values else '')
print(x.groupby(['folder','arm'])[['shown_share','said_unav']].sum())
