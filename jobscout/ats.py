"""只使用各 ATS 的公开职位接口，不登录、不抓取受限页面。"""
import html
import json
import re
import time
import urllib.request
from datetime import datetime, timezone

from . import filters
from .network import tls_context

UA = "jobscout/0.1 (personal job search)"


def fetch_json(url, timeout=25):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout, context=tls_context()) as r:
        return json.loads(r.read().decode("utf-8"))


def _text(h):
    h = html.unescape(h or "")
    h = re.sub(r"<[^>]+>", " ", h)
    return re.sub(r"\s+", " ", h).strip()


def greenhouse(slug, fetch):
    d = fetch(f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs?content=true")
    for j in d.get("jobs", []):
        yield dict(id=f"gh:{slug}:{j['id']}", title=j.get("title", ""), location=(j.get("location") or {}).get("name", ""),
                   url=j.get("absolute_url", ""), description=_text(j.get("content")), posted=j.get("updated_at", ""))


def lever(slug, fetch):
    for j in fetch(f"https://api.lever.co/v0/postings/{slug}?mode=json"):
        cat = j.get("categories") or {}
        ts = j.get("createdAt")
        posted = datetime.fromtimestamp(ts / 1000, timezone.utc).date().isoformat() if ts else ""
        sections = [j.get('descriptionPlain') or _text(j.get('description'))]
        for section in j.get('lists', []):
            sections.append(_text(section.get('text'))+' '+_text(section.get('content')))
        sections.append(j.get('additionalPlain') or _text(j.get('additional')))
        yield dict(id=f"lever:{slug}:{j['id']}", title=j.get("text", ""), location=cat.get("location", ""),
                   url=j.get("hostedUrl", ""), description='\n'.join(filter(None, sections)), posted=posted)


def ashby(slug, fetch):
    d = fetch(f"https://api.ashbyhq.com/posting-api/job-board/{slug}")
    for j in d.get("jobs", []):
        if j.get("isListed") is False:
            continue
        loc = j.get("location")
        yield dict(id=f"ashby:{slug}:{j['id']}", title=j.get("title", ""), location=loc if isinstance(loc, str) else "",
                   url=j.get("jobUrl", ""), description=j.get("descriptionPlain") or _text(j.get("descriptionHtml")), posted=j.get("publishedAt", ""))


FETCHERS = {"greenhouse": greenhouse, "lever": lever, "ashby": ashby}


def scan(con, companies, cfg, fetch=fetch_json, sleep=0.3):
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    stats = {"companies": 0, "seen": 0, "kept": 0, "new": 0, "errors": []}
    for c in companies:
        fn = FETCHERS.get(c["ats"])
        try:
            jobs = list(fn(c["slug"], fetch))
        except Exception as e:  # 404、限流、结构变化都只记录，不中断
            stats["errors"].append(f"{c['name']}: {e}")
            continue
        stats["companies"] += 1
        # Only a successful full-board fetch can mark an old job as no longer listed.
        con.execute('UPDATE jobs SET is_open=0 WHERE company=? AND ats=?',(c['name'],c['ats']))
        con.executemany('UPDATE jobs SET is_open=1,last_seen=? WHERE id=?',[(now,j['id']) for j in jobs])
        for j in jobs:
            stats["seen"] += 1
            if not (filters.title_ok(j["title"], cfg) and filters.location_ok(j["location"], cfg)):
                continue
            fl = ",".join(filters.flags(j["title"] + " " + j["description"]))
            if con.execute("SELECT 1 FROM jobs WHERE id=?", (j["id"],)).fetchone():
                old = con.execute('SELECT description FROM jobs WHERE id=?',(j['id'],)).fetchone()
                if old['description'] != j['description']:
                    con.execute('DELETE FROM scores WHERE job_id=?',(j['id'],))
                con.execute("UPDATE jobs SET last_seen=?,flags=?,title=?,location=?,url=?,description=?,posted=? WHERE id=?", (now,fl,j['title'],j['location'],j['url'],j['description'],j['posted'],j['id']))
            else:
                con.execute("INSERT INTO jobs(id,company,ats,title,location,url,description,posted,first_seen,last_seen,flags) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                            (j["id"], c["name"], c["ats"], j["title"], j["location"], j["url"], j["description"], j["posted"], now, now, fl))
                stats["new"] += 1
            stats["kept"] += 1
        time.sleep(sleep)
    con.commit()
    return stats
