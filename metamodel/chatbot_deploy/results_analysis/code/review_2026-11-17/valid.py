import json, re, pandas as pd, numpy as np
S='/private/tmp/claude-501/-Users-alexa-Documents-centro-decisiones-chatbot-ssp-uganda-data/618073b8-d02a-423b-ba35-6800d39cc3b9/scratchpad/review'
B='/Users/alexa/Documents/centro_decisiones/chatbot/ssp_uganda_data/metamodel/chatbot_deploy'
REF=json.load(open(f'{B}/backend/rdm/eval/e3_reference.json'))
d=pd.read_pickle(f'{S}/convs.pkl')
UNIT_RX = {
    "tonne": r"(?P<n>\d[\d,]*(?:\.\d+)?)\s*(?P<s>million|thousand|kt|Mt)?\s*(?:tonnes|tons|t)\b",
    "PJ": r"(?P<n>\d[\d,]*(?:\.\d+)?)\s*(?P<s>)PJ\b",
    "ha": r"(?P<n>\d[\d,]*(?:\.\d+)?)\s*(?P<s>million|thousand)?\s*(?:hectares|ha)\b",
    "vehicle-km": r"(?P<n>\d[\d,]*(?:\.\d+)?)\s*(?P<s>billion|million)\s*(?:vehicle[- ]?)?(?:km|kilomet)",
}
SCALE = {"million": 1e6, "thousand": 1e3, "kt": 1e3, "Mt": 1e6, "billion": 1e9, "": 1}
def values(text, unit):
    return [float(m.group("n").replace(",", "")) * SCALE[m.group("s") or ""] for m in re.finditer(UNIT_RX[unit], text, re.I)]
def keyok(q,v):
    if q=='HD1': return 3<=v<=5 or 59<=v<=60.5
    k=REF[q]; return k['key_p10']<=v<=k['key_p90']
d['vals']=[values(a,REF[q]['unit']) for a,q in zip(d.ans,d.q)]
d['valid']=[any(keyok(q,v) for v in vs) for q,vs in zip(d.q,d.vals)]
# broader extractor: Mt, kt, Mha, million/ thousand/ billion with 'of' etc, both ends of ranges
SC={'million':1e6,'thousand':1e3,'billion':1e9,'kt':1e3,'mt':1e6,'k':1e3,'m':1e6,'mha':1e6,'kha':1e3,'':1}
def broad(text, unit):
    out=[]
    if unit=='tonne':
        rx=r"(?P<a>\d[\d,]*(?:\.\d+)?)(?:\s*(?:–|-|to|and)\s*(?P<b>\d[\d,]*(?:\.\d+)?))?\s*(?P<s>million|thousand|kt|Mt|k|m)?\s*(?:metric\s+)?(?:tonnes|tons|t\b|kt\b|Mt\b)"
        for m in re.finditer(rx,text,re.I):
            s=(m.group('s') or '').lower()
            tail=text[m.end()-3:m.end()+6]
            mult=SC.get(s,1)
            # unit token itself may be kt/Mt
            ut=re.search(r"(tonnes|tons|t\b|kt\b|Mt\b)",text[m.start():m.end()+1],re.I)
            if ut and ut.group(1).lower() in ('kt','mt') and not s: mult=SC[ut.group(1).lower()]
            # exclude CO2e
            after=text[m.end():m.end()+12]
            if re.match(r"\s*(?:of\s+)?CO", after, re.I) or re.match(r"\s*CO",after): continue
            for g in ('a','b'):
                if m.group(g): out.append(float(m.group(g).replace(',',''))*mult)
    elif unit=='PJ':
        for m in re.finditer(r"(?P<a>\d[\d,]*(?:\.\d+)?)(?:\s*(?:–|-|to|and)\s*(?P<b>\d[\d,]*(?:\.\d+)?))?\s*PJ\b",text):
            for g in ('a','b'):
                if m.group(g): out.append(float(m.group(g).replace(',','')))
    elif unit=='ha':
        for m in re.finditer(r"(?P<a>\d[\d,]*(?:\.\d+)?)(?:\s*(?:–|-|to|and)\s*(?P<b>\d[\d,]*(?:\.\d+)?))?\s*(?P<s>million|thousand|M|k)?\s*(?:hectares|ha\b|Mha\b)",text,re.I):
            s=(m.group('s') or '').lower(); mult={'million':1e6,'thousand':1e3,'m':1e6,'k':1e3}.get(s,1)
            if 'mha' in text[m.start():m.end()].lower(): mult=1e6
            for g in ('a','b'):
                if m.group(g): out.append(float(m.group(g).replace(',',''))*mult)
    else:
        out=values(text,unit)
    return out
d['bvals']=[broad(a,REF[q]['unit']) for a,q in zip(d.ans,d.q)]
d['valid_broad']=[any(keyok(q,v) for v in vs) for q,vs in zip(d.q,d.bvals)]
# compare with xlsx
x3=pd.read_excel(f'{B}/results_analysis/e3_analysis.xlsx',sheet_name='Conversations (hand check)')
x4=pd.read_excel(f'{B}/results_analysis/e4_analysis.xlsx',sheet_name='Conversations (hand check)')
x=pd.concat([x3,x4]); x['file']=x.log_file.str.split('/').str[1]; x['folder']=x.log_file.str.split('/').str[0]
m=d.merge(x[['folder','file','valid','reached','stop']],on=['folder','file'],suffixes=('','_x'))
print('rows',len(m),'valid mismatch',(m.valid!=m.valid_x).sum(),'reached mismatch',(m.reached!=m.reached_x).sum())
print(m.groupby(['folder','arm'])[['valid','valid_broad','reached','key_on_screen']].sum())
m.to_pickle(f'{S}/convs2.pkl')
