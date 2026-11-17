import pandas as pd, numpy as np
S='/private/tmp/claude-501/-Users-alexa-Documents-centro-decisiones-chatbot-ssp-uganda-data/618073b8-d02a-423b-ba35-6800d39cc3b9/scratchpad/review'
m=pd.read_pickle(f'{S}/convs6.pkl'); m['genuine']=m.valid & m.key_on_screen
s=m[m.folder=='e4_S']
rng=np.random.default_rng(3)
for col in ('valid','valid_c','genuine'):
    g=s.groupby(['q','arm'])[col].mean().unstack()  # per question rates
    qs=g.index.to_numpy()
    def inter(G): return ((G.C-G.R)-(G.F-G.P)).mean()
    def rp(G): return (G.R-G.P).mean()
    est=inter(g); bs=[];bs2=[]
    # two-stage bootstrap: resample questions, then conversations within question-arm
    for _ in range(4000):
        qq=rng.choice(qs,len(qs),replace=True)
        rows=[]
        for q in qq:
            r={}
            for a in 'PRFCH':
                v=s[(s.q==q)&(s.arm==a)][col].to_numpy().astype(float)
                r[a]=rng.choice(v,len(v),replace=True).mean()
            rows.append(r)
        G=pd.DataFrame(rows); bs.append(inter(G)); bs2.append(rp(G))
    print(col,'interaction %.3f 95%% CI [%.3f, %.3f]'%(est,*np.percentile(bs,[2.5,97.5])),'| R-P %.3f CI [%.3f, %.3f]'%(rp(g),*np.percentile(bs2,[2.5,97.5])))
