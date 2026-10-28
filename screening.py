"""Auditable search facets. Unknown requirements are never represented as confirmed fit."""
import re
from candidate import graduation, label as graduation_label, settings as candidate_settings
from market_rules import CALIFORNIA,INTERN

CN_CITIES=['北京','上海','杭州','深圳','广州','成都','南京','苏州','武汉','西安','天津','重庆','合肥','长沙','厦门','宁波','青岛','济南','郑州','无锡','福州']
STATES={'CA':r'california|san francisco|san jose|san diego|los angeles|palo alto|mountain view|sunnyvale|san mateo|oakland|berkeley|irvine|menlo park|foster city|redwood city',
 'NY':r'new york|nyc','MA':r'massachusetts|boston|cambridge','WA':r'seattle|bellevue|redmond|washington state','TX':r'texas|austin|dallas|houston','IL':r'illinois|chicago','CT':r'connecticut|stamford|greenwich','NC':r'north carolina|charlotte|raleigh|durham','FL':r'florida|miami|tampa','VA':r'virginia|mclean|richmond|arlington','DC':r'washington,? (?:dc|district of columbia)|district of columbia','CO':r'colorado|denver|boulder','NJ':r'new jersey|jersey city','PA':r'pennsylvania|philadelphia|pittsburgh'}
FOREIGN=re.compile(r'\b(canada|toronto|vancouver|ontario|quebec|india|bangalore|bengaluru|singapore|australia|london|united kingdom|ireland|dublin|germany|france|brazil|mexico|chile|argentina|colombia|latam|emea|apac|europe|luxembourg|hong kong|taiwan|china|japan|israel|netherlands|amsterdam|poland|spain|portugal|philippines|indonesia|pakistan|malaysia|south africa|uruguay|costa rica)\b',re.I)
DIRECTIONS=[('data','数据分析 / BI',r'数据分析|数据治理|数据运营|数据管理|商业智能|数据工程|data analy|business intelligence|\bBI\b|data quality|data governance|reporting analyst|data engineer'),('product','产品 / 商业 / 增长',r'产品|商业分析|经营分析|业务分析|增长|用户分析|运营分析|product|business analy|growth|marketing analy|operations analy|strategy|strategic'),('risk','风控 / 信用 / 反欺诈',r'风控|风险|信用|反欺诈|risk|credit|fraud'),('research','金融 / 经济研究',r'宏观|投研|研究|投资|金融|finance|financial|econom|investment|research|equity|portfolio'),('quant','量化 / 算法挑战',r'量化|算法|科学家|quant|scientist|machine learning'),('other','其他相关',r'.')]
SKILLS=[('SQL',r'\bsql\b|MaxCompute'),('Python',r'\bpython\b'),('Excel',r'\bexcel\b'),('BI',r'\bbi\b|dashboard|看板|可视化'),('Stata / 计量',r'stata|econometric|计量|面板'),('风控建模',r'credit risk|risk model|scorecard|评分卡|风控模型'),('A/B 实验',r'a/b|实验设计|因果推断|causal'),('Tableau / Power BI',r'tableau|power\s*bi')]

def geography(job):
 loc=job.get('location') or ''
 if job.get('market')=='cn':
  aliases={'北京':'beijing','上海':'shanghai','杭州':'hangzhou','深圳':'shenzhen','广州':'guangzhou','成都':'chengdu','南京':'nanjing','苏州':'suzhou','武汉':'wuhan','西安':'xian','天津':'tianjin','重庆':'chongqing','合肥':'hefei','长沙':'changsha','厦门':'xiamen','宁波':'ningbo'}
  cities=[x for x in CN_CITIES if x in loc or x in aliases and re.search(r'\b'+aliases[x]+r'\b',loc,re.I)]
  outside=bool(re.search(r'香港|澳门|台湾|美国|新加坡|英国|澳大利亚|科威特|迪拜|利雅得|hong kong|taiwan|macau|united states|singapore|australia|london',loc,re.I))
  return {'country':'cn' if cities or (re.search(r'中国|省|\bchina\b|mainland',loc,re.I) and not outside) else 'other' if outside else 'unknown','regions':cities,'label':'含中国大陆 / 境外地点' if cities and outside else '中国大陆' if cities else '港澳台 / 境外' if outside else '国内地点待核对','remote':bool(re.search('远程|remote',loc,re.I))}
 regions=[key for key,pattern in STATES.items() if re.search(r'\b(?:'+pattern+'|'+key+r')\b',loc,re.I)]
 explicit=bool(re.search(r'\b(united states|usa|u\.?s\.?)\b',loc,re.I) or regions)
 foreign=bool(FOREIGN.search(loc))
 return {'country':'mixed' if explicit and foreign else 'us' if explicit else 'other' if foreign else 'unknown','regions':regions,'label':'美国 / 多国' if explicit and foreign else '美国' if explicit else '美国以外' if foreign else '国家待核对','remote':bool(re.search('remote|远程',loc,re.I))}

