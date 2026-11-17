import pandas as pd, json, re
S='/private/tmp/claude-501/-Users-alexa-Documents-centro-decisiones-chatbot-ssp-uganda-data/618073b8-d02a-423b-ba35-6800d39cc3b9/scratchpad/review'
B='/Users/alexa/Documents/centro_decisiones/chatbot/ssp_uganda_data/metamodel/chatbot_deploy'
REF=json.load(open(f'{B}/backend/rdm/eval/e3_reference.json'))
m=pd.read_pickle(f'{S}/convs6.pkl')
x=m[(m.folder=='e4_S')&(m.reached)&(~m.valid)]
print(x.groupby('arm').size())
for _,r in x.iterrows():
    k=REF[r.q]
    print('==',r.arm,r.file,'onscreen',r.key_on_screen,'key %.4g–%.4g'%(k['key_p10'],k['key_p90']),'|',r.final[:260].replace('\n',' '))
