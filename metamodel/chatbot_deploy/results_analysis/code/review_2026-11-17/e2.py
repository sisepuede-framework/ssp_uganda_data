import json, glob, collections, re, sys, pandas as pd
sys.path.insert(0,'/Users/alexa/Documents/centro_decisiones/chatbot/ssp_uganda_data/metamodel/chatbot_deploy')
B='/Users/alexa/Documents/centro_decisiones/chatbot/ssp_uganda_data/metamodel/chatbot_deploy/backend/rdm/eval'
for d in ['bank_v4','retrieval_v4','bank_v4_drift']:
    fs=glob.glob(f'{B}/pilot_runs/{d}/*.json'); st=[];c=collections.Counter();dirty=collections.Counter()
    for f in fs:
        r=json.load(open(f)); st.append(r['started']); c[r['versions']['git_commit'][:7]]+=1; dirty[r['versions']['rdm_code_uncommitted_changes']]+=1
    print(d,len(fs),min(st),max(st),dict(c),dict(dirty))
REF=json.load(open(f'{B}/retrieval_v4_reference.json'))
fm=pd.read_csv(f'{B}/pilot_runs/retrieval_v4/failure_modes.csv')
fm=fm[~fm.file.str.startswith('_infra')]
fm['reached']=fm['25_required_node_not_visited'].astype(str)=='False'
print(fm.groupby('arm').reached.sum().to_dict())
x=pd.read_excel('/Users/alexa/Documents/centro_decisiones/chatbot/ssp_uganda_data/metamodel/chatbot_deploy/results_analysis/run_v4_analysis.xlsx',sheet_name='Held-out (B)')
print(x.groupby('arm')[['PROCESS: reached the node','ANSWER: value inside the key']].sum())
print(x[x['ANSWER: value inside the key']][['question','arm','rep','values found','answer key']].to_string())
for k,v in REF.items(): print(k, v['lever'], v['node'], v['key_p10'], v['key_p90'])
