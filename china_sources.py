"""Read public Chinese employer job listings; never log in or submit applications."""
import concurrent.futures
import hashlib
import gzip
import zlib
import html
import json
import re
import time
import urllib.parse
import urllib.request
from datetime import datetime
from html.parser import HTMLParser
from pathlib import Path
from zoneinfo import ZoneInfo

from jobscout.network import tls_context

HEADERS={'User-Agent':'Mozilla/5.0 (compatible; JobScout personal career research)','Accept':'application/json,text/html'}
ROLE=re.compile(r'战略分析|战略研究|商业研究|数据产品|数据|商业分析|经营分析|业务分析|产品分析|用户分析|增长分析|风控|风险|信用|金融科技|数字金融|金融工程|宏观|策略研究|固收研究|基金评价|投资分析|投研|量化|\bBI\b|analytics|data analyst|business analyst',re.I)
EXCLUDE=re.compile(r'销售|柜员|客户经理|理财经理|营销经理|总监|首席|负责人|资深|专家|行政|人事|法务|合规专员|客户服务',re.I)
FIELDS=['JobAdId','JobAdName','Category','LocId','Salary','Duty','Require','PostDate','EndTime','Degree','YearsOfWorking','ClassificationOne','ClassificationTwo','Org','HeadCount']


def read(url,body=None):
    data=json.dumps(body,ensure_ascii=False).encode() if body is not None else None
    req=urllib.request.Request(url,data=data,headers={**HEADERS,**({'Content-Type':'application/json'} if data else {})})
    with urllib.request.urlopen(req,timeout=22,context=tls_context()) as r:
        raw=r.read(12*1024*1024+1)
        if len(raw)>12*1024*1024:raise ValueError('公开响应过大，已停止读取')
        encoding=r.headers.get('Content-Encoding','').lower()
        if encoding=='gzip' or raw.startswith(b'\x1f\x8b'):raw=gzip.decompress(raw)
        elif encoding=='deflate':raw=zlib.decompress(raw)
        if len(raw)>24*1024*1024:raise ValueError('解压后的响应过大')
        return raw.decode('utf-8-sig','replace')


def read_json(url,body=None):
    try:return json.loads(read(url,body))
    except json.JSONDecodeError:raise ValueError('未返回公开职位 JSON；可能需要人工访问') from None


def text(value):
    return re.sub(r'[ \t]+',' ',html.unescape(re.sub('<[^>]+>',' ',str(value or '')))).strip()


def date_value(value):
    s=str(value or '')
    m=re.search(r'(20\d{2})[-年/](\d{1,2})[-月/](\d{1,2})',s)
    if not m:return ''
    try:return datetime(*map(int,m.groups())).date().isoformat()
    except ValueError:return ''


def passed(deadline):
    return bool(deadline and deadline<datetime.now(ZoneInfo('Asia/Shanghai')).date().isoformat())


def relevant(job):
    title=job.get('title','')
    adjacent=bool(re.search(r'产品经理|产品运营|策略运营|用户运营|业务运营|经营管理|研究助理',title) and len(re.findall(r'数据分析|商业分析|经营分析|SQL|指标体系|数据看板',job.get('description',''),re.I))>=2)
    return bool((ROLE.search(title) or adjacent) and not EXCLUDE.search(title))


