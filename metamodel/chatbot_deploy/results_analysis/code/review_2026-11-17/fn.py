import json, re, pandas as pd
S='/private/tmp/claude-501/-Users-alexa-Documents-centro-decisiones-chatbot-ssp-uganda-data/618073b8-d02a-423b-ba35-6800d39cc3b9/scratchpad/review'
B='/Users/alexa/Documents/centro_decisiones/chatbot/ssp_uganda_data/metamodel/chatbot_deploy'
REF=json.load(open(f'{B}/backend/rdm/eval/e3_reference.json'))
m=pd.read_pickle(f'{S}/convs3.pkl')
NUM=r"\d[\d,]*(?:\.\d+)?"
def cand(text,q):
    k=REF[q]; unit=k['unit']; out=[]
    if unit=='tonne': rx=rf"(?<![−+\-\d.,])(?P<a>{NUM})(?:\s*(?:–|-|to)\s*(?P<b>{NUM}))?\s*(?P<u>Mt|kt|million t\b|thousand t\b)(?!\s*(?:of\s+)?CO)(?!\s*(?:\(|−|lower|higher|below|above))"
    elif unit=='ha': rx=rf"(?P<a>{NUM})(?:\s*(?:–|-|to)\s*(?P<b>{NUM}))?\s*(?P<u>Mha|kha)\b"
    else: return out
    for x in re.finditer(rx,text):
        u=x.group('u').lower(); mult=1e6 if u.startswith('m') else 1e3
        pre=text[max(0,x.start()-70):x.start()].lower()
        if 'emission' in pre or 'co₂' in pre or 'co2' in pre: continue
        vals=[float(x.group(g).replace(',',''))*mult for g in ('a','b') if x.group(g)]
        if any(k['key_p10']<=v<=k['key_p90'] for v in vals):
            out.append((vals,text[max(0,x.start()-150):x.end()+80].replace('\n',' ')))
    return out
n=0
for _,r in m[~m.valid].iterrows():
    c=cand(r.ans,r.q)
    if c:
        n+=1
        k=REF[r.q]
        print('=====',r.folder,r.file,'arm',r.arm,'reached',r.reached,'key %.4g-%.4g'%(k['key_p10'],k['key_p90']))
        for v,s in c[:3]: print('   ',v,'>>',s)
print(n)
