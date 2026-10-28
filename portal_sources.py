"""Public employer feeds used by the重点公司 board. No account credentials stored."""
import http.cookiejar
import json
import re
import time
import urllib.parse
import urllib.request
from datetime import datetime,timezone
from jobscout.network import tls_context

class PublicSession:
    def __init__(self,base):
        self.base=base.rstrip('/')
        self.opener=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()),urllib.request.HTTPSHandler(context=tls_context()))
    def request(self,path,body=None,headers=None):
        req=urllib.request.Request(self.base+path,data=json.dumps(body,ensure_ascii=False).encode() if body is not None else None,
          headers={'User-Agent':'Mozilla/5.0','Accept':'application/json,text/html','Referer':self.base+'/',**({'Content-Type':'application/json'} if body is not None else {}),**(headers or {})})
        with self.opener.open(req,timeout=22) as response:
            raw=response.read(12*1024*1024+1)
            if len(raw)>12*1024*1024:raise ValueError('公开响应超过安全读取上限')
            return raw.decode('utf-8-sig','replace')
    def json(self,path,body=None):return json.loads(self.request(path,body))


def timestamp(value):
    try:return datetime.fromtimestamp(float(value)/1000,timezone.utc).date().isoformat() if value else ''
    except (ValueError,TypeError,OverflowError):return ''


def alibaba(source):
    import china_sources as c
    session=PublicSession(source.get('url','https://campus-talent.alibaba.com/'))
    raw=session.request('/')
    token=re.search(r'__token__\s*:\s*"([^\"]+)"',raw)
    if not token:raise ValueError('官网未提供正常访客会话参数，需要人工查看')
    def query(path,body):
        response=session.json(path+'?'+urllib.parse.urlencode({'_csrf':token.group(1)}),body)
        if response.get('relogin'):raise ValueError('官网明确要求登录后读取')
        if not response.get('success'):raise ValueError(response.get('errorMsg') or '官网公开列表读取失败')
        return response.get('content') or {}
    groups=query('/searchCondition/listBatch',{})
    batches=[b for key in ['graduate','internship'] for b in groups.get(key,[]) if isinstance(b,dict) and b.get('id')]
    if not batches:raise ValueError('官网未列出当前校招或实习批次')
    jobs={};seen=set()
    for batch in batches:
        ids=set()
        for page in range(1,21):
            data=query('/position/search',{'batchId':batch['id'],'pageIndex':page,'pageSize':100,'channel':'new_campus_group_official_site','language':'zh'})
            rows=data.get('datas') or [];total=int(data.get('totalCount') or 0)
            if not isinstance(rows,list):raise ValueError('阿里职位列表结构发生变化')
            new=[r for r in rows if str(r.get('id')) not in ids]
            if rows and not new:raise ValueError('阿里分页未前进，未把重复页面视为完整采集')
            for row in new:
                ident=str(row.get('id') or '')
                if not ident:continue
                ids.add(ident);seen.add(ident)
                title=c.text(row.get('name'))
                if not c.relevant({'title':title,'description':c.text(row.get('description'))+' '+c.text(row.get('requirement'))}):continue
                business=' / '.join(row.get('circleNames') or [])
                graduation=row.get('graduationTime') or {}
                window=c.text(batch.get('remark')) or ' ~ '.join(filter(None,[timestamp(graduation.get('from')),timestamp(graduation.get('to'))]))
                description='招聘批次：'+c.text(batch.get('name'))+'\n业务范围（官网列示）：'+business+'\n毕业时间窗口：'+window+'\n岗位职责：\n'+c.text(row.get('description'))+'\n任职要求：\n'+c.text(row.get('requirement'))
                jobs[ident]={'source_key':ident,'title':title,'location':' / '.join(row.get('workLocations') or []),
                  'url':session.base+'/campus/position/'+urllib.parse.quote(ident), 'description':description,
                  'posted':timestamp(row.get('publishTime') or row.get('modifyTime')),'deadline':'',
                  'category':'校园招聘（2027届）' if batch in groups.get('graduate',[]) else c.text(batch.get('name')),
                  'is_open':0 if row.get('status') not in [None,'recruit','OPEN'] else 1}
            if not rows or len(ids)>=total:break
            if page==20:raise ValueError('阿里岗位超过分页上限，未将不完整列表作为全量结果')
            time.sleep(.15)
    return {'jobs':list(jobs.values()),'seen':len(seen),'complete':True,'official_name':'阿里巴巴集团官方校招 / 实习'}


