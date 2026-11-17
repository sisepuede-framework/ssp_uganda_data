import pandas as pd, json, re
S='/private/tmp/claude-501/-Users-alexa-Documents-centro-decisiones-chatbot-ssp-uganda-data/618073b8-d02a-423b-ba35-6800d39cc3b9/scratchpad/review'
B='/Users/alexa/Documents/centro_decisiones/chatbot/ssp_uganda_data/metamodel/chatbot_deploy'
REF=json.load(open(f'{B}/backend/rdm/eval/e3_reference.json'))
m=pd.read_pickle(f'{S}/convs5.pkl')
x=m[m.only_allruns & m.key_on_screen]
print(len(x), x.groupby(['folder','arm']).size().to_dict())
for _,r in x.iterrows():
    k=REF[r.q]
    # find the sentence that mentions top third / high third / top of range
    s=re.search(r"[^.\n]*(?:top third|high third|highest third|upper third|top of (?:the|its) range|⅔)[^.\n]*",r.ans,re.I)
    print('==',r.folder,r.file,'key %.4g–%.4g'%(k['key_p10'],k['key_p90']),'inkey',[f'{v:.4g}' for v in r.inkey],'|',(s.group(0)[:260] if s else '-'))
