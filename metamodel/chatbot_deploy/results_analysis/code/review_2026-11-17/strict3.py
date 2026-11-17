import json, pandas as pd, numpy as np
S='/private/tmp/claude-501/-Users-alexa-Documents-centro-decisiones-chatbot-ssp-uganda-data/618073b8-d02a-423b-ba35-6800d39cc3b9/scratchpad/review'
m=pd.read_pickle(f'{S}/convs5.pkl')
m['fp_allruns']=m.only_allruns & ~m.key_on_screen
FN={('e4_S','N2_v3_r9.json'),('e4_S','S50_v6_r6.json'),('e4_S','R6_v6_r7.json'),('e4_S','N5_v6_r1.json'),('e4_S','N5_v6_r3.json')}
m['fn_mt']=m.apply(lambda r:(r.folder,r.file) in FN,axis=1)
m['valid_c']=(m.valid & ~m.fp_allruns) | m.fn_mt
t=m.groupby(['folder','arm']).agg(n=('valid','size'),valid=('valid','sum'),fp_allruns=('fp_allruns','sum'),fn_mt=('fn_mt','sum'),valid_c=('valid_c','sum'),valid_onscreen=('valid_onscreen','sum'),reached=('reached','sum'),reached_lever2050=('reached_strict','sum'))
print(t)
m.to_pickle(f'{S}/convs6.pkl')
# list fp_allruns files for report
print(m[m.fp_allruns].groupby(['folder','arm']).file.apply(lambda s: ', '.join(sorted(s))).to_string())
