import json, glob, re, os, sys, collections
import pandas as pd
B='/Users/alexa/Documents/centro_decisiones/chatbot/ssp_uganda_data/metamodel/chatbot_deploy/backend/rdm/eval'
REF=json.load(open(f'{B}/e3_reference.json'))
ARM={"v1":"P","v3":"H","v4":"L","v5":"T","v6":"C","v7":"R","v8":"F"}
rows=[]
for folder in ['e3_S','e3_SX','e3_O','e4_S','e4_O']:
    fm=pd.read_csv(f'{B}/pilot_runs/{folder}/failure_modes.csv').set_index('file')
    for f in sorted(glob.glob(f'{B}/pilot_runs/{folder}/*.json')):
        r=json.load(open(f)); q=r['question_id']; ref=REF[q]
        node=ref['node'].lower(); field=ref['field'].lower()
        calls=[c for c in r['tool_log'] if c['tool']=='model_network']
        ok=[c for c in calls if c['status']=='ok']
        def hit(c):
            n=str((c.get('args') or {}).get('node','')).strip().lower()
            return n==node or field in n
        # independent reached: exact node name or field substring, case-insensitive
        reached=any(hit(c) for c in ok)
        # stricter: reached at 2050 with the question's lever as filter
        reached_strict=any(hit(c) and int((c.get('args') or {}).get('year') or 0)==2050 and str((c.get('args') or {}).get('lever'))==str(ref['lever']) for c in ok)
        # Did reply include the high-third values? (i.e., the key was on screen)
        key_on_screen=False
        for c in ok:
            if hit(c):
                rep=c.get('reply') or {}
                for fl in rep.get('fields',[]) or []:
                    if fl.get('field')==ref['field'] and isinstance(fl.get('values'),dict) and 'high' in fl['values']:
                        key_on_screen=True
        errs=sum(c['status']!='ok' for c in calls)
        ans="\n".join(r.get('answers') or [r.get('final_answer') or ''])
        base=os.path.basename(f)
        rows.append(dict(folder=folder,file=base,q=q,arm=ARM[r['arm']],rep=r['rep'],reached=reached,reached_strict=reached_strict,
                         key_on_screen=key_on_screen,fm25=str(fm.loc[base,'25_required_node_not_visited'])=='False',
                         ncalls=len(calls),nerr=errs,nanswers=len(r.get('answers') or []),ans=ans,final=r.get('final_answer') or '',
                         first_meaning=None))
d=pd.DataFrame(rows)
d.to_pickle('/private/tmp/claude-501/-Users-alexa-Documents-centro-decisiones-chatbot-ssp-uganda-data/618073b8-d02a-423b-ba35-6800d39cc3b9/scratchpad/review/convs.pkl')
print('mismatch reached vs fm25:', (d.reached!=d.fm25).sum())
print(d[d.reached!=d.fm25][['folder','file','reached','fm25']])
print(d.groupby(['folder','arm'])[['reached','fm25','reached_strict','key_on_screen']].sum())
print(d.groupby(['folder','arm'])[['ncalls','nerr','nanswers']].mean().round(2))
