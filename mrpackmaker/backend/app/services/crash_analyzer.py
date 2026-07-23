from __future__ import annotations
import re
def analyze_crash(text:str,mods=None)->dict:
 body=text or ''; lower=body.casefold(); conflicts=[]
 for match in re.finditer(r'([A-Za-z][\w -]{2,40})\s+(?:requires|conflicts with|incompatible with)\s+([A-Za-z][\w -]{2,40})',body,re.I): conflicts.append({'left':match.group(1).strip(),'right':match.group(2).strip(),'cause':'dependency or compatibility conflict'})
 if not conflicts and any(x in lower for x in ('mixin','nosuchmethod','mod resolution','failed to load')): conflicts.append({'left':'runtime','right':'mod set','cause':'loader or dependency resolution failed'})
 return {'status':'conflict' if conflicts else 'unknown','conflicts':conflicts,'solutions':['Update the dependency','Downgrade the parent mod','Replace the conflicting mod'],'source_length':len(body)}
