import pandas as pd
S='/private/tmp/claude-501/-Users-alexa-Documents-centro-decisiones-chatbot-ssp-uganda-data/618073b8-d02a-423b-ba35-6800d39cc3b9/scratchpad/review'
m=pd.read_pickle(f'{S}/convs3.pkl')
m['cell']=m.reached.map({True:'R',False:'-'})+m.key_on_screen.map({True:'K',False:'-'})+m.valid.map({True:'V',False:'-'})
print(pd.crosstab([m.folder,m.arm],m.cell))
print(pd.crosstab([m.folder,m.q],m.arm,values=m.valid,aggfunc='sum'))
