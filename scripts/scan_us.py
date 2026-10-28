"""Run the ordinary US scan with durable history, independently of the UI."""
import json,os,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT));os.chdir(ROOT)
import platform_core as core
core.initialize()
with core.connect() as con:ident=con.execute('INSERT INTO runs(kind,state,started,detail) VALUES(?,?,?,?)',('scan','running',core.now(),'{}')).lastrowid
last=[-1]
def progress(message,done=0,total=0):
 if done//10!=last[0] or done==total:print(f'{done}/{total} {message}',flush=True);last[0]=done//10
core.TASK.progress=progress
try:
 result=core.run_scan();status='partial' if result.get('errors') else 'completed'
except Exception as e:result={'error':str(e)};status='failed'
with core.connect() as con:con.execute('UPDATE runs SET state=?,finished=?,detail=? WHERE id=?',(status,core.now(),json.dumps(result,ensure_ascii=False),ident))
print(json.dumps({k:v for k,v in result.items() if k!='company_results'},ensure_ascii=False),flush=True)
if status=='failed':raise SystemExit(1)
