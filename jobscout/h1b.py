"""导入 DOL LCA 披露数据与 USCIS Employer Data Hub 数据，并按公司名关联。
注意：LCA 获批只是申请前的劳工条件认证，不等于 H-1B 请愿获批；USCIS 数据才是批准数。"""
import csv
import difflib
import re

SUFFIX = {"inc", "incorporated", "llc", "l", "c", "ltd", "limited", "corp", "corporation", "co", "company", "lp", "llp", "plc", "opco", "the", "usa", "us"}
_CACHE = {}


def norm(name):
    s = re.sub(r"[^a-z0-9 ]", " ", str(name or "").lower().replace("&", " and "))
    return " ".join(t for t in s.split() if t not in SUFFIX)


def _rows(path):
    if str(path).lower().endswith((".xlsx", ".xlsm")):
        import openpyxl
        ws = openpyxl.load_workbook(path, read_only=True, data_only=True).active
        it = ws.iter_rows(values_only=True)
        head = [str(h or "").strip() for h in next(it)]
        for r in it:
            yield dict(zip(head, r))
    else:
        with open(path, newline="", encoding="utf-8-sig") as f:
            yield from csv.DictReader(f)


def _int(v):
    try:
        return int(float(str(v).replace(",", "")))
    except (TypeError, ValueError):
        return 0


def _save(con, source, fy, agg):
    con.executemany("INSERT OR REPLACE INTO h1b(norm_name,display_name,fiscal_year,source,count,extra) VALUES(?,?,?,?,?,?)",
                    [(n, v[0], fy_, source, v[1], v[2]) for (n, fy_), v in agg.items()])
    con.commit()
    _CACHE.clear()
    return len(agg)


def import_lca(con, path, fy):
    agg, cols = {}, None
    for row in _rows(path):
        if cols is None:
            low = {str(k).lower(): k for k in row}
            cols = {n: low.get(n.lower()) for n in ("EMPLOYER_NAME", "CASE_STATUS", "VISA_CLASS", "PW_WAGE_LEVEL", "TOTAL_WORKER_POSITIONS")}
            if not cols["EMPLOYER_NAME"]:
                raise ValueError(f"找不到 EMPLOYER_NAME 列，实际列名：{list(row)[:15]}")
        g = lambda k: row.get(cols[k]) if cols[k] else None
        if cols["VISA_CLASS"] and str(g("VISA_CLASS") or "").strip().upper() != "H-1B":
            continue
        if cols["CASE_STATUS"] and str(g("CASE_STATUS") or "").strip().upper() != "CERTIFIED":
            continue
        name = str(g("EMPLOYER_NAME") or "").strip()
        n = norm(name)
        if not n:
            continue
        pos = _int(g("TOTAL_WORKER_POSITIONS")) or 1
        hi = pos if str(g("PW_WAGE_LEVEL") or "").strip().upper() in ("III", "IV", "3", "4") else 0
        a = agg.setdefault((n, str(fy)), [name, 0, 0])
        a[1] += pos
        a[2] += hi
    return _save(con, "lca", fy, agg)


def import_uscis(con, path, fy=None):
    agg, cols = {}, None
    for row in _rows(path):
        if cols is None:
            def find(*subs):
                return next((k for k in row if all(s in str(k).lower() for s in subs)), None)
            cols = dict(name=find("employer"), fy=find("fiscal"), ini=find("initial", "approval"), con=find("continuing", "approval"))
            if not cols["name"] or not cols["ini"]:
                raise ValueError(f"找不到雇主或 Initial Approval 列，实际列名：{list(row)[:15]}")
        n = norm(row[cols["name"]])
        if not n:
            continue
        year = str(row.get(cols["fy"]) if cols["fy"] else fy or "")
        ini, cont = _int(row.get(cols["ini"])), _int(row.get(cols["con"])) if cols["con"] else 0
        a = agg.setdefault((n, year), [str(row[cols["name"]]).strip(), 0, 0])
        a[1] += ini + cont
        a[2] += ini
    return _save(con, "uscis", fy or "", agg)


def lookup(con, names, cutoff=0.9):
    names = [norm(n) for n in names if n]
    key = (id(con), con.execute("SELECT COUNT(*) FROM h1b").fetchone()[0])
    if key not in _CACHE:
        _CACHE.clear()
        _CACHE[key] = [r[0] for r in con.execute("SELECT DISTINCT norm_name FROM h1b")]
    known = _CACHE[key]
    hit = next((n for n in names if n in known), None)
    if not hit:
        hit = next((m[0] for n in names for m in [difflib.get_close_matches(n, known, 1, cutoff)] if m), None)
    if not hit:
        return None
    rows = con.execute("SELECT display_name,fiscal_year,source,count,extra FROM h1b WHERE norm_name=? ORDER BY fiscal_year", (hit,)).fetchall()
    if not rows:
        return None
    return {"matched": rows[0]["display_name"], "rows": [dict(r) for r in rows]}


def describe(info):
    if not info:
        return "H-1B：无匹配记录（可能是公司名没对上，请手动查官方数据）"
    parts = []
    for r in info["rows"]:
        if r["source"] == "lca":
            share = f"，III/IV 级 {r['extra'] * 100 // r['count']}%" if r["count"] else ""
            parts.append(f"LCA FY{r['fiscal_year']} {r['count']} 个职位{share}")
        else:
            parts.append(f"USCIS FY{r['fiscal_year']} 批准 {r['count']}（初次 {r['extra']}）")
    return f"H-1B（匹配到：{info['matched']}）：" + "；".join(parts)
