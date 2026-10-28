"""Candidate preferences stay local; committed defaults are explicitly fictional."""
import json
import os
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DEFAULTS = {'graduation_month':'2030-06','degree':'masters','intern_region':'any_us','fulltime_region':'any_us','demo':True}

def settings():
    value=dict(DEFAULTS)
    for path in [ROOT/'config/candidate.example.json',ROOT/'data/candidate.json']:
        if path.exists():value.update(json.loads(path.read_text(encoding='utf-8')))
    month=os.environ.get('JOBSCOUT_GRADUATION_MONTH',value['graduation_month'])
    if not re.fullmatch(r'20\d{2}-(?:0[1-9]|1[0-2])',str(month)):
        raise ValueError('graduation_month must use YYYY-MM')
    value['graduation_month']=month
    return value

def graduation():
    year,month=map(int,settings()['graduation_month'].split('-'))
    return year,month

def label():
    year,month=graduation()
    return f'{year} 年 {month} 月（本机候选人配置）'

def ensure_local_files(root):
    root=Path(root);(root/'data').mkdir(exist_ok=True)
    for name in ['profile.md','profile_cn.md']:
        target=root/name;example=root/'examples'/name
        if not target.exists() and example.exists():target.write_text(example.read_text(encoding='utf-8'),encoding='utf-8')
    local=root/'data/candidate.json';example=root/'config/candidate.example.json'
    if not local.exists() and example.exists():local.write_text(example.read_text(encoding='utf-8'),encoding='utf-8')