def zhiye(source):
    parsed=urllib.parse.urlsplit(source['url'])
    base=parsed.scheme+'://'+parsed.netloc
    raw=read(source['url'])
    m=re.search(r'var\s+BSGlobal\s*=\s*',raw)
    if not m:raise ValueError('不是新版公开招聘页，请使用旧版适配器或人工入口')
    config=json.JSONDecoder().raw_decode(raw[m.end():])[0]
    official=config.get('tenantInfo',{}).get('Alias','')
    if source.get('brand') and source['brand'] not in official:raise ValueError('官网企业名称与配置不符，未导入')
    jobs=[];seen=set();count=0;complete=False
    for page in range(10):
        body={'PageIndex':page,'PageSize':100,'KeyWords':'','SpecialType':0,'PortalId':config['PortalId'],'DisplayFields':FIELDS}
        response=read_json(base+'/api/Jobad/GetJobAdPageList',body)
        if response.get('Code')!=200 or not isinstance(response.get('Data'),list):raise ValueError('公开职位接口返回异常')
        count=int(response.get('Count') or 0)
        rows=response['Data']
        for r in rows:
            ident=str(r.get('Id') or '')
            if not ident or ident in seen:continue
            seen.add(ident)
            locs=r.get('LocNames') or []
            loc=' / '.join(str(x.get('Name') or x.get('Text') or '') if isinstance(x,dict) else str(x) for x in locs)
            category=r.get('Category') or ''
            detail_path='/campus/detail' if str(r.get('CategoryId'))=='2' or '校园' in category else '/intern/detail' if str(r.get('CategoryId'))=='3' or '实习' in category else '/social/detail'
            custom=re.search(r'"'+re.escape(detail_path)+r'"\s*:\s*"([^\"]+)"',config.get('CustomRouteRule') or '')
            detail_url=base+(custom.group(1).replace('${jobAdId}',urllib.parse.quote(ident)) if custom else detail_path+'?'+urllib.parse.urlencode({'jobAdId':ident}))
            description='招聘类别：'+category+'\n工作职责：\n'+text(r.get('Duty'))+'\n任职资格：\n'+text(r.get('Require'))
            if r.get('YearsOfWorking'):description+='\n工作年限：'+text(r['YearsOfWorking'])
            deadline=date_value(r.get('EndTime'))
            if deadline:description+='\n官网截止日期：'+deadline
            job={'source_key':ident,'title':text(r.get('JobAdName')),'location':loc,'description':description,'posted':date_value(r.get('PostDate')) or date_value(r.get('ChangeDate')),'deadline':deadline,
                 'url':detail_url,'category':category,'is_open':0 if passed(deadline) or r.get('Status')==2 else 1}
            jobs.append(job)
        if not rows or len(seen)>=count:complete=True;break
        time.sleep(.15)
    if not complete:raise ValueError('职位分页达到限制，未把不完整响应当作成功扫描')
    return {'jobs':jobs,'seen':len(jobs),'complete':True,'official_name':official}


class PublicHTML(HTMLParser):
    def __init__(self):
        super().__init__();self.skip=0;self.parts=[];self.links=[];self.href=None;self.anchor=[]
    def handle_starttag(self,tag,attrs):
        if tag in ['script','style','noscript']:self.skip+=1
        if self.skip:return
        if tag in ['p','div','li','br','h1','h2','h3','tr','dt','dd']:self.parts.append('\n')
        if tag=='a':self.href=dict(attrs).get('href');self.anchor=[]
    def handle_data(self,data):
        if self.skip:return
        self.parts.append(data)
        if self.href is not None:self.anchor.append(data)
    def handle_endtag(self,tag):
        if tag in ['script','style','noscript']:
            self.skip=max(0,self.skip-1);return
        if self.skip:return
        if tag=='a' and self.href is not None:self.links.append((self.href,''.join(self.anchor).strip()));self.href=None
        if tag in ['p','div','li','h1','h2','h3','tr','dt','dd']:self.parts.append('\n')
    def plain(self):return re.sub(r'\n\s*\n+','\n',''.join(self.parts)).strip()


