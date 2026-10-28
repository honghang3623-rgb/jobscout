"""Populate an empty local database with explicitly fictional jobs; no network calls."""
import json
import os
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));os.chdir(ROOT)
import platform_core as core

def main():
    core.initialize()
    with core.connect() as con:
        if con.execute('SELECT 1 FROM jobs LIMIT 1').fetchone():
            print('Database already contains records; no demo data inserted.');return
    prefs=core.preferences();prefs.update(demo=True,daily_enabled=False,intern_region='any_us',fulltime_region='any_us')
    core.save_preferences(prefs)
    rows=json.loads((ROOT/'examples/jobs.json').read_text())
    for row in rows:
        result=core.add_job(row)
        with core.connect() as con:
            con.execute('UPDATE jobs SET category=?,sector=? WHERE id=?',(row.get('category',''),row.get('sector',''),result['id']))
    with core.connect() as con:core.rescore_all(con)
    print(f'Loaded {len(rows)} fictional jobs. No live employers, applications or personal records were imported.')

if __name__=='__main__':main()
