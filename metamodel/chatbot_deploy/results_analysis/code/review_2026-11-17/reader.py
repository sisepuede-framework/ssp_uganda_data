import pandas as pd, json
S='/private/tmp/claude-501/-Users-alexa-Documents-centro-decisiones-chatbot-ssp-uganda-data/618073b8-d02a-423b-ba35-6800d39cc3b9/scratchpad/review'
B='/Users/alexa/Documents/centro_decisiones/chatbot/ssp_uganda_data/metamodel/chatbot_deploy/backend/rdm/eval/pilot_runs'
m=pd.read_pickle(f'{S}/convs6.pkl'); m['genuine']=m.valid & m.key_on_screen
rows=[]
for folder in ['e3_S','e3_SX','e3_O','e4_S','e4_O']:
    fm=pd.read_csv(f'{B}/{folder}/failure_modes.csv')
    for _,r in fm.iterrows():
        ms=str(r.get('missing_statements'))
        rows.append(dict(folder=folder,file=r.file,reader_value=None if pd.isna(r.get('22_statement_missing')) else ('gives a value from the model runs between' not in ms)))
d=m.merge(pd.DataFrame(rows),on=['folder','file'])
d=d[d.reader_value.notna()]
d['reader_value']=d.reader_value.astype(bool)
print(pd.crosstab([d.folder],[d.valid,d.reader_value]))
print('agreement text rule vs reader:', (d.valid==d.reader_value).mean().round(3), 'n',len(d))
print('agreement genuine vs reader:', (d.genuine==d.reader_value).mean().round(3))
print(d.groupby(['folder','arm'])[['valid','genuine','reader_value']].sum())
