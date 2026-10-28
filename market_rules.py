"""Market-specific preferences and Chinese JD evidence. No work-authorization assumptions."""
import re
from datetime import datetime
from zoneinfo import ZoneInfo

CALIFORNIA = re.compile(r'\b(california|ca|san francisco|south san francisco|san jose|san diego|los angeles|berkeley|oakland|palo alto|menlo park|mountain view|sunnyvale|santa clara|cupertino|foster city|san mateo|redwood city|irvine|santa monica|bay area|sf[- ]hq)\b|加州|旧金山|洛杉矶|圣地亚哥|湾区',re.I)
CHINA = re.compile(r'中国|国内|北京|上海|杭州|深圳|广州|成都|南京|苏州|武汉|西安|天津|重庆|合肥|长沙|全国|\b(china|beijing|shanghai|hangzhou|shenzhen|guangzhou|chengdu|nanjing|suzhou|wuhan|xian|tianjin|chongqing)\b',re.I)
INTERN = re.compile(r'\bintern(?:ship)?\b|实习|summer(?:\s+20\d{2})?\s+(?:analyst|associate)',re.I)
TERMS = {
 'SQL':['sql'],'Python':['python'],'Excel':['excel'],'pandas':['pandas'],
 '数据分析':['数据分析','data analytics','data analysis'],'商业分析':['商业分析','business analytics','business intelligence'],
 '产品分析':['产品分析','产品及竞品分析','product analytics'],'BI / 看板':['bi','看板','dashboard','商业智能'],
 '数据可视化':['数据可视化','data visualization','plotly'],'统计建模':['统计','计量','回归','statistical','regression','stata'],
 '风险建模':['风控','风险模型','风险建模','risk model','信用评分','credit scorecard'],'机器学习':['机器学习','machine learning','xgboost','scikit-learn'],
 'Tableau':['tableau'],'Power BI':['power bi'],'A/B 实验':['a/b','ab test','实验设计','因果推断'],
 '数据仓库 / ETL':['数据仓库','etl','dataworks','maxcompute'],'R':['r 语言','r语言',' r,','、r',' r；'],
 '宏观与政策研究':['宏观','cpi','gdp','美联储','关税','macroeconomic'],
 'Wind':['wind','万得'],'CEIC':['ceic'],'Bloomberg':['bloomberg'],
 '金融研究与报告':['宏观研究','固收','固定收益','研究报告','投资研究'],
 '信用风险基础':['信用风险','信用评分','credit risk','credit scorecard'],
 }


def preference(job,pref):
    intern=bool(INTERN.search(job.get('title','')+' '+job.get('category','')))
    market=job.get('market','us')
    ca=market=='us' and intern and bool(CALIFORNIA.search(job.get('location','')))
    preferred=ca and pref.get('intern_region','any_us')=='california'
    return {'job_type':'intern' if intern else 'fulltime','preferred':preferred,
            'label':'加州实习 · 偏好匹配' if preferred else '全职 · 美国州别不限' if market=='us' and not intern else '其他地区实习' if market=='us' else '国内实习' if intern else '国内全职 / 校招'}


