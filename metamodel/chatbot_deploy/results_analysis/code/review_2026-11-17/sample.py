import pandas as pd, json
S='/private/tmp/claude-501/-Users-alexa-Documents-centro-decisiones-chatbot-ssp-uganda-data/618073b8-d02a-423b-ba35-6800d39cc3b9/scratchpad/review'
B='/Users/alexa/Documents/centro_decisiones/chatbot/ssp_uganda_data/metamodel/chatbot_deploy'
REF=json.load(open(f'{B}/backend/rdm/eval/e3_reference.json'))
m=pd.read_pickle(f'{S}/convs6.pkl')
x3=pd.read_excel(f'{B}/results_analysis/e3_analysis.xlsx',sheet_name='Conversations (hand check)')
x4=pd.read_excel(f'{B}/results_analysis/e4_analysis.xlsx',sheet_name='Conversations (hand check)')
x=pd.concat([x3,x4]); x['file']=x.log_file.str.split('/').str[1]; x['folder']=x.log_file.str.split('/').str[0]
m=m.merge(x[['folder','file','stop']],on=['folder','file'],suffixes=('','_wb'))
pool=m[m.folder.isin(['e3_S','e3_SX','e4_S'])]
smp=pool.groupby('arm',group_keys=False).apply(lambda g:g.sample(3,random_state=20261117))
for _,r in smp.iterrows():
    k=REF[r.q]
    print('#####',r.folder,r.file,'| reached',r.reached,'valid',r.valid,'stop',repr(r.stop_wb),'| key %.4g–%.4g %s'%(k['key_p10'],k['key_p90'],k['unit']),'| vals',[f'{v:.3g}' for v in r.vals[:6]])
    print(r.final[:900].replace('\n',' '))
