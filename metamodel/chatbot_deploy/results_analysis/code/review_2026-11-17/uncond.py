import json
from backend.rdm.runs import active_run_name, get_run
from backend.rdm.tools.network import model_network
REF=json.load(open('backend/rdm/eval/e3_reference.json'))
run=get_run(active_run_name())
for q,r in REF.items():
    a=model_network(run, r['node'], 2050, 'v1')
    f=next(x for x in a['fields'] if x['field']==r['field'])
    v=f['values']
    allv=v.get('any') or v
    b=model_network(run, r['node'], 2050, 'v1', lever=r['lever'])
    fb=next(x for x in b['fields'] if x['field']==r['field'])['values']
    inkey=lambda x: r['key_p10']<=x<=r['key_p90']
    med=list(allv.values())[0]['median'] if isinstance(allv,dict) and 'median' not in allv else allv.get('median')
    print(q, r['set'], 'key %.4g–%.4g'%(r['key_p10'],r['key_p90']), '| all runs:', json.dumps(allv)[:90], '| low', fb['low']['median'], fb['low']['p10_p90'], 'mid', fb['mid']['median'], '| all-run median in key:', inkey(med) if med else None, '| low-third median in key:', inkey(fb['low']['median']), '| mid in key:', inkey(fb['mid']['median']))
