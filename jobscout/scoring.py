import json
import os
import re
import urllib.request
from datetime import datetime, timezone

KW = ["sql", "python", "tableau", "looker", "power bi", "excel", "stata", "pandas", "scikit", "xgboost", "machine learning", "statistics",
      "a/b", "experiment", "dashboard", "etl", "airflow", "dbt", "snowflake", "bigquery", "spark", "aws", "credit", "risk", "fintech",
      "forecast", "optimization", "visualization", "product analytics", "data warehouse", "git", "regression"]

PROMPT = """你是严格的求职顾问。根据候选人资料评估岗位匹配度，只输出 JSON，不要任何其他文字。
评分规则：先看硬性条件（学历、年限、地点、工作授权、公民身份/安全许可、实习或全职类型与时间是否对得上候选人目标），不满足则 score 不超过 45；再看技能覆盖、经历相关度、加分项。不要编造候选人没有的经历。若 JD 写明不提供 sponsorship，不得推定 OPT 期间可接受；区分当前与未来的授权要求。公民或安全许可要求需与资料逐项核对，不明确时标为待核实。
JSON 结构：{{"score":0-100整数,"verdict":"值得投|可投|谨慎|不投","summary":"一句话","hard":[{{"item":"","status":"符合|不符合|不确定","note":""}}],"matched":[""],"gaps":[""],"resume":"Technical|FinTech|InvestmentResearch|中文数据分析版","edits":[""],"risks":[""],"opening":"cover letter 开头两句","dims":{{"硬性条件":0,"技能":0,"经历相关度":0,"行业与方向":0,"成长空间":0}},"evidence":[{{"req":"","evidence":"","strength":"强|中|弱|无"}}],"h1b":"据 JD 与雇主 H-1B 记录判断对留美的影响"}}
公司：{company}；职位：{title}；地点：{location}
雇主 H-1B 记录：{h1b}
【候选人资料】
{profile}
【岗位描述】
{jd}"""


ROLE = re.compile(r"analy|data|business intelligence|\bbi\b|risk|quantitative|strateg|credit|fraud|financ")
LEVEL = re.compile(r"intern|new grad|university|entry|associate|junior")
SENIOR_YEARS = re.compile(r"\b([4-9]|1\d)\+?\s*(or more\s*)?years")


def heuristic(job, profile):
    """关键词初筛：命中的 JD 关键词太少时不给高分；只用于排序，不代表真实匹配度。"""
    title = job["title"].lower()
    text = (title + " " + (job["description"] or "")).lower()
    p = "\n".join(l for l in profile.lower().splitlines() if not l.startswith("缺口"))
    has = lambda k, s: re.search(r"(?<![a-z0-9])" + re.escape(k) + r"(?![a-z0-9])", s)
    inj = [k for k in KW if has(k, text)]
    have = [k for k in inj if has(k, p)]
    cov = len(have) / len(inj) if inj else 0
    conf = min(1, len(inj) / 6)
    score = 30 + 40 * cov * conf + (10 if ROLE.search(title) else 0) + (8 if LEVEL.search(text) else 0) - (10 if SENIOR_YEARS.search(text) else 0)
    return {"score": int(max(0, min(score, 80))), "verdict": "初筛", "summary": "关键词初筛，未经 AI 评估", "matched": have,
            "gaps": [k for k in inj if k not in have], "method": "heuristic"}


def apply_caps(res, flag_str):
    fl = set(filter(None, (flag_str or "").split(",")))
    res.setdefault("risks", [])
    if fl & {"citizen", "clearance"}:
        res["score"] = min(res["score"], 30)
        res["risks"].append("JD 疑似要求美国公民或安全许可，请核对原文")
    if "no_sponsor" in fl:
        res["score"] = min(res["score"], 60)
        res["risks"].append("JD 疑似不提供 sponsorship，OPT 之后没有后续，请核对原文")
    if not res.get("verdict"):
        s = res["score"]
        res["verdict"] = "值得投" if s >= 80 else "可投" if s >= 65 else "谨慎" if s >= 50 else "不投"
    return res


def llm(job, profile, h1b_text, model, api_key):
    prompt = PROMPT.format(company=job["company"], title=job["title"], location=job["location"], h1b=h1b_text, profile=profile, jd=(job["description"] or "")[:9000])
    body = json.dumps({"model": model, "max_tokens": 2000, "messages": [{"role": "user", "content": prompt}]}).encode()
    req = urllib.request.Request("https://api.anthropic.com/v1/messages", data=body,
                                 headers={"x-api-key": api_key, "anthropic-version": "2023-06-01", "content-type": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as r:
        d = json.loads(r.read())
    text = "".join(b.get("text", "") for b in d["content"] if b.get("type") == "text")
    res = json.loads(re.search(r"\{.*\}", text, re.S).group(0))
    res["method"] = "llm"
    return res


def score_pending(con, profile, cfg, h1b_for, limit=300, use_llm=True):
    """h1b_for(job_row) -> 描述文本。先用关键词给所有未评分岗位初筛，再对最靠前的 N 个调用模型。"""
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    rows = con.execute("SELECT * FROM jobs WHERE id NOT IN (SELECT job_id FROM scores) ORDER BY first_seen DESC LIMIT ?", (limit,)).fetchall()
    scored = []
    for j in rows:
        res = apply_caps(heuristic(j, profile), j["flags"])
        scored.append((j, res))
    key = os.environ.get("ANTHROPIC_API_KEY")
    if use_llm and key:
        cand = sorted([x for x in scored if x[1]["score"] >= cfg["llm_min_heuristic"] and not set(x[0]["flags"].split(",")) & {"citizen", "clearance"}],
                      key=lambda x: -x[1]["score"])[: cfg["llm_top_n"]]
        for j, _ in cand:
            try:
                r = apply_caps(llm(j, profile, h1b_for(j), cfg["model"], key), j["flags"])
                scored = [(jj, r if jj["id"] == j["id"] else rr) for jj, rr in scored]
            except Exception as e:
                print(f"LLM 评分失败 {j['company']} {j['title']}: {e}")
    for j, r in scored:
        con.execute("INSERT OR REPLACE INTO scores(job_id,score,verdict,detail,method,scored_at) VALUES(?,?,?,?,?,?)",
                    (j["id"], r["score"], r["verdict"], json.dumps(r, ensure_ascii=False), r["method"], now))
    con.commit()
    return len(scored)


def ai_rescore(con, profile, cfg, h1b_for, n=None):
    """对已有初筛分数、靠前的岗位调用模型，覆盖原评分。返回 (成功数, 错误列表)。"""
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        return 0, ["未设置 API 密钥"]
    rows = con.execute("""SELECT j.* FROM jobs j JOIN scores s ON s.job_id=j.id
                          WHERE s.method='heuristic' AND j.status IN ('new','shortlist') AND s.score>=?
                          ORDER BY s.score DESC LIMIT ?""", (cfg["llm_min_heuristic"], n or cfg["llm_top_n"])).fetchall()
    done, errs = 0, []
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    for j in rows:
        if set(j["flags"].split(",")) & {"citizen", "clearance"}:
            continue
        try:
            r = apply_caps(llm(j, profile, h1b_for(j), cfg["model"], key), j["flags"])
            con.execute("INSERT OR REPLACE INTO scores(job_id,score,verdict,detail,method,scored_at) VALUES(?,?,?,?,?,?)",
                        (j["id"], r["score"], r["verdict"], json.dumps(r, ensure_ascii=False), "llm", now))
            con.commit()
            done += 1
        except Exception as e:
            errs.append(f"{j['company']} {j['title']}: {e}")
    return done, errs
