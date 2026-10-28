import argparse
import json
import os
import pathlib
import tomllib

from . import ats, db, h1b, scoring


LOCAL = pathlib.Path("data/local.json")


def load_local():
    try:
        return json.loads(LOCAL.read_text(encoding="utf-8"))
    except Exception:
        return {}


def save_local(d):
    LOCAL.parent.mkdir(parents=True, exist_ok=True)
    LOCAL.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
    try:
        LOCAL.chmod(0o600)
    except OSError:
        pass


def save_companies(rows, path="config/companies.toml"):
    q = lambda x: json.dumps(str(x), ensure_ascii=False)
    out = ["# ats: greenhouse | lever | ashby；h1b_names：官方数据里的法人名\n"]
    for r in rows:
        if not str(r.get("name") or "").strip() or not str(r.get("slug") or "").strip():
            continue
        names = [x.strip() for x in str(r.get("h1b_names") or "").split(";") if x.strip()]
        out.append(f"\n[[company]]\nname = {q(r['name'].strip())}\nats = {q(r.get('ats') or 'greenhouse')}\nslug = {q(r['slug'].strip())}\nh1b_names = [{', '.join(q(n) for n in names)}]\n")
    pathlib.Path(path).write_text("".join(out), encoding="utf-8")


def load():
    from candidate import ensure_local_files
    ensure_local_files(pathlib.Path.cwd())
    cfg = tomllib.loads(pathlib.Path("config/settings.toml").read_text(encoding="utf-8"))
    loc = load_local()
    if loc.get("api_key"):
        os.environ["ANTHROPIC_API_KEY"] = loc["api_key"]
    if loc.get("model"):
        cfg["model"] = loc["model"]
    comps = tomllib.loads(pathlib.Path("config/companies.toml").read_text(encoding="utf-8"))["company"]
    profile = pathlib.Path("profile.md").read_text(encoding="utf-8")
    return cfg, comps, profile


def h1b_info(con, comps, cfg, company):
    c = next((x for x in comps if x["name"] == company), {})
    return h1b.lookup(con, [company] + c.get("h1b_names", []), cfg["fuzzy_cutoff"])


def report(con, comps, cfg, top=15, min_score=50):
    rows = con.execute("""SELECT j.*, s.score, s.verdict, s.detail FROM jobs j JOIN scores s ON s.job_id=j.id
                          WHERE j.status IN ('new','shortlist') AND s.score>=? ORDER BY s.score DESC LIMIT ?""", (min_score, top)).fetchall()
    out = []
    for j in rows:
        d = json.loads(j["detail"])
        out.append(f"### {j['score']}｜{j['verdict']}｜{j['company']}｜{j['title']}\n{j['location']}｜{j['url']}\n"
                   f"{h1b.describe(h1b_info(con, comps, cfg, j['company']))}\n"
                   f"{d.get('summary', '')}\n匹配：{', '.join(d.get('matched', [])[:8])}\n缺口：{', '.join(d.get('gaps', [])[:8])}\n"
                   f"风险：{'；'.join(d.get('risks', [])) or '无'}\n")
    return "\n".join(out) or "没有符合条件的岗位。"


def main():
    ap = argparse.ArgumentParser(prog="jobscout")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("scan")
    s = sub.add_parser("score"); s.add_argument("--no-llm", action="store_true")
    sub.add_parser("ai-score")
    for n in ("import-lca", "import-uscis"):
        p = sub.add_parser(n); p.add_argument("file"); p.add_argument("--fy", required=(n == "import-lca"))
    r = sub.add_parser("report"); r.add_argument("--top", type=int, default=15); r.add_argument("--min-score", type=int, default=50)
    a = ap.parse_args()
    cfg, comps, profile = load()
    con = db.connect()
    if a.cmd == "scan":
        st = ats.scan(con, comps, cfg)
        print({k: v for k, v in st.items() if k != "errors"})
        for e in st["errors"]:
            print("  跳过：", e)
    elif a.cmd == "score":
        n = scoring.score_pending(con, profile, cfg, lambda j: h1b.describe(h1b_info(con, comps, cfg, j["company"])), use_llm=not a.no_llm)
        print(f"已评分 {n} 个岗位")
    elif a.cmd == "ai-score":
        d, e = scoring.ai_rescore(con, profile, cfg, lambda j: h1b.describe(h1b_info(con, comps, cfg, j["company"])))
        print(f"AI 评分完成 {d} 个", *e, sep="\n  ")
    elif a.cmd == "import-lca":
        print("导入雇主数：", h1b.import_lca(con, a.file, a.fy))
    elif a.cmd == "import-uscis":
        print("导入雇主数：", h1b.import_uscis(con, a.file, a.fy))
    elif a.cmd == "report":
        print(report(con, comps, cfg, a.top, a.min_score))
