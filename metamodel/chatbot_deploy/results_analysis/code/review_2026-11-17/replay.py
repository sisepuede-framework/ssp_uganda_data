import json, glob, sys
sys.path.insert(0,'/Users/alexa/Documents/centro_decisiones/chatbot/ssp_uganda_data/metamodel/chatbot_deploy')
from backend.rdm.runs import active_run_name, get_run
from backend.rdm.tools import information
from backend.rdm.tools.common import ToolError
B='/Users/alexa/Documents/centro_decisiones/chatbot/ssp_uganda_data/metamodel/chatbot_deploy/backend/rdm/eval/pilot_runs'
run=get_run(active_run_name())
def norm(x):
    if isinstance(x,dict):
        return {k:norm(v) for k,v in x.items() if k!='lever_effects'}
    if isinstance(x,list): return [norm(v) for v in x]
    return x
tot=same=same_noeff=0; diffs=[]
for folder in ['e3_S','e3_SX','e3_O','e3_G']:
    for f in glob.glob(f'{B}/{folder}/*.json'):
        r=json.load(open(f))
        for c in r['tool_log']:
            if c['tool']!='model_network': continue
            a=c.get('args') or {}
            tot+=1
            try:
                out=information.model_network(run,a['node'],a['year'],r['arm'],a.get('lever'),a.get('uncertainty'),a.get('third'))
            except ToolError as e:
                out={'error':str(e)}
            except KeyError as e:
                out={'error':f"Missing argument {e}"}
            got=json.loads(json.dumps(out,ensure_ascii=False,default=str)); exp=c['reply']
            if got==exp: same+=1
            elif norm(got)==norm(exp): same_noeff+=1
            else: diffs.append((folder,f.split('/')[-1],a))
print('calls',tot,'identical',same,'identical except lever_effects order',same_noeff,'different',len(diffs))
print(diffs[:5])
