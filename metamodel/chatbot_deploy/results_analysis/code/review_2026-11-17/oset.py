import pandas as pd
S='/private/tmp/claude-501/-Users-alexa-Documents-centro-decisiones-chatbot-ssp-uganda-data/618073b8-d02a-423b-ba35-6800d39cc3b9/scratchpad/review'
m=pd.read_pickle(f'{S}/convs6.pkl')
x=m[(m.folder=='e3_O')&(~m.reached)]
print(x.groupby(['arm','q']).size())
for _,r in x[x.arm=='P'].iterrows():
    print('==',r.file,'|',r.final[:300].replace('\n',' '))
