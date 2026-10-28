"""Deadline provenance and platform leads; never infer that an unknown date means rolling."""
import json
import re
from datetime import datetime,date
from pathlib import Path
from zoneinfo import ZoneInfo


def deadline_info(job,today=None):
    today=today or datetime.now(ZoneInfo('Asia/Shanghai')).date()
    candidates=[]
    if re.fullmatch(r'20\d{2}-\d{2}-\d{2}',job.get('deadline') or ''):
        try:candidates.append(date.fromisoformat(job['deadline']).isoformat())
        except ValueError:pass
    jd=job.get('description') or ''
    pattern=r'(?:报名|网申|投递|申请|简历)?截止(?:时间|日期)?[：:\s]*(20\d{2})[-年/](\d{1,2})[-月/](\d{1,2})'
    for match in re.finditer(pattern,jd):
        try:candidates.append(date(*map(int,match.groups())).isoformat())
        except ValueError:pass
    unique=sorted(set(candidates))
    source='官网职位字段 / 正文' if job.get('source_id') else '手动资料，待核对官网'
    if len(unique)>1:
        return {'status':'conflict','label':'日期冲突，需核对','date':'','days_left':None,'dates':unique,'source':source,'timezone':'Asia/Shanghai'}
    if not unique:
        return {'status':'unknown','label':'未公布截止日期','date':'','days_left':None,'dates':[],'source':source,'timezone':'Asia/Shanghai'}
    days=(date.fromisoformat(unique[0])-today).days
    return {'status':'expired' if days<0 else 'urgent' if days<=3 else 'soon' if days<=7 else 'open',
            'label':'已截止' if days<0 else '北京时间今日截止，时刻需核对' if days==0 else f'{days} 天内截止',
            'date':unique[0],'days_left':days,'dates':unique,'source':source,'timezone':'Asia/Shanghai'}


def load_intelligence(root):
    path=Path(root)/'config/recruitment_intelligence.json'
    data=json.loads(path.read_text()) if path.exists() else {'platforms':[],'leads':[]}
    today=datetime.now(ZoneInfo('Asia/Shanghai')).date()
    for lead in data.get('leads',[]):
        value=lead.get('deadline','')
        lead['deadline_info']=deadline_info({'deadline':value},today)
        if lead.get('verification')=='platform_lead':lead['deadline_info']['source']='第三方线索，尚未官网核验'
    return data
