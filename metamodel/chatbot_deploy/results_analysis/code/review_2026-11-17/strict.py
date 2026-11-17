import json, re, pandas as pd, numpy as np, sys
sys.path.insert(0,'/Users/alexa/Documents/centro_decisiones/chatbot/ssp_uganda_data/metamodel/chatbot_deploy')
from backend.rdm.runs import active_run_name, get_run
from backend.rdm.tools.network import model_network
S='/private/tmp/claude-501/-Users-alexa-Documents-centro-decisiones-chatbot-ssp-uganda-data/618073b8-d02a-423b-ba35-6800d39cc3b9/scratchpad/review'
B='/Users/alexa/Documents/centro_decisiones/chatbot/ssp_uganda_data/metamodel/chatbot_deploy'
REF=json.load(open(f'{B}/backend/rdm/eval/e3_reference.json'))
run=get_run(active_run_name())
other={}
for q,r in REF.items():
    a=model_network(run, r['node'], 2050, 'v1')
    f=next(x for x in a['fields'] if x['field']==r['field'])['values']
    b=model_network(run, r['node'], 2050, 'v1', lever=r['lever'])
    fb=next(x for x in b['fields'] if x['field']==r['field'])['values']
    vals=[]
    for cell in list(f.values())+[fb['low'],fb['mid']]:
        vals += [cell['median']]+cell['p10_p90']
    other[q]=vals
m=pd.read_pickle(f'{S}/convs3.pkl')
def keyok(q,v):
    if q=='HD1': return 3<=v<=5 or 59<=v<=60.5
    k=REF[q]; return k['key_p10']<=v<=k['key_p90']
def near(v,pool): return any(abs(v-p)<=0.03*abs(p)+1e-9 for p in pool)
m['valid_noallruns']=[any(keyok(q,v) and not near(v,other[q]) for v in vs) for q,vs in zip(m.q,m.vals)]
m['valid_onscreen']=m.valid & m.key_on_screen
m.to_pickle(f'{S}/convs4.pkl')
print(m.groupby(['folder','arm'])[['valid','valid_noallruns','valid_onscreen','reached','reached_strict']].sum())