def authorization(text):
 # Restriction evidence outranks mentions of sponsorship in an equal opportunity statement.
 patterns=[('opt_excluded','明确排除 OPT / 临时授权',r'(?:(?:not|cannot|unable|ineligible|do not)[^.\n]{0,100}(?:\bOPT\b|\bCPT\b))|(?:(?:\bOPT\b|\bCPT\b)[^.\n]{0,50}(?:not eligible|not accepted|ineligible))|permanent (?:US |U\.S\. )?work authorization'),
 ('citizen','公民 / 许可要求待核对',r'(?:must|required|only)[^.\n]{0,60}(?:u\.?s\.? citizen|security clearance)|(?:u\.?s\.? citizenship|security clearance)[^.\n]{0,40}(?:required|must)|must be a (?:u\.?s\.? )?citizen'),
 ('no_future','未来 sponsorship 受限',r'(?:no|not|cannot|unable|without)[^.\n]{0,80}(?:sponsor|sponsorship)|sponsorship[^.\n]{0,35}(?:not available|not provided|not offered)'),
 ('supports','JD 提及支持 sponsorship',r'(?:provide|offer|available|eligible for)[^.\n]{0,90}(?:visa sponsorship|immigration sponsorship|visa support|H-1B)|sponsor (?:employment|work) visas'),
 ('opt_mentioned','JD 提及 OPT / CPT，需核对',r'\b(?:STEM OPT|OPT|CPT)\b')]
 for code,label,pattern in patterns:
  m=re.search(pattern,text,re.I)
  if m:return {'code':code,'label':label,'evidence':text[max(0,m.start()-35):m.end()+100].strip(),'everify':'未核验','i983':'未核验'}
 return {'code':'unknown','label':'授权政策未说明','evidence':'未提取到明确授权政策；不等于接受 OPT 或承诺 sponsorship。','everify':'未核验','i983':'未核验'}

MONTHS={'january':(1,1),'february':(2,2),'march':(3,3),'april':(4,4),'may':(5,5),'june':(6,6),'july':(7,7),'august':(8,8),'september':(9,9),'october':(10,10),'november':(11,11),'december':(12,12),'spring':(3,5),'summer':(6,8),'fall':(9,11),'autumn':(9,11),'winter':(1,2)}
def graduation_conflict(text):
    year,month=graduation();expected=year*12+month
    for clause in re.finditer(r'graduat(?:ion|ing|e|es)[^.!?\n]{0,200}',text,re.I):
        dates=[]
        for match in re.finditer(r'\b('+ '|'.join(MONTHS)+r')\s+(?:of\s+)?(20\d{2})',clause.group(0),re.I):
            lo,hi=MONTHS[match.group(1).lower()];year=int(match.group(2));dates.append((year*12+lo,year*12+hi))
        if dates and not min(x[0] for x in dates)<=expected<=max(x[1] for x in dates):return clause.group(0).strip()
    return ''

