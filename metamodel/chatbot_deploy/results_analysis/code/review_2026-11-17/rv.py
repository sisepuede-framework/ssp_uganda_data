import pandas as pd, json, re
S='/private/tmp/claude-501/-Users-alexa-Documents-centro-decisiones-chatbot-ssp-uganda-data/618073b8-d02a-423b-ba35-6800d39cc3b9/scratchpad/review'
B='/Users/alexa/Documents/centro_decisiones/chatbot/ssp_uganda_data/metamodel/chatbot_deploy'
REF=json.load(open(f'{B}/backend/rdm/eval/e3_reference.json'))
m=pd.read_pickle(f'{S}/convs3.pkl')
sel=m[(m.reached)&(~m.key_on_screen)&(m.valid)&(m.folder.str.endswith('S')|m.folder.str.endswith('SX'))]
print(len(sel)); print(sel.groupby(['folder','arm','q']).size())
from importlib import import_module
UNIT_RX = {"tonne": r"(?P<n>\d[\d,]*(?:\.\d+)?)\s*(?P<s>million|thousand|kt|Mt)?\s*(?:tonnes|tons|t)\b",
    "PJ": r"(?P<n>\d[\d,]*(?:\.\d+)?)\s*(?P<s>)PJ\b","ha": r"(?P<n>\d[\d,]*(?:\.\d+)?)\s*(?P<s>million|thousand)?\s*(?:hectares|ha)\b"}
SC={"million": 1e6, "thousand": 1e3, "kt": 1e3, "Mt": 1e6, "billion": 1e9, "": 1}
for _,r in sel.iterrows():
    k=REF[r.q]
    print('=====',r.folder,r.file,'key %.4g–%.4g'%(k['key_p10'],k['key_p90']))
    for x in re.finditer(UNIT_RX[k['unit']],r.ans,re.I):
        v=float(x.group('n').replace(',',''))*SC[x.group('s') or '']
        if k['key_p10']<=v<=k['key_p90']:
            print('   IN KEY %.4g >>'%v, r.ans[max(0,x.start()-220):x.end()+60].replace('\n',' '))
            break
