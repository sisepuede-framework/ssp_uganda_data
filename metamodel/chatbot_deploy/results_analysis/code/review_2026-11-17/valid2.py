import json, re, pandas as pd
S='/private/tmp/claude-501/-Users-alexa-Documents-centro-decisiones-chatbot-ssp-uganda-data/618073b8-d02a-423b-ba35-6800d39cc3b9/scratchpad/review'
B='/Users/alexa/Documents/centro_decisiones/chatbot/ssp_uganda_data/metamodel/chatbot_deploy'
REF=json.load(open(f'{B}/backend/rdm/eval/e3_reference.json'))
m=pd.read_pickle(f'{S}/convs2.pkl')
NUM=r"\d[\d,]*(?:\.\d+)?"
SCW={'million':1e6,'thousand':1e3,'billion':1e9,'':1}
UNITS={'tonne':{'tonnes':1,'tonne':1,'tons':1,'t':1,'kt':1e3,'mt':1e6},
       'ha':{'hectares':1,'ha':1,'mha':1e6,'kha':1e3},
       'PJ':{'pj':1},'vehicle-km':None}
def fixed(text,unit):
    if unit=='vehicle-km':
        rx=rf"(?P<a>{NUM})\s*(?P<s>billion|million)\s*(?:vehicle[- ]?)?(?:km|kilomet)"
        return [float(x.group('a').replace(',',''))*SCW[x.group('s').lower()] for x in re.finditer(rx,text,re.I)]
    us='|'.join(sorted(UNITS[unit],key=len,reverse=True))
    rx=rf"(?P<a>{NUM})(?:\s*(?:–|-|to|and)\s*(?P<b>{NUM}))?\s*(?P<s>million|thousand|billion)?\s*(?P<u>{us})\b(?!\s*(?:of\s+)?CO)"
    out=[]
    for x in re.finditer(rx,text,re.I):
        mult=SCW[(x.group('s') or '').lower()]*UNITS[unit][x.group('u').lower()]
        for g in ('a','b'):
            if x.group(g):
                out.append(float(x.group(g).replace(',',''))*mult)
    return out
def keyok(q,v):
    if q=='HD1': return 3<=v<=5 or 59<=v<=60.5
    k=REF[q]; return k['key_p10']<=v<=k['key_p90']
m['fvals']=[fixed(a,REF[q]['unit']) for a,q in zip(m.ans,m.q)]
m['valid_fixed']=[any(keyok(q,v) for v in vs) for q,vs in zip(m.q,m.fvals)]
print(m.groupby(['folder','arm'])[['valid','valid_fixed','reached']].sum())
dis=m[m.valid!=m.valid_fixed]
print(len(dis)); print(dis.groupby(['folder','arm','valid','valid_fixed']).size())
m.to_pickle(f'{S}/convs3.pkl')
for _,r in dis.iterrows():
    k=REF[r.q]
    print('=====',r.folder,r.file,'reached',r.reached,'key %.4g-%.4g'%(k['key_p10'],k['key_p90']),'orig',[f'{v:.3g}' for v in r.vals[:5]],'fixed',[f'{v:.3g}' for v in r.fvals[:8]])
    # print snippet with in-key values
    us='|'.join(sorted(UNITS.get(k['unit']) or ['km'],key=len,reverse=True))
    for x in re.finditer(rf"(?P<a>{NUM})(?:\s*(?:–|-|to|and)\s*(?P<b>{NUM}))?\s*(?:million|thousand|billion)?\s*(?:{us})\b(?!\s*(?:of\s+)?CO)",r.ans,re.I):
        print('   >>',r.ans[max(0,x.start()-120):x.end()+60].replace('\n',' '))
