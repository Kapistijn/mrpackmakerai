from __future__ import annotations
def conflict_options(conflicts):
 options=[]
 for item in conflicts:
  left,right=item.get('left','left'),item.get('right','right');options.append({'problem':f'{left} + {right}','solutions':[{'label':f'Keep {left}, remove {right}','recommended':True},{'label':f'Keep {right}, remove {left}','recommended':False},{'label':'Search replacement','recommended':False}]})
 return options
