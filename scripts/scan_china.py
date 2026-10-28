"""Run the same domestic scan as the app; results persist in its run history."""
import json,os,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));os.chdir(ROOT)
import platform_core as core
core.initialize()
with core.connect() as con:
 run_id=con.execute('INSERT INTO runs(kind,state,started,detail) VALUES(?,?,?,?)',('china_scan','running',core.now(),'{}')).lastrowid
try:
 old=core.TASK.progress
 def progress(message,done=0,total=0):
  print(f'{done}/{total} {message}',flush=True);old(message,done,total)
 core.TASK.progress=progress
 result=core.run_china_scan();status='partial' if result['errors'] else 'completed'
except Exception as e:
 result={'error':str(e)};status='failed'
with core.connect() as con:
 con.execute('UPDATE runs SET state=?,finished=?,detail=? WHERE id=?',(status,core.now(),json.dumps(result,ensure_ascii=False),run_id))
print(json.dumps({k:v for k,v in result.items() if k!='company_results'},ensure_ascii=False),flush=True)
if status=='failed':raise SystemExit(1)