def assess_china(job,profile):
    from candidate import label as graduation_label, settings as candidate_settings
    title=job.get('title','');jd=job.get('description','');loc=job.get('location','')
    text=(title+' '+jd).lower()
    lines=[line for line in profile.splitlines() if not re.search(r'^来源|^求职偏好|^求职目标|缺口|没有|不熟悉|未证实|暂无|no experience',line,re.I)]
    evidence=[];have=[];gaps=[]
    for name,aliases in TERMS.items():
        if any(alias_present(a,text) for a in aliases):
            line=next((line for line in lines if any(alias_present(a,line.lower()) for a in aliases)),'')
            (have if line else gaps).append(name)
            evidence.append({'req':name,'evidence':line or '简历中暂无已证实的对应经历','strength':'中' if line else '无'})
    hard=[]
    hard.append({'item':'工作地点','status':'符合' if CHINA.search(loc) else '不确定','note':loc+'；国内城市暂不限制' if loc else '尚未填写，需查看 JD'})
    if candidate_settings().get('degree')!='doctorate' and (re.search(r'博士',title) or re.search(r'博士(?:研究生)?(?:学历|学位|在读)|学历[^。\n]{0,12}博士|仅限博士',jd)):
        hard.append({'item':'学历要求','status':'不符合','note':'岗位明确要求博士；本机配置未表明博士资格'})
    senior=bool(re.search(r'高级|资深|专家|总监|负责人|首席|\b(senior|director|principal|lead)\b',title,re.I) or ('经理' in title and not re.search('产品|助理|实习|校招|2027',title)))
    hard.append({'item':'岗位职级','status':'不符合' if senior else '不确定','note':'检测到资深或管理职级，请核对' if senior else '需核对是否应届、实习或初级岗位'})
    requirements=re.split(r'任职资格[：:]|任职要求[：:]',jd)[-1]
    if re.search(r'岗位职责内|上方.*(?:要求|说明)|详见上方',requirements):requirements=jd
    years_matches=list(re.finditer(r'(?<![0-9])([0-9一二两三四五六七八九十]{1,2})\s*(?:[-至到~]\s*[0-9一二两三四五六七八九十]{1,2}\s*)?年(?:及以上|以上)?[^。；;\n]{0,80}?经验',requirements))
    numerals={'一':1,'二':2,'两':2,'三':3,'四':4,'五':5,'六':6,'七':7,'八':8,'九':9,'十':10}
    for years in years_matches:
        n=int(years.group(1)) if years.group(1).isdigit() else numerals.get(years.group(1),10)
        line=requirements[requirements.rfind('\n',0,years.start())+1:requirements.find('\n',years.end()) if '\n' in requirements[years.end():] else len(requirements)]
        tail=requirements[years.end():years.end()+12]
        optional=bool(re.search(r'优秀应届|应届生.*(?:可|亦)|泛校招',line) or ('优先' in tail and not re.search(r'必须',line)))
        hard.append({'item':'经验要求','status':'不符合' if n>=2 and not optional else '不确定','note':years.group(0)+('（原文为优先或应届可考虑）' if optional else '；简历未证实对应年限的正式工作经验')})
        if n>=2 and not optional:break
    hard.append({'item':'毕业批次与到岗时间','status':'不确定','note':graduation_label()+'；以当前招聘批次、在读要求、每周天数及到岗时间为准'})
    if job.get('deadline') and job['deadline']<datetime.now(ZoneInfo('Asia/Shanghai')).date().isoformat():
        hard.append({'item':'投递截止','status':'不符合','note':'官网截止日期：'+job['deadline']})
    for item,pattern in [('专业范围',r'[^。\n]{0,25}专业[^。\n]{0,80}'),('资格证与考试',r'[^。\n]{0,20}(?:证券从业|基金从业|CFA|FRM|CET[- ]?[46]|英语六级)[^。\n]{0,70}'),('实习出勤',r'[^。\n]{0,20}(?:每周.{0,10}天|实习.{0,10}个月|返校)[^。\n]{0,60}')]:
        evidence_line=re.search(pattern,requirements,re.I)
        if evidence_line:hard.append({'item':item,'status':'不确定','note':evidence_line.group(0).strip()+'；需确认，未据此假定你符合'})
    from screening import constraints
    hard.extend(constraints({**job,'market':'cn'}))
    blocked=any(h['status']=='不符合' for h in hard)
    score=round(30+45*len(have)/max(1,len(evidence))*min(1,len(evidence)/4)+(8 if re.search(r'数据|分析|商业|策略|风控|产品',title) else 0))
    if blocked:score=min(score,40)
    direct=bool(re.search(r'数据分析|商业分析|经营分析|产品分析|业务分析|增长分析|用户分析|数据治理|数据运营|风险分析|风险策略|风控策略|风险建模|\bBI\b|analytics|data analyst',title,re.I))
    advanced_quant=bool(re.search(r'多因子|Alpha来源|组合优化|风险量化引擎|尾部风险预测|量化引擎|深度量化研究',jd,re.I) and re.search(r'Pytorch|paper to code|随机过程|文献复现|多资产风险模型',requirements,re.I))
    stretch=bool(re.search(r'量化研究|量化策略|算法|高频|深度学习|量化开发|大模型|金融工程研究|研究型|研发|软件开发|数据开发|分布式|Agent工程师',title) or advanced_quant)
    low=bool(re.search(r'销售|柜员|客户经理|理财经理|营销',title))
    tier='low' if low or blocked else 'stretch' if stretch else 'priority' if direct else 'related'
    reasons=[];risks=[]
    if direct:reasons.append('岗位职责包含分析或指标相关任务；对应经验以资料证据为准')
    if job.get('sector') in ['银行','证券','公募基金','私募基金']:
        reasons.append('金融岗位需单独核实专业背景、研究项目与实际经验')
    if stretch:
        score=min(score,55)
        risks.append('挑战方向：需核实量化实盘、Alpha 研究或专职算法研发经历；一般课程项目不能替代正式经验')
    if not direct and not stretch:risks.append('相关备选：需核对实际工作是否以数据分析为主，避免泛管培或主要销售职责')
    if re.search(r'每周.{0,8}[三四五3-5].{0,3}天|实习.{0,8}[3-6三四五六].{0,3}月',jd):risks.append('JD 提到实习出勤或时长要求，需要与你的在读安排核对')
    if low:score=min(score,35)
    if job.get('category')=='社会招聘' and not re.search(r'实习|2027|校招|应届',title):
        score=min(score,60)
        risks.append('官网标注为社会招聘；应届生是否可投需要核对，不按校招岗位推荐')
    return {'score':score,'verdict':'暂缓' if blocked else '挑战岗位' if tier=='stretch' else '优先查看' if tier=='priority' and score>=65 else '相关备选' if tier=='related' else '待复核',
            'summary':'国内岗位初筛，依据中文简历对照；毕业批次、到岗日期和实习天数需人工确认。',
            'method':'rules','hard':hard,'matched':have,'gaps':gaps,'evidence':evidence,'risks':risks,'match_tier':tier,'fit_reasons':reasons,
            'resume':'中文数据分析版','edits':[],'opening':'','dims':{'技能证据覆盖':round(100*len(have)/max(1,len(evidence)))},
            'h1b':'不适用：国内岗位不使用美国签证记录排序。'}


def alias_present(alias,value):
    if re.fullmatch(r'[a-z0-9 /_-]+',alias):
        return bool(re.search(r'(?<![a-z0-9])'+re.escape(alias)+r'(?![a-z0-9])',value))
    return alias in value
