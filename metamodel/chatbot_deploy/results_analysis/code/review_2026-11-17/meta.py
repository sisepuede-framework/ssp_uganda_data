import json, glob, os, collections
B='/Users/alexa/Documents/centro_decisiones/chatbot/ssp_uganda_data/metamodel/chatbot_deploy/backend/rdm/eval/pilot_runs'
for d in ['e3_S','e3_SX','e3_O','e3_G','e4_S','e4_O','e4_G','smoke_e3_2026_11_17','smoke_e4_2026_11_17']:
    fs=sorted(glob.glob(f'{B}/{d}/*.json'))
    starts=[];commits=collections.Counter();dirty=collections.Counter();tsha=collections.Counter();psha=collections.Counter();models=collections.Counter();eff=collections.Counter();steplim=0;stops=collections.Counter()
    arms=collections.Counter(); qs=set(); qset=collections.Counter()
    tables=collections.Counter(); sur=collections.Counter()
    for f in fs:
        r=json.load(open(f))
        starts.append(r['started']); v=r['versions']
        commits[v['git_commit'][:7] if v['git_commit'] else None]+=1
        dirty[v['rdm_code_uncommitted_changes']]+=1
        tsha[(r['arm'],v['tools_sha'])]+=1; psha[v['system_prompt_sha']]+=1
        models[r['model']]+=1; eff[r['effort']]+=1
        steplim+=bool(r.get('hit_step_limit')); stops[r.get('final_stop_reason')]+=1
        arms[r['arm']]+=1; qs.add(r['question_id']); qset[r.get('question_set')]+=1
        tables[json.dumps(v['tables_sha'],sort_keys=True)[:60]]+=1; sur[v['surrogate_sha']]+=1
    print('==',d,len(fs),min(starts) if starts else None,max(starts) if starts else None)
    print(' commits',dict(commits),'dirty',dict(dirty))
    print(' tools',dict(tsha)); print(' prompt',dict(psha),'model',dict(models),dict(eff))
    print(' steplimit',steplim,'stops',dict(stops),'arms',dict(arms),'nq',len(qs),'qset',dict(qset))
    print(' tables',len(tables),'surrogate',dict(sur))
