import pathlib
import sqlite3

SCHEMA = """
CREATE TABLE IF NOT EXISTS jobs(
  id TEXT PRIMARY KEY, company TEXT, ats TEXT, title TEXT, location TEXT, url TEXT,
  description TEXT, posted TEXT, first_seen TEXT, last_seen TEXT,
  status TEXT DEFAULT 'new', flags TEXT DEFAULT '', notes TEXT DEFAULT '');
CREATE TABLE IF NOT EXISTS scores(
  job_id TEXT PRIMARY KEY, score INTEGER, verdict TEXT, detail TEXT, method TEXT, scored_at TEXT);
-- source: 'lca' (DOL 劳工条件申请, count=获批职位数, extra=工资等级 III/IV 的职位数)
--         'uscis' (USCIS Employer Data Hub, count=批准总数, extra=初次批准数)
CREATE TABLE IF NOT EXISTS h1b(
  norm_name TEXT, display_name TEXT, fiscal_year TEXT, source TEXT, count INTEGER, extra INTEGER DEFAULT 0,
  PRIMARY KEY(norm_name, fiscal_year, source));
"""


def connect(path="data/jobscout.db"):
    pathlib.Path(path).parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(path, check_same_thread=False)
    con.row_factory = sqlite3.Row
    con.executescript(SCHEMA)
    columns = {r['name'] for r in con.execute('PRAGMA table_info(jobs)')}
    if 'is_open' not in columns:
        con.execute('ALTER TABLE jobs ADD COLUMN is_open INTEGER DEFAULT 1')
        con.commit()
    if 'market' not in columns:
        con.execute("ALTER TABLE jobs ADD COLUMN market TEXT NOT NULL DEFAULT 'us'")
        con.commit()
    for name in ['deadline','sector','source_id','category']:
        if name not in columns:
            con.execute(f"ALTER TABLE jobs ADD COLUMN {name} TEXT DEFAULT ''")
            con.commit()
    return con
