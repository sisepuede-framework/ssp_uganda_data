import numpy as np
from scipy.special import expit, logit
rng=np.random.default_rng(7)
def sim(pa,n_q,reps,sd_q=1.2,sd_slope=0.6,N_SIM=1000,N_PERM=500):
    la=logit(pa); hits=0
    for _ in range(N_SIM):
        base=la+rng.normal(0,sd_q,n_q); slope=rng.normal(0,sd_slope,n_q)   # mean effect 0, heterogeneous
        ya=rng.random((n_q,reps))<expit(base)[:,None]; yb=rng.random((n_q,reps))<expit(base+slope)[:,None]
        y=np.concatenate([ya,yb],axis=1).astype(float)
        obs=y[:,reps:].mean()-y[:,:reps].mean()
        idx=np.argsort(rng.random((N_PERM,n_q,2*reps)),axis=2)
        yp=np.take_along_axis(np.broadcast_to(y,(N_PERM,n_q,2*reps)),idx,axis=2)
        null=yp[:,:,reps:].mean(axis=(1,2))-yp[:,:,:reps].mean(axis=(1,2))
        p=(np.sum(np.abs(null)>=abs(obs)-1e-12)+1)/(N_PERM+1)
        hits+=p<0.05
    return hits/N_SIM
for pa in (0.15,0.4):
  for reps in (5,10):
    for sds in (0.6,1.2):
      print('base',pa,'reps',reps,'sd_slope',sds,'rejection rate at mean effect 0:',sim(pa,12,reps,sd_slope=sds))