def zhiye_legacy(source):
    jobs=[];seen=set();next_url=source['url'];base=urllib.parse.urlsplit(next_url)
    for page in range(5):
        parser=PublicHTML();parser.feed(read(next_url))
        for href,title in parser.links:
            if not re.search(r'zpdetail|campusxq|jobId=',href,re.I) or not title or title in ['查看','详情','申请','立即申请','立即投递']:continue
            url=urllib.parse.urljoin(next_url,href)
            if urllib.parse.urlsplit(url).hostname!=base.hostname or url in seen:continue
            seen.add(url)
            if not ROLE.search(title) or EXCLUDE.search(title):continue
            detail=PublicHTML();detail.feed(read(url));plain=detail.plain()
            pos=re.search(r'工作职责|岗位职责',plain)
            if not pos or len(plain[pos.start():])<80:continue
            description=plain[max(0,pos.start()-180):]
            loc=re.search(r'工作地点[：:]?\s*([^\n]{1,60})',plain)
            end=re.search(r'截止(?:时间|日期)[：:]?\s*([^\n]{1,30})',plain)
            posted=re.search(r'发布时间[：:]?\s*([^\n]{1,30})',plain)
            deadline=date_value(end.group(1) if end else '')
            jobs.append({'source_key':url,'title':title,'location':loc.group(1).strip() if loc else '',
                         'description':description,'url':url,'posted':date_value(posted.group(1) if posted else ''),'deadline':deadline,'category':'校招 / 实习（以原文为准）','is_open':0 if passed(deadline) else 1})
            time.sleep(.12)
        next_link=next((href for href,title in parser.links if '下一页' in title and href and not href.startswith(('#','javascript'))),None)
        if not next_link:break
        next_url=urllib.parse.urljoin(next_url,next_link)
    if not seen:raise ValueError('公开列表没有可识别的职位链接，保留人工入口')
    return {'jobs':jobs,'seen':len(seen),'complete':False,'official_name':source['name']}


def tencent(source):
    base='https://careers.tencent.com/tencentcareer/api/post/'
    jobs={};count=0
    for keyword in ['数据分析','商业分析','经营分析','风险','产品分析']:
        for page in range(1,5):
            params={'timestamp':int(time.time()*1000),'countryId':'1','cityId':'','bgIds':'','productId':'','categoryId':'','parentCategoryId':'','attrId':'','keyword':keyword,'pageIndex':page,'pageSize':50,'language':'zh-cn','area':'cn'}
            response=read_json(base+'Query?'+urllib.parse.urlencode(params))
            if response.get('Code')!=200:raise ValueError('腾讯公开职位接口返回异常')
            data=response.get('Data') or {};rows=data.get('Posts') or [];count+=len(rows)
            for row in rows:
                title=row.get('RecruitPostName','');ident=str(row.get('PostId') or '')
                if not ident or ident in jobs or not ROLE.search(title) or EXCLUDE.search(title):continue
                years=row.get('RequireWorkYearsName','')
                # Retain experienced roles only if they are not an explicit 3+ year requirement.
                if re.search(r'[三四五六七八九十3-9].*年',years):continue
                detail=read_json(base+'ByPostId?'+urllib.parse.urlencode({'timestamp':int(time.time()*1000),'postId':ident,'language':'zh-cn'}))
                if detail.get('Code')!=200:continue
                d=detail.get('Data') or {}
                if not d.get('Requirement'):continue
                description='工作职责：\n'+text(d.get('Responsibility') or row.get('Responsibility'))+'\n任职要求：\n'+text(d.get('Requirement'))+'\n工作年限：'+years
                jobs[ident]={'source_key':ident,'title':title,'location':row.get('LocationName',''),'url':'https://careers.tencent.com/jobdesc.html?postId='+ident,
                            'description':description,'posted':date_value(row.get('LastUpdateTime')),'deadline':'','category':'以原文岗位类型为准','is_open':1}
                time.sleep(.12)
            if not rows or page*50>=int(data.get('Count') or 0):break
            time.sleep(.15)
    return {'jobs':list(jobs.values()),'seen':count,'complete':False,'official_name':'腾讯'}


