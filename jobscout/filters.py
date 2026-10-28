import re

NO_SPONSOR = re.compile(r"(no|not|cannot|can't|unable to)[^.]{0,40}sponsor|without[^.]{0,30}sponsor|sponsorship (is )?not (available|provided|offered)", re.I)
CITIZEN = re.compile(r"u\.?s\.? citizen(ship)?( (is )?(required|only))?|must be a (u\.?s\.? )?citizen|citizenship (is )?required", re.I)
CLEARANCE = re.compile(r"security clearance|secret clearance|ts/sci|public trust", re.I)


def _has(tokens, text):
    return any(re.search(r"(?<![a-z0-9])" + re.escape(t.strip()) + r"(?![a-z0-9])", text) for t in tokens)


def title_ok(title, cfg):
    t = title.lower()
    f = cfg["filter"]
    return _has(f["include_title"], t) and not _has(f["exclude_title"], t)


def location_ok(location, cfg):
    """有美国地名就通过；只写 Remote 时，若带有外国地名则拒绝；空地点放行（需人工核对）。"""
    loc = (location or "").lower()
    if not loc:
        return True
    f = cfg["filter"]
    if _has([t for t in f["locations"] if t != "remote"], loc):
        return True
    return "remote" in loc and not _has(f.get("foreign", []), loc)


def flags(text):
    """返回风险标记。只是提醒，必须人工核对原文。"""
    out = []
    if NO_SPONSOR.search(text):
        out.append("no_sponsor")
    if CITIZEN.search(text):
        out.append("citizen")
    if CLEARANCE.search(text):
        out.append("clearance")
    return out
