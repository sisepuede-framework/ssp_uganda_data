import pandas as pd
S='/private/tmp/claude-501/-Users-alexa-Documents-centro-decisiones-chatbot-ssp-uganda-data/618073b8-d02a-423b-ba35-6800d39cc3b9/scratchpad/review'
m=pd.read_pickle(f'{S}/convs6.pkl')
st=pd.read_pickle(f'{S}/stops.pkl')[['folder','file','stop']]
x=m[~m.reached & m.folder.isin(['e3_S','e3_SX','e4_S'])].merge(st,on=['folder','file'])
x['multi']=x.nanswers>1
print(pd.crosstab([x.folder,x.arm],[x.multi,x.stop_y]))