def constraints(job):
 title=job.get('title','');jd=job.get('description','');full=title+'\n'+jd
 hard=[];intern=bool(INTERN.search(title+' '+job.get('category','')));cn=job.get('market')=='cn';grad_year,grad_month=graduation()
 if cn:
  cohorts={2000+int(x) for x in re.findall(r'(?<!\d)(?:20)?([2-9][0-9])(?:\s*届|(?=\s*[/、和及]\s*(?:20)?[2-9][0-9]\s*届))',title)}
  if cohorts and grad_year not in cohorts:
   hard.append({'item':'招聘届别','status':'不符合','note':'标题明确面向 '+ ' / '.join(map(str,sorted(cohorts)))+' 届；本机配置为 '+graduation_label()+'。'})
  for m in re.finditer(r'毕业时间窗口[：:]\s*(20\d{2})-(\d{2})-\d{2}\s*[~～至到]+\s*(20\d{2})-(\d{2})-\d{2}',jd):
   start=int(m[1])*12+int(m[2]);end=int(m[3])*12+int(m[4]);year,month=graduation();expected=year*12+month
   if not start<=expected<=end:
    hard.append({'item':'毕业窗口','status':'不符合','note':m[0]+'；不包含 '+graduation_label()+'。'})
 if not cn:
  geo=geography(job)
  if geo['country']=='other':hard.append({'item':'实际工作国家','status':'不符合','note':job.get('location','')+'；不属于美国岗位'})
  phd_only_title=bool(re.search(r'\b(?:ph\.?d\.?|doctoral)\b',title,re.I))
  phd_only_jd=any(re.search(r'(?:must|required|requires|pursuing)[^.\n]{0,50}\b(?:ph\.?d\.?|doctoral)\b|\b(?:ph\.?d\.?|doctoral)\b[^.\n]{0,30}(?:required|only)',line,re.I) and not re.search(r'master|bachelor|undergraduate',line,re.I) for line in re.split(r'[\n;]',jd))
  if (phd_only_title or phd_only_jd) and candidate_settings().get('degree')!='doctorate':
   hard.append({'item':'学历要求','status':'不符合','note':'明确要求博士；本机配置未表明博士资格。'})
  if intern:
   window=graduation_conflict(jd)
   if window:hard.append({'item':'毕业窗口','status':'不符合','note':window+'；与 '+graduation_label()+' 不一致。'})
   m=re.search(r'(?:must|require[ds]?|expected to|will)[^.\n]{0,65}(?:return|returning)[^.\n]{0,45}(?:school|university|academic|semester|quarter)|(?:returning to (?:school|university)|at least one (?:semester|quarter))[^.\n]{0,80}(?:after|following|internship)',jd,re.I)
   if m:hard.append({'item':'实习后返校','status':'不符合' if re.search(str(grad_year)+r'|summer',title,re.I) else '不确定','note':m.group(0)+'；毕业配置为 '+graduation_label()+'，返校计划未核实。'})
   if re.search(rf'(?:graduat\w*|class of)[^.\n]{{0,80}}{grad_year+1}',jd,re.I) and not re.search(rf'(?:graduat\w*|class of)[^.\n]{{0,80}}{grad_year}',jd,re.I):
    hard.append({'item':'毕业窗口','status':'不符合','note':'JD 面向后续届别，未提取到接受 '+graduation_label()+' 的依据。'})
  auth=authorization(full)
  if auth['code']=='opt_excluded':hard.append({'item':'OPT 适用性','status':'不符合','note':auth['evidence']})
  elif auth['code']=='citizen':hard.append({'item':'公民与安全许可','status':'不确定','note':auth['evidence']})
 return hard

def facets(job,analysis=None):
 analysis=analysis or {};title=job.get('title','');jd=job.get('description','');full=title+'\n'+jd;cn=job.get('market')=='cn'
 direction=next(({'code':c,'label':l} for c,l,p in DIRECTIONS if re.search(p,title,re.I)),{'code':'other','label':'其他相关'})
 if re.search(r'博士|\bph\.?d|quant researcher|量化研究|算法|研究型|研发|软件开发|数据开发|分布式|Agent工程师',title,re.I):direction={'code':'quant','label':'量化 / 算法挑战'}
 experience=[]
 pattern=r'(?<!\d)(\d{1,2})\s*(?:\+|[-–至到]\s*\d{1,2})?\s*(?:years?[^.。\n]{0,65}experience|年[^。\n]{0,60}经验)'
 for m in re.finditer(pattern,jd,re.I):
  context=jd[max(0,m.start()-40):m.end()+35]
  optional=bool(re.search(r'prefer|nice.to.have|优先|应届.*(?:亦可|可考虑)',context,re.I))
  experience.append({'years':int(m.group(1)),'optional':optional,'evidence':context.strip()})
 mandatory=[x['years'] for x in experience if not x['optional']]
 intern=bool(INTERN.search(title+' '+job.get('category','')));newgrad=bool(re.search(rf'{graduation()[0]}|校招|campus|new.?grad|graduate program|entry.level|early career',title+' '+job.get('category',''),re.I))
 hard=list({(h['item'],h.get('status'),h.get('note')):h for h in analysis.get('hard',[])+constraints(job)}.values())
 conflicts=list(dict.fromkeys(x['item'] for x in hard if x.get('status')=='不符合'))
 return {'geo':geography(job),'direction':direction,'type':'intern' if intern else 'fulltime',
  'track':'intern' if intern else 'graduate' if newgrad else 'experienced' if (job.get('category')=='社会招聘' or mandatory and min(mandatory)>=2) else 'unclassified',
  'experience':{'min_years':min(mandatory) if mandatory else None,'items':experience[:4],'label':f'明确 {min(mandatory)}+ 年' if mandatory else '年限未明确 / 优先项'},
  'skills':[label for label,p in SKILLS if re.search(p,full,re.I)],'matched_count':len(analysis.get('matched',[])), 'gap_count':len(analysis.get('gaps',[])),
  'authorization':{'code':'na','label':'国内岗位不使用美国授权筛选'} if cn else authorization(full),
  'checks':hard,'conflicts':conflicts,'eligible':not conflicts,
  'time_label':graduation_label()+'；到岗日期需核对','source_label':'官网浏览器核实（部分）' if job.get('ats')=='cn-public_browser' else '官网自动采集' if job.get('source_id') or job.get('ats') in ['greenhouse','lever','ashby'] else '人工补充 / 待核验'}
