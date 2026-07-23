from __future__ import annotations
from app.services.crash_analyzer import analyze_crash
def repair_report(crash_text:str,mods=None):
 report=analyze_crash(crash_text,mods);report['recommended']='preserve both mods first, then resolve versions, then search an alternative, remove only as last resort';return report
