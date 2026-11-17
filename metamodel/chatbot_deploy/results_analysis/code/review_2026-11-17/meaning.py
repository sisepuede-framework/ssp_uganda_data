import json, glob, collections, re
B='/Users/alexa/Documents/centro_decisiones/chatbot/ssp_uganda_data/metamodel/chatbot_deploy/backend/rdm/eval/pilot_runs'
for folder in ['e4_S','e4_O','e4_G']:
    c=collections.Counter()
    for f in glob.glob(f'{B}/{folder}/*_v6_*.json')+glob.glob(f'{B}/{folder}/*_v7_*.json'):
        r=json.load(open(f)); arm=r['arm']
        calls=[x for x in r['tool_log'] if x['tool']=='model_network']
        asked=[i for i,x in enumerate(calls) if (x.get('args') or {}).get('meaning') and x['status']=='ok']
        walk=[i for i,x in enumerate(calls) if not (x.get('args') or {}).get('meaning') and x['status']=='ok' and (x.get('reply') or {}).get('kind') not in ('lever',)]
        anyexp_before=None
        c[(arm,'n')]+=1
        c[(arm,'asked')]+=bool(asked)
        c[(arm,'asked_before_walk')]+= bool(asked) and (not walk or asked[0]<walk[0])
        c[(arm,'walked_first')]+= bool(walk) and (not asked or walk[0]<asked[0])
        # first model_network call is meaning?
        c[(arm,'first_call_meaning')]+= bool(calls) and bool((calls[0].get('args') or {}).get('meaning'))
        c[(arm,'meaning_errors')]+=sum(1 for x in calls if (x.get('args') or {}).get('meaning') and x['status']!='ok')
        c[(arm,'lf_missing_err')]+=sum(1 for x in calls if x.get('error_code')=='MISSING_LOOKING_FOR')
    print(folder, dict(sorted(c.items())))
# looking_for refusals in F
for folder in ['e4_S','e4_O','e4_G']:
    n=0;tot=0
    for f in glob.glob(f'{B}/{folder}/*_v8_*.json')+glob.glob(f'{B}/{folder}/*_v6_*.json'):
        r=json.load(open(f)); tot+=1
        n+=any(x.get('error_code')=='MISSING_LOOKING_FOR' for x in r['tool_log'])
    print(folder,'conversations with a MISSING_LOOKING_FOR refusal',n,'of',tot)