def jd(source):
    import china_sources as c
    session=PublicSession(source.get('url','https://campus.jd.com'))
    session.request('/')
    jobs=[];seen=set()
    for kind,label in [('present','校园招聘'),('internship','日常 / 转正实习')]:
        ids=set()
        for page in range(30):
            response=session.json('/api/wx/position/page?type='+kind,{'pageSize':100,'pageIndex':page,'parameter':{'positionName':'','planIdList':[],'jobDirectionCodeList':[],'workCityCodeList':[],'positionDeptList':[]}})
            if response.get('success') is not True:raise ValueError('京东官网要求登录或公开查询返回异常')
            data=response.get('body') or {};rows=data.get('items') or [];total=int(data.get('totalNumber') or 0)
            if not isinstance(rows,list):raise ValueError('京东公开岗位结构变化')
            new=[r for r in rows if str(r.get('publishId')) not in ids]
            if rows and not new:raise ValueError('京东分页未前进，保留原岗位状态')
            for row in new:
                ident=str(row.get('publishId') or '')
                if not ident:continue
                ids.add(ident);seen.add(kind+':'+ident)
                if not c.relevant({'title':row.get('positionName',''),'description':c.text(row.get('workContent'))+' '+c.text(row.get('qualification'))}):continue
                reqs=row.get('requirementVoList') or []
                def values(field):return list(dict.fromkeys(c.text(r.get(field)) for r in reqs if r.get(field)))
                location=' / '.join(values('workCity')) or c.text(row.get('workCity') or row.get('address'))
                business=' / '.join(values('positionBg') or row.get('bgList') or [])
                description='招聘通道：'+label+'\n业务范围（官网列示）：'+business+'\n岗位职责：\n'+c.text(row.get('workContent'))+'\n任职要求：\n'+c.text(row.get('qualification'))
                jobs.append({'source_key':kind+':'+ident,'title':c.text(row.get('positionName')),'location':location,
                  'url':session.base+'/#/details?id='+urllib.parse.quote(ident),'description':description,
                  'posted':timestamp(row.get('publishTime')),'deadline':'','category':label,'is_open':1})
            if not rows or len(ids)>=total:break
            if page==29:raise ValueError('京东职位超过分页限制，未判定缺席岗位下架')
            time.sleep(.15)
    return {'jobs':jobs,'seen':len(seen),'complete':True,'official_name':'京东集团官方校招 / 实习'}


def xiaohongshu(source):
    import china_sources as c
    session=PublicSession(source.get('url','https://job.xiaohongshu.com'))
    session.request('/campus')
    jobs=[];ids=set()
    for page in range(1,31):
        response=session.json('/websiterecruit/position/pageQueryPosition',{'pageNum':page,'pageSize':100,'recruitType':'campus'})
        if response.get('success') is not True:raise ValueError(response.get('errorMsg') or '小红书公开职位读取失败，可能需登录')
        data=response.get('data') or {};rows=data.get('list') or [];total=int(data.get('total') or 0)
        new=[r for r in rows if str(r.get('positionId')) not in ids]
        if rows and not new:raise ValueError('小红书分页未前进，未将重复页面作为全量列表')
        for row in new:
            ident=str(row.get('positionId') or '')
            if not ident:continue
            ids.add(ident)
            description='招聘项目：'+c.text(row.get('jobProjectName'))+'\n岗位职责：\n'+c.text(row.get('duty'))+'\n任职要求：\n'+c.text(row.get('qualification'))
            job={'source_key':ident,'title':c.text(row.get('positionName')),'location':c.text(row.get('workplace')),
              'url':session.base+'/campus/position/'+urllib.parse.quote(ident),'description':description,
              'posted':c.date_value(row.get('publishTime')),'deadline':'','category':'校招 / 实习（以 JD 为准）',
              'is_open':1 if row.get('recruitStatus')=='in_recruitment' else 0}
            # This endpoint serves both campus and internship projects. Classify from
            # actual title / project evidence, never label every campus job an intern.
            job['category']='实习' if re.search(r'实习|intern',job['title']+' '+c.text(row.get('jobProjectName')),re.I) else '校园招聘'
            if c.relevant(job):jobs.append(job)
        if not rows or len(ids)>=total:break
        if page==30:raise ValueError('小红书职位超过分页上限')
        time.sleep(.15)
    return {'jobs':jobs,'seen':len(ids),'complete':True,'official_name':'小红书官方校园招聘 / 实习'}


