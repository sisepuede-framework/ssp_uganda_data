import json, re, pandas as pd, numpy as np, sys
sys.path.insert(0,'/Users/alexa/Documents/centro_decisiones/chatbot/ssp_uganda_data/metamodel/chatbot_deploy')
from backend.rdm.runs import active_run_name, get_run
from backend.rdm.tools.network import model_network
S='/private/tmp/claude-501/-Users-alexa-Documents-centro-decisiones-chatbot-ssp-uganda-data/618073b8-d02a-423b-ba35-6800d39cc3b9/scratchpad/review'
B='/Users/alexa/Documents/centro_decisiones/chatbot/ssp_uganda_data/metamodel/chatbot_deploy'
REF=json.load(open(f'{B}/backend/rdm/eval/e3_reference.json'))
run=get_run(active_run_name())
allr={}
for q,r in REF.items():
    a=model_network(run, r['node'], 2050, 'v1')
    c=next(x for x in a['fields'] if x['field']==r['field'])['values']['all']
    allr[q]=[c['median']]+c['p10_p90']
m=pd.read_pickle(f'{S}/convs4.pkl')
def keyok(q,v):
    if q=='HD1': return 3<=v<=5 or 59<=v<=60.5
    k=REF[q]; return k['key_p10']<=v<=k['key_p90']
def near(v,pool): return any(abs(v-p)<=0.035*abs(p) for p in pool)
# valid only through all-runs numbers: every in-key value is (rounded) an all-runs median/p10/p90
m['inkey']=[[v for v in vs if keyok(q,v)] for q,vs in zip(m.q,m.vals)]
m['only_allruns']=[bool(ik) and all(near(v,allr[q]) for v in ik) for q,ik in zip(m.q,m.inkey)]
m['valid_corr']=m.valid & ~m.only_allruns
# add clear false negatives (answer in Mt inside the key, read by hand)
FN={('e4_S','N2_v3_r9.json'),('e4_S','S50_v6_r6.json'),('e4_S','R6_v6_r7.json'),('e4_S','N5_v6_r1.json'),('e4_S','N5_v6_r3.json')}
m['valid_corr2']=m.valid_corr | m.apply(lambda r:(r.folder,r.file) in FN,axis=1)
print(m.groupby(['folder','arm'])[['valid','only_allruns','valid_corr','valid_corr2','valid_onscreen']].sum())
m.to_pickle(f'{S}/convs5.pkl')
