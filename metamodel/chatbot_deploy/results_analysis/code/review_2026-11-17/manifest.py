import pandas as pd, hashlib, os
B='/Users/alexa/Documents/centro_decisiones/chatbot/ssp_uganda_data/metamodel/chatbot_deploy/backend/rdm/eval'
for d in ['e3_S','e3_SX','e3_O','e3_G','e4_S','e4_O','e4_G']:
    m=pd.read_csv(f'{B}/run_manifests/{d}.csv')
    fcol=[c for c in m.columns if 'file' in c.lower()][0]; hcol=[c for c in m.columns if 'sha' in c.lower()][0]
    bad=0; missing=0
    for _,r in m.iterrows():
        p=f'{B}/pilot_runs/{d}/{r[fcol]}'
        if not os.path.exists(p): missing+=1; continue
        h=hashlib.sha256(open(p,'rb').read()).hexdigest()
        if not h.startswith(str(r[hcol])[:16]) and h!=r[hcol]: bad+=1
    ondisk=len([f for f in os.listdir(f'{B}/pilot_runs/{d}') if f.endswith('.json') or f.endswith('.csv')])
    print(d,'manifest rows',len(m),'missing',missing,'hash mismatch',bad,'files on disk (json+csv)',ondisk, 'cols',list(m.columns)[:6])
