import pandas as pd, json, re, sys
S='/private/tmp/claude-501/-Users-alexa-Documents-centro-decisiones-chatbot-ssp-uganda-data/618073b8-d02a-423b-ba35-6800d39cc3b9/scratchpad/review'
B='/Users/alexa/Documents/centro_decisiones/chatbot/ssp_uganda_data/metamodel/chatbot_deploy'
REF=json.load(open(f'{B}/backend/rdm/eval/e3_reference.json'))
m=pd.read_pickle(f'{S}/convs6.pkl')
folder,arms=sys.argv[1],sys.argv[2].split(',')
UNIT_RX = {"tonne": r"(?P<n>\d[\d,]*(?:\.\d+)?)\s*(?P<s>million|thousand|kt|Mt)?\s*(?:tonnes|tons|t)\b",
    "PJ": r"(?P<n>\d[\d,]*(?:\.\d+)?)\s*(?P<s>)PJ\b","ha": r"(?P<n>\d[\d,]*(?:\.\d+)?)\s*(?P<s>million|thousand)?\s*(?:hectares|ha)\b","vehicle-km": r"(?P<n>\d[\d,]*(?:\.\d+)?)\s*(?P<s>billion|million)\s*(?:vehicle[- ]?)?(?:km|kilomet)"}
SC={"million": 1e6, "thousand": 1e3, "kt": 1e3, "Mt": 1e6, "billion": 1e9, "": 1}
x=m[(m.folder==folder)&(m.arm.isin(arms))&(m.valid)]
for _,r in x.iterrows():
    k=REF[r.q]
    print('=====',r.folder,r.file,'onscreen',r.key_on_screen,'key %.4g–%.4g'%(k['key_p10'],k['key_p90']))
    for mm in re.finditer(UNIT_RX[k['unit']],r.ans,re.I):
        v=float(mm.group('n').replace(',',''))*SC[mm.group('s') or '']
        if (k['key_p10']<=v<=k['key_p90']) if r.q!='HD1' else (3<=v<=5 or 59<=v<=60.5):
            print('   %.4g >>'%v, r.ans[max(0,mm.start()-170):mm.end()+30].replace('\n',' '))