def global_ats(source):
    from jobscout import ats
    mainland=re.compile(r'北京|上海|杭州|深圳|广州|成都|南京|苏州|武汉|西安|天津|重庆|合肥|长沙|\b(beijing|shanghai|hangzhou|shenzhen|guangzhou|chengdu|nanjing|suzhou|wuhan|xian|tianjin|chongqing|china|mainland)\b',re.I)
    jobs=[];seen=0
    for row in ats.FETCHERS[source['ats_kind']](source['slug'],ats.fetch_json):
        seen+=1
        if not mainland.search(row['location']) or re.search(r'hong kong|香港|taiwan|台湾|taipei|台北',row['location'],re.I):continue
        jobs.append({**row,'source_key':row['id'],'category':'以官网任职要求为准','deadline':'','is_open':1})
    return {'jobs':jobs,'seen':seen,'complete':True,'official_name':source['name']}


def baidu_public(source):
    # Public server-rendered search pages contain full JD data. The direct API needs
    # authorization, so it is deliberately not used. Only the first visible page of
    # each search is collected; this partial feed must never close unseen jobs.
    jobs={};seen=set()
    for kind,project in [('GRADUATE','1'),('INTERN','-1')]:
        for keyword in ['数据','商业分析','经营分析','风险','产品运营','策略']:
            url=source['url']+'?'+urllib.parse.urlencode({'projectType':project,'recruitType':kind,'search':keyword})
            raw=read(url)
            marker=re.search(r'window\.__INITIAL_DATA__\s*=\s*',raw)
            if not marker:raise ValueError('公开页面未返回可读取的职位资料，需人工查看')
            # JSON-shaped hydration data may use the JS undefined literal.
            payload=re.sub(r'(?<=[,:])undefined(?=[,}])','null',raw[marker.end():])
            state=json.JSONDecoder().raw_decode(payload)[0]
            data=state.get('listData') or {}
            if data.get('keyWord')!=keyword:raise ValueError('官网未应用关键词，未把重复首屏当作完整搜索')
            for row in data.get('listDetailData',[]):
                key=row.get('postId');title=row.get('name') or ''
                if not key:continue
                seen.add(key)
                if key in jobs or not relevant({'title':title}):continue
                jobs[key]={'source_key':key,'title':title,'location':row.get('workPlace') or '',
                  'url':'https://talent.baidu.com/jobs/detail/'+kind+'/'+urllib.parse.quote(key),
                  'description':'招聘项目：'+text(row.get('projectType'))+'\n工作职责：\n'+text(row.get('workContent'))+'\n任职资格：\n'+text(row.get('serviceCondition'))+'\n工作年限：'+text(row.get('workYears')),
                  'posted':date_value(row.get('updateDate')) or date_value(row.get('publishDate')),'deadline':'',
                  'category':'校园招聘' if kind=='GRADUATE' else '日常实习','is_open':1}
            time.sleep(.2)
    return {'jobs':list(jobs.values()),'seen':len(seen),'complete':False,'official_name':'百度（公开搜索页部分采集）'}


from portal_sources import alibaba,jd,xiaohongshu,meituan,youdao,public_browser,antgroup

ADAPTERS={'zhiye':zhiye,'zhiye_legacy':zhiye_legacy,'tencent':tencent,'global_ats':global_ats,'baidu_public':baidu_public,'alibaba':alibaba,'jd':jd,'xiaohongshu':xiaohongshu,'meituan':meituan,'youdao':youdao,'public_browser':public_browser,'antgroup':antgroup}


def fetch_source(source):
    if source.get('adapter') not in ADAPTERS:
        return {'source':source,'ok':False,'status':'manual','error':source.get('reason','当前需从官网人工查看')}
    try:
        result=ADAPTERS[source['adapter']](source)
        return {'source':source,'ok':True,**result}
    except Exception as e:
        return {'source':source,'ok':False,'status':'error','error':str(e)}


def source_config(root):
    path=Path(root)/'config/china_sources.json'
    return json.loads(path.read_text()) if path.exists() else []


