import pandas as pd, re, json
S='/private/tmp/claude-501/-Users-alexa-Documents-centro-decisiones-chatbot-ssp-uganda-data/618073b8-d02a-423b-ba35-6800d39cc3b9/scratchpad/review'
B='/Users/alexa/Documents/centro_decisiones/chatbot/ssp_uganda_data/metamodel/chatbot_deploy'
REF=json.load(open(f'{B}/backend/rdm/eval/e3_reference.json'))
m=pd.read_pickle(f'{S}/convs6.pkl')
RX=r"(?P<n>\d[\d,]*(?:\.\d+)?)\s*(?P<s>million|thousand|kt|Mt)?\s*(?:tonnes|tons|t)\b"
SC={"million": 1e6, "thousand": 1e3, "kt": 1e3, "Mt": 1e6, "": 1}
n=0
for _,r in m[m.valid].iterrows():
    k=REF[r.q]
    if k['unit']!='tonne': continue
    ctx=[]
    for x in re.finditer(RX,r.ans,re.I):
        v=float(x.group('n').replace(',',''))*SC[x.group('s') or '']
        if k['key_p10']<=v<=k['key_p90']:
            ctx.append(r.ans[x.end():x.end()+25])
    if ctx and all(re.match(r"\s*(?:of\s+)?(?:CO|carbon|CH)",c,re.I) for c in ctx):
        n+=1; print(r.folder,r.file,ctx)
print('valid only via emissions-like contexts:',n)