def meituan(source):
    import china_sources as c
    session=PublicSession('https://zhaopin.meituan.com');jobs=[];ids=set()
    for page in range(1,61):
        response=session.json('/api/official/job/getJobList',{'page':{'pageNo':page,'pageSize':100},'jobShareType':'1','keywords':'','cityList':[],'department':[],'jfJgList':[],'jobType':[{'code':'1','subCode':[]},{'code':'2','subCode':[]}],'typeCode':[],'specialCode':[]})
        data=response.get('data') or {}
        if not isinstance(data.get('list'),list):raise ValueError('美团公开职位返回异常，未判定岗位下架')
        rows=data['list'];total=int((data.get('page') or {}).get('totalCount') or 0)
        fresh=[r for r in rows if str(r.get('jobUnionId')) not in ids]
        if rows and not fresh:raise ValueError('美团分页未前进')
        for row in fresh:
            ident=str(row.get('jobUnionId') or '')
            if not ident:continue
            ids.add(ident)
            description='岗位职责：\n'+c.text(row.get('jobDuty'))+'\n任职要求：\n'+c.text(row.get('jobRequirement'))+'\n其他信息：\n'+c.text(row.get('otherInfo'))
            job={'source_key':ident,'title':c.text(row.get('name')),'location':' / '.join(c.text(x.get('name')) for x in (row.get('cityList') or [])),
                'description':description,'url':session.base+'/web/position/detail?highlightType=campus&jobShareType=1&jobUnionId='+urllib.parse.quote(ident),
                'posted':timestamp(row.get('firstPostTime')),'deadline':timestamp(row.get('expiredTime')),'category':'实习' if str(row.get('jobType'))=='2' else '校园招聘','is_open':1}
            if c.relevant(job):jobs.append(job)
        if not rows or len(ids)>=total:break
        if page==60:raise ValueError('美团公开职位超过分页上限')
        time.sleep(.15)
    return {'jobs':jobs,'seen':len(ids),'complete':True,'official_name':'美团官方校招 / 实习'}


def youdao(source):
    import china_sources as c
    session=PublicSession('https://hr.163.com');jobs=[];ids=set()
    for page in range(1,61):
        response=session.json('/api/hr163/position/queryPage',{'currentPage':page,'pageSize':100})
        if response.get('code')!=200:raise ValueError('网易公开岗位查询失败')
        data=response.get('data') or {};rows=data.get('list') or [];total=int(data.get('total') or 0)
        fresh=[r for r in rows if str(r.get('id')) not in ids]
        if rows and not fresh:raise ValueError('网易分页未前进，保留已有职位状态')
        for row in fresh:
            ident=str(row.get('id') or '')
            if not ident:continue
            ids.add(ident)
            if '有道' not in str(row.get('productName','')):continue
            description='业务范围（官网列示）：'+c.text(row.get('productName'))+'\n学历：'+c.text(row.get('reqEducationName'))+'\n工作经验：'+c.text(row.get('reqWorkYearsName'))+'\n岗位职责：\n'+c.text(row.get('description'))+'\n任职要求：\n'+c.text(row.get('requirement'))
            job={'source_key':ident,'title':c.text(row.get('name')),'location':' / '.join(row.get('workPlaceNameList') or []),'description':description,
                'url':session.base+'/job-detail.html?id='+urllib.parse.quote(ident),'posted':timestamp(row.get('updateTime')),'deadline':'',
                'category':'实习' if re.search('实习',c.text(row.get('name'))) else '社会招聘（经验以 JD 为准）','is_open':1}
            if c.relevant(job):jobs.append(job)
        if not rows or len(ids)>=total:break
        if page==60:raise ValueError('网易公开职位超过分页上限')
        time.sleep(.15)
    return {'jobs':jobs,'seen':len(ids),'complete':True,'official_name':'网易招聘官网 · 有道业务'}


