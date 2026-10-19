from __future__ import annotations
def conflict_options(conflicts):
 options=[]
 for item in conflicts or ():
  if not isinstance(item, dict):
   continue
  left=str(item.get('left') or 'left').strip() or 'left'
  right=str(item.get('right') or 'right').strip() or 'right'
  if left.casefold() == right.casefold():
   options.append({'problem':left,'solutions':[{'label':'Review the self-conflicting dependency metadata','recommended':True},{'label':'Search replacement','recommended':False}]})
   continue
  options.append({'problem':f'{left} + {right}','solutions':[{'label':f'Keep {left}, remove {right}','recommended':True},{'label':f'Keep {right}, remove {left}','recommended':False},{'label':'Search replacement','recommended':False}]})
 return options
