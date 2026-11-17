import pandas as pd, numpy as np
S='/private/tmp/claude-501/-Users-alexa-Documents-centro-decisiones-chatbot-ssp-uganda-data/618073b8-d02a-423b-ba35-6800d39cc3b9/scratchpad/review'
m=pd.read_pickle(f'{S}/convs6.pkl')
m['genuine']=m.valid & m.key_on_screen
m['own']=m.valid & ~m.key_on_screen & ~m.fp_allruns
pass
def perm(d,col,a,b,rng,N=10000):
    d=d[d.arm.isin([a,b])]
    vals=d[col].astype(float).to_numpy(); isa=(d.arm==a).to_numpy(); qs=d.q.to_numpy()
    obs=vals[isa].mean()-vals[~isa].mean()
    blocks=[np.flatnonzero(qs==q) for q in np.unique(qs)]
    hits=0
    for _ in range(N):
        lab=isa.copy()
        for bl in blocks: lab[bl]=rng.permutation(lab[bl])
        hits+= abs(vals[lab].mean()-vals[~lab].mean())>=abs(obs)-1e-12
    return int(vals[isa].sum()),int(vals[~isa].sum()),obs,(hits+1)/(N+1)
def holm(ps):
    o=np.argsort(ps); adj=[0]*len(ps); run=0
    for k,i in enumerate(o):
        run=max(run,min(1,(len(ps)-k)*ps[i])); adj[i]=run
    return adj
rng=np.random.default_rng(1)
s3=m[m.folder=='e3_S']; sx=m[m.folder=='e3_SX'].assign(arm='X'); 
c3=pd.concat([s3[s3.arm=='P'],sx])
print('\nE3 (set S); outcome: valid (orig) | valid_c (all-runs FPs removed, Mt FNs added) | genuine (key cell on screen)')
for a,b,d in [('H','P',s3),('L','P',s3),('T','P',s3),('L','T',s3),('X','P',c3)]:
    print(a,'vs',b, *[ '%s %d vs %d p=%.4f'%(col,*perm(d,col,a,b,rng)[:2],perm(d,col,a,b,rng)[3]) for col in ('valid','valid_c','genuine')])
s4=m[m.folder=='e4_S']
print('\nE4 (set S)')
for col in ('valid','valid_c','genuine'):
    res=[perm(s4,col,a,b,rng) for a,b in [('R','P'),('C','F'),('F','P'),('C','R'),('C','P'),('R','H')]]
    adj=holm([r[3] for r in res])
    print(col, ['%s %d vs %d p=%.4f holm=%.4f'%(n,r[0],r[1],r[3],h) for n,r,h in zip(['R-P','C-F','F-P','C-R','C-P','R-H'],res,adj)])
    rate={a:s4[s4.arm==a][col].mean() for a in 'PRFC'}
    print('   interaction',round((rate['C']-rate['R'])-(rate['F']-rate['P']),3))
print('\n--- reached with the lever filter at 2050 (key cell displayed)')
for a,b,d in [('H','P',s3),('L','P',s3),('T','P',s3),('X','P',c3)]:
    r=perm(d,'reached_strict',a,b,rng); print('E3',a,b,r[0],r[1],'p=%.4f'%r[3])
for a,b in [('R','P'),('C','F'),('F','P'),('C','R'),('C','P'),('R','H')]:
    r=perm(s4,'reached_strict',a,b,rng); print('E4',a,b,r[0],r[1],'p=%.4f'%r[3])
