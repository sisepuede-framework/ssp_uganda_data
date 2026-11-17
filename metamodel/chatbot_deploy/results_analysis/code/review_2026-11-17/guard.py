import pandas as pd, json, glob, os, sys
sys.path.insert(0,'/Users/alexa/Documents/centro_decisiones/chatbot/ssp_uganda_data/metamodel/chatbot_deploy')
from backend.rdm.eval.questions import BANK_SPECS
B='/Users/alexa/Documents/centro_decisiones/chatbot/ssp_uganda_data/metamodel/chatbot_deploy/backend/rdm/eval/pilot_runs'
ARM={"v1":"P","v3":"H","v4":"L","v5":"T","v6":"C","v7":"R","v8":"F"}
for folder in ['e3_G','e4_G']:
    fm=pd.read_csv(f'{B}/{folder}/failure_modes.csv')
    fm['A']=fm.arm.map(ARM)
    off=[c for c in fm.columns if c.endswith('03_level_off_key')]
    fm['off']=fm['03_level_off_key'].astype(str)=='True'
    print(folder, fm.groupby('A').off.sum().to_dict(), 'n', fm.groupby('A').size().to_dict())
    # composition: no run vs wrong level; run_expected
    rows=[]
    for _,r in fm.iterrows():
        run=json.load(open(f'{B}/{folder}/{r.file}'))
        spec=BANK_SPECS[r.question_id]
        nexp=sum(1 for c in run['tool_log'] if c['tool']=='exploratory_modeling')
        mean=[c for c in run['tool_log'] if c['tool']=='model_network' and (c.get('args') or {}).get('meaning')]
        rows.append(dict(A=r.A,q=r.question_id,off=r.off,ran=nexp>0,run_expected=spec.get('run_expected',True),literal=str(r.get('02_literal_translation'))=='True',level=r.get('level_set'),meaning=len(mean)>0, key=spec.get('key_level')))
    d=pd.DataFrame(rows)
    print(pd.crosstab([d.A],[d.off,d.ran]))
    print('literal translation by arm', d.groupby('A').literal.sum().to_dict())
    print('asked meaning by arm', d.groupby('A').meaning.sum().to_dict())
    if folder=='e4_G':
        print(pd.crosstab(d.q,d.A,values=d.off,aggfunc='sum'))
        print(d[(d.A=='H')&d.off][['q','ran','level','key','literal']].to_string())
