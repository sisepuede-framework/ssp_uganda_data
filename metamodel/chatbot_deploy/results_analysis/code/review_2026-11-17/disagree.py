import pandas as pd, re, json
S='/private/tmp/claude-501/-Users-alexa-Documents-centro-decisiones-chatbot-ssp-uganda-data/618073b8-d02a-423b-ba35-6800d39cc3b9/scratchpad/review'
m=pd.read_pickle(f'{S}/convs2.pkl')
dis=m[m.valid!=m.valid_broad]
print(len(dis)); print(dis.groupby(['folder','arm','q']).size())
B='/Users/alexa/Documents/centro_decisiones/chatbot/ssp_uganda_data/metamodel/chatbot_deploy/backend/rdm/eval'
REF=json.load(open(f'{B}/e3_reference.json'))
for _,r in dis.head(60).iterrows():
    k=REF[r.q]
    print('=====',r.folder,r.file,'reached',r.reached,'key',k['key_p10'],k['key_p90'],'orig',r.vals[:5],'broad',[round(v) for v in r.bvals[:8]])
    # print snippets around matched numbers
    a=r.ans
    for mm in re.finditer(r"\d[\d,.]*\s*(?:–|-|to)?\s*\d*[\d,.]*\s*(?:million|thousand)?\s*(?:Mt|kt|tonnes|t\b|Mha|ha|hectares|PJ)",a):
        print('   ...',a[max(0,mm.start()-80):mm.end()+40].replace('\n',' '))
        break
