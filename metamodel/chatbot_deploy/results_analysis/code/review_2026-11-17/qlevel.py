import pandas as pd, numpy as np, itertools
S='/private/tmp/claude-501/-Users-alexa-Documents-centro-decisiones-chatbot-ssp-uganda-data/618073b8-d02a-423b-ba35-6800d39cc3b9/scratchpad/review'
m=pd.read_pickle(f'{S}/convs6.pkl')
def signflip(diffs):
    diffs=np.array(diffs); obs=abs(diffs.mean()); n=len(diffs)
    cnt=0; tot=0
    for signs in itertools.product([1,-1],repeat=n):
        tot+=1; cnt+= abs((diffs*np.array(signs)).mean())>=obs-1e-12
    return cnt/tot
def qtest(d,col,a,b):
    g=d[d.arm.isin([a,b])].groupby(['q','arm'])[col].mean().unstack()
    diff=(g[a]-g[b])
    return ' '.join(f'{q}:{v:+.1f}' for q,v in diff.items() if v!=0), (diff>0).sum(),(diff<0).sum(), signflip(diff.values)
s3=m[m.folder=='e3_S']; sx=m[m.folder=='e3_SX'].assign(arm='X'); c3=pd.concat([s3[s3.arm=='P'],sx])
for a,b,d in [('H','P',s3),('L','P',s3),('T','P',s3),('X','P',c3)]:
    for col in ('reached','valid'):
        diffs,pos,neg,p=qtest(d,col,a,b); print('E3',a,'vs',b,col,'questions +',pos,'-',neg,'question-level sign-flip p=%.4f'%p,'|',diffs)
s4=m[m.folder=='e4_S']
for a,b in [('R','P'),('C','F'),('F','P'),('C','R'),('C','P'),('R','H')]:
    diffs,pos,neg,p=qtest(s4,'valid',a,b); print('E4',a,'vs',b,'valid questions +',pos,'-',neg,'p=%.4f'%p,'|',diffs)
o3=m[m.folder=='e3_O']; o4=m[m.folder=='e4_O']
for nm,d in [('E3 O',o3),('E4 O',o4)]:
    for col in ('reached','valid'):
        diffs,pos,neg,p=qtest(d,col,'H','P'); print(nm,'H vs P',col,'+',pos,'-',neg,'p=%.4f'%p,'|',diffs)