def scan(root,connection,analyze,profile,progress=lambda *args:None):
    sources=source_config(root)
    stats={'market':'cn','configured':len(sources),'companies':0,'manual':0,'seen':0,'kept':0,'new':0,'errors':[],'company_results':[]}
    now=datetime.now(ZoneInfo('UTC')).isoformat(timespec='seconds')
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        futures={pool.submit(fetch_source,s):s for s in sources}
        for index,future in enumerate(concurrent.futures.as_completed(futures)):
            result=future.result();s=result['source'];health={'id':s['id'],'company':s['name'],'sector':s['sector'],'checked_at':now,'ok':result['ok']}
            progress('国内采集：'+s['name'],index+1,len(sources))
            if not result['ok']:
                health.update(status=result['status'],error=result['error'],seen=0,new=0)
                if result['status']=='manual':stats['manual']+=1
                else:stats['errors'].append(s['name']+'：'+result['error'])
                stats['company_results'].append(health);continue
            observed_at=result.get('snapshot_at') or now
            stats['companies']+=0 if result.get('snapshot_at') else 1;stats['browser_snapshots']=stats.get('browser_snapshots',0)+(1 if result.get('snapshot_at') else 0);stats['seen']+=result['seen'];new_count=kept=0
            with connection() as con:
                identifiers=[]
                for job in result['jobs']:
                    ident='cn:auto:'+s['id']+':'+hashlib.sha256(job['source_key'].encode()).hexdigest()[:20]
                    identifiers.append(ident)
                    existing=con.execute('SELECT id,description FROM jobs WHERE id=?',(ident,)).fetchone()
                    if not relevant(job) and not existing:continue
                    kept+=1
                    if existing:
                        con.execute('UPDATE jobs SET title=?,location=?,description=?,url=?,posted=?,last_seen=?,is_open=?,deadline=?,sector=?,source_id=?,category=? WHERE id=?',
                                    (job['title'],job['location'],job['description'],job['url'],job['posted'],observed_at,job['is_open'],job['deadline'],s['sector'],s['id'],job['category'],ident))
                    else:
                        con.execute('INSERT INTO jobs(id,company,ats,title,location,url,description,posted,first_seen,last_seen,market,is_open,deadline,sector,source_id,category) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
                                    (ident,s['name'],'cn-'+s['adapter'],job['title'],job['location'],job['url'],job['description'],job['posted'],now,observed_at,'cn',job['is_open'],job['deadline'],s['sector'],s['id'],job['category']))
                        new_count+=1
                    row=dict(con.execute('SELECT * FROM jobs WHERE id=?',(ident,)).fetchone())
                    score=analyze(row,profile)
                    old=con.execute('SELECT method,detail FROM scores WHERE job_id=?',(ident,)).fetchone()
                    preserve=False
                    if existing and old and old['method']=='llm' and existing['description']==job['description']:
                        previous=json.loads(old['detail'] or '{}')
                        preserve=all(previous.get(k)==score.get(k) for k in ['profile_hash','rules_version','goal'])
                    if not preserve:con.execute('INSERT OR REPLACE INTO scores VALUES(?,?,?,?,?,?)',(ident,score['score'],score['verdict'],json.dumps(score,ensure_ascii=False),score['method'],now))
                if result.get('complete'):
                    for row in con.execute('SELECT id FROM jobs WHERE source_id=? AND market=\'cn\'',(s['id'],)):
                        if row['id'] not in identifiers:con.execute('UPDATE jobs SET is_open=0 WHERE id=?',(row['id'],))
            stats['kept']+=kept;stats['new']+=new_count
            health.update(status='ok',seen=result['seen'],kept=kept,new=new_count,complete=result.get('complete',False),official_name=result.get('official_name'))
            if result.get('snapshot_at'):health.update(status='browser_snapshot',checked_at=result['snapshot_at'],snapshot_at=result['snapshot_at'])
            stats['company_results'].append(health)
    return stats