def public_browser(source):
    """Import only complete JDs read in the normal public browser, never imply a rescan."""
    import china_sources as c
    from pathlib import Path
    path=Path(__file__).resolve().parent/'data'/'bytedance-public-browser.json'
    data=json.loads(path.read_text());checked=datetime.fromisoformat(data['checked_at'].replace('Z','+00:00'))
    if (datetime.now(timezone.utc)-checked).total_seconds()>7*86400:
        raise ValueError('浏览器核实已超过 7 天，请重新查看官网；保留旧记录，不判断岗位下架')
    jobs=[]
    for row in data.get('jobs',[]):
        if not row.get('full_detail') or not c.relevant(row):continue
        job={k:c.text(row.get(k)) for k in ['source_key','title','location','url','posted','deadline','category']}
        job['description']='采集说明：官网浏览器核实，部分收录；核实时间 '+data['checked_at']+'。非每日接口更新。\n招聘批次：'+job['category']+'\n'+c.text(row.get('description'))
        job['is_open']=1;jobs.append(job)
    if not jobs:raise ValueError('尚无可核实的完整官网 JD，未导入列表摘要')
    return {'jobs':jobs,'seen':len(data.get('jobs',[])),'complete':False,'snapshot_at':data['checked_at'],'official_name':'字节跳动官网浏览器核实 · 部分收录'}


def antgroup(source):
    import china_sources as c
    from zoneinfo import ZoneInfo
    session=PublicSession('https://hrcareersweb.antgroup.com');jobs=[];ids=set()
    def cn_date(value):
        try:return datetime.fromisoformat(value.replace('Z','+00:00')).astimezone(ZoneInfo('Asia/Shanghai')).date().isoformat() if value else ''
        except (ValueError,TypeError,AttributeError):return ''
    # The official endpoint rejects pageSize=100. Its own public page uses 10.
    for page in range(1,101):
        response=session.json('/api/campus/position/search',{'channel':'campus_group_official_site','language':'zh','pageIndex':page,'pageSize':10,'recruitType':[],'batchIds':[]})
        if response.get('success') is not True:raise ValueError(response.get('errorMsg') or '蚂蚁公开职位读取失败')
        rows=response.get('content') or [];total=int(response.get('totalCount') or 0)
        if not isinstance(rows,list):raise ValueError('蚂蚁职位结构变化')
        fresh=[r for r in rows if str(r.get('id')) not in ids]
        if rows and not fresh:raise ValueError('蚂蚁分页未前进，未判断缺席职位下架')
        for row in fresh:
            ident=str(row.get('id') or '')
            if not ident:continue
            ids.add(ident);graduation=row.get('graduationTime') or {}
            window=' ~ '.join(filter(None,[cn_date(graduation.get('from')),cn_date(graduation.get('to'))]))
            description='招聘批次：'+c.text(row.get('batchName'))+'\n毕业时间窗口：'+window+'\n岗位职责：\n'+c.text(row.get('description'))+'\n任职要求：\n'+c.text(row.get('requirement'))
            job={'source_key':ident,'title':c.text(row.get('name')),'location':' / '.join(row.get('workLocations') or []),'description':description,
              'url':'https://talent.antgroup.com/campus-position?positionId='+urllib.parse.quote(ident),
              'posted':cn_date(row.get('publishTime')),'deadline':'','category':c.text(row.get('batchName')),'is_open':1}
            if c.relevant(job):jobs.append(job)
        if not rows or len(ids)>=total:break
        if page==100:raise ValueError('蚂蚁职位超过公开分页上限')
        time.sleep(.15)
    return {'jobs':jobs,'seen':len(ids),'complete':True,'official_name':'蚂蚁集团官方校招 / 实习'}
