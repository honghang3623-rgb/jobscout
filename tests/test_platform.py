import csv
import json
import os
import shutil
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path
from unittest.mock import patch

import platform_core as core
import server
from jobscout import ats, h1b


class PlatformTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.original_root,self.original_db,self.original_cwd=core.ROOT,core.DB,Path.cwd()
        core.ROOT=Path(self.temp.name)
        core.DB=core.ROOT/'data/test.db'
        shutil.copytree(self.original_root/'config',core.ROOT/'config')
        shutil.copy(self.original_root/'profile.md',core.ROOT/'profile.md')
        os.chdir(core.ROOT)
        core.initialize()

    def tearDown(self):
        os.chdir(self.original_cwd)
        core.ROOT,core.DB=self.original_root,self.original_db
        self.temp.cleanup()

    def example(self,**changes):
        return dict(company='Example',title='Data Analyst',description='Use SQL, Python, Tableau and dashboard analytics. '+('Analyze product data. '*6),location='New York, NY',url='https://example.com/jobs/1',**changes)

    def test_negative_skills_and_foreign_location(self):
        p='技能：SQL、Python、Excel\n缺口：没有 Tableau / Looker / Power BI 的明确使用经历'
        result=core.assess(self.example(),p)
        self.assertIn('sql',result['matched'])
        self.assertIn('tableau',result['gaps'])
        self.assertNotIn('tableau',result['matched'])
        j=self.example();j['location']='Remote - Luxembourg'
        result=core.assess(j,p)
        self.assertLessEqual(result['score'],40)
        self.assertTrue(any(x['status']=='不符合' and x['item']=='工作地点' for x in result['hard']))

    def test_california_internship_soft_preference_and_fulltime(self):
        from market_rules import preference
        prefs=core.preferences();prefs['intern_region']='california';core.save_preferences(prefs)
        ca=self.example();ca.update(title='Data Analyst Intern',location='San Diego, CA')
        ny={**ca,'location':'New York, NY'}
        fulltime={**ny,'title':'Data Analyst'}
        self.assertTrue(preference(ca,core.preferences())['preferred'])
        self.assertFalse(preference(ny,core.preferences())['preferred'])
        self.assertFalse(preference(fulltime,core.preferences())['preferred'])
        result=core.assess(ny,'SQL Python','实习和全职都看')
        self.assertFalse(any(h['status']=='不符合' and h['item']=='实习地点偏好' for h in result['hard']))
        self.assertFalse(any(h['status']=='不符合' for h in core.assess(fulltime,'SQL Python','实习和全职都看')['hard']))

    def test_china_market_language_profile_and_independent_records(self):
        (core.ROOT/'profile_cn.md').write_text('技能：SQL、Python、数据分析、Excel\n实习：使用 SQL 开发 BI 看板，参与数据分析。')
        job=self.example();job.update(market='cn',company='示例公司',title='数据分析实习生',location='上海',description='岗位职责：使用 SQL 和 Python 分析业务数据，使用 Excel 整理业务指标，搭建 BI 看板。任职要求：在校生，具备数据分析和统计知识，实习到岗日期面议，每周至少三天。')
        cn=core.add_job(job);us=core.add_job(self.example())
        detail=core.detail(cn['id'])
        self.assertEqual(detail['market'],'cn')
        self.assertEqual(detail['analysis']['resume'],'中文数据分析版')
        self.assertIn('SQL',detail['analysis']['matched'])
        self.assertFalse(any(h['item']=='工作授权' for h in detail['analysis']['hard']))
        self.assertFalse(detail['stale'])
        self.assertIsNone(detail['h1b'])
        self.assertEqual(core.detail(us['id'])['market'],'us')
        self.assertEqual(len(core.state()['jobs']),2)
        (core.ROOT/'profile_cn.md').write_text('国内资料变更：SQL Python Excel 数据分析')
        self.assertTrue(core.detail(cn['id'])['stale'])
        self.assertFalse(core.detail(us['id'])['stale'])
        self.assertEqual(len([j for j in core.state()['jobs'] if j['market']=='cn']),1)

    def test_domestic_experience_and_quant_stretch(self):
        j=self.example();j.update(market='cn',title='数据分析师',location='上海',description='任职要求：\n1. 具有五年以上游戏行业数据分析经验，熟悉 SQL 和 Python。')
        r=core.assess(j,'技能：SQL Python 数据分析','实习和全职都看')
        self.assertLessEqual(r['score'],40)
        self.assertTrue(any(h['item']=='经验要求' and h['status']=='不符合' for h in r['hard']))
        j.update(title='量化研究实习生',description='任职要求：具备 SQL Python 统计建模能力；有3年相关经验者优先。')
        r=core.assess(j,'技能：SQL Python 统计建模','实习和全职都看')
        self.assertEqual(r['match_tier'],'stretch')
        self.assertLessEqual(r['score'],55)
        self.assertFalse(any(h['item']=='经验要求' and h['status']=='不符合' for h in r['hard']))

    def test_public_zhiye_pagination_and_expiry(self):
        import china_sources as sources
        html='var BSGlobal = '+json.dumps({'PortalId':'public-portal','tenantInfo':{'Alias':'测试银行'}})+';'
        row={'Id':'public-id','JobAdName':'数据分析岗','Category':'校园招聘','LocNames':['上海市'],'Duty':'使用 SQL 分析业务','Require':'2027 届，熟悉 Python','PostDate':'2026-10-01T00:00:00','EndTime':'2020-01-01T00:00:00','Status':1}
        responses=[{'Code':200,'Count':2,'Data':[row]},{'Code':200,'Count':2,'Data':[{**row,'Id':'second','EndTime':'2099-01-01'}]}]
        with patch.object(sources,'read',return_value=html),patch.object(sources,'read_json',side_effect=responses):
            result=sources.zhiye({'name':'测试银行','url':'https://test.zhiye.com/campus/jobs','brand':'测试银行'})
        self.assertTrue(result['complete'])
        self.assertEqual(result['seen'],2)
        self.assertEqual(result['jobs'][0]['is_open'],0)
        self.assertEqual(result['jobs'][1]['is_open'],1)
        self.assertIn('任职资格',result['jobs'][0]['description'])
        self.assertIn('jobAdId=public-id',result['jobs'][0]['url'])

    def test_domestic_scan_dedup_and_keeps_application_state(self):
        import china_sources as sources
        config=[{'id':'bank','name':'测试银行','sector':'银行','adapter':'zhiye','url':'https://test.zhiye.com/campus/jobs'}]
        (core.ROOT/'config/china_sources.json').write_text(json.dumps(config))
        job={'source_key':'1','title':'数据分析岗','location':'上海','description':'任职资格：2027 届，熟悉 SQL Python 数据分析。','url':'https://test.zhiye.com/campus/detail?jobAdId=1','posted':'2026-10-01','deadline':'','category':'校园招聘','is_open':1}
        fetched={'source':config[0],'ok':True,'seen':1,'complete':True,'jobs':[job]}
        analyze=lambda j,p:core.assess(j,p,'实习和全职都看')
        with patch.object(sources,'fetch_source',return_value=fetched):
            first=sources.scan(core.ROOT,core.connect,analyze,'技能：SQL Python 数据分析')
            self.assertEqual(first['new'],1)
            ident=core.state()['jobs'][0]['id']
            core.update_job({'id':ident,'status':'applied','notes':'Keep this note'})
            second=sources.scan(core.ROOT,core.connect,analyze,'技能：SQL Python 数据分析')
        self.assertEqual(second['new'],0)
        self.assertEqual(core.detail(ident)['status'],'applied')
        self.assertEqual(core.detail(ident)['notes'],'Keep this note')
        with patch.object(sources,'fetch_source',return_value={**fetched,'seen':0,'jobs':[],'complete':False}):
            sources.scan(core.ROOT,core.connect,analyze,'技能：SQL Python')
        self.assertEqual(core.detail(ident)['is_open'],1)
        with patch.object(sources,'fetch_source',return_value={**fetched,'seen':0,'jobs':[],'complete':True}):
            sources.scan(core.ROOT,core.connect,analyze,'技能：SQL Python')
        self.assertEqual(core.detail(ident)['is_open'],0)

    def test_seniority_experience_and_goal(self):
        j=self.example();j['title']='Data Analytics Leader'
        self.assertLessEqual(core.assess(j,'SQL Python')['score'],40)
        j=self.example();j['description']+=' Minimum 5+ years of professional experience.'
        self.assertTrue(any(x['item']=='经验要求' and x['status']=='不符合' for x in core.assess(j,'SQL Python')['hard']))
        j=self.example();j['title']='Data Analyst Intern'
        self.assertLessEqual(core.assess(j,'SQL Python','2027 毕业后全职')['score'],40)

    def test_job_dedup_persistence_notes_and_events(self):
        first=core.add_job(self.example())
        duplicate=core.add_job(self.example())
        self.assertEqual(first['id'],duplicate['id'])
        self.assertTrue(duplicate['existing'])
        core.update_job({'id':first['id'],'status':'shortlist','notes':'Check graduation date'})
        detail=core.detail(first['id'])
        self.assertEqual(detail['notes'],'Check graduation date')
        self.assertEqual(detail['status'],'shortlist')
        self.assertEqual(len(core.state()['events']),1)
        with self.assertRaises(ValueError):
            core.update_job({'id':first['id'],'status':'invented'})
        self.assertNotIn('csrf',core.state())

    def test_profile_change_marks_results_stale(self):
        job=core.add_job(self.example())
        self.assertFalse(core.detail(job['id'])['stale'])
        (core.ROOT/'profile.md').write_text('New profile SQL Python analytics')
        self.assertTrue(core.detail(job['id'])['stale'])

    def test_lca_is_distinct_and_strict_h1b_only(self):
        path=core.ROOT/'records.csv'
        with path.open('w',newline='') as f:
            w=csv.writer(f)
            w.writerow(['EMPLOYER_NAME','CASE_STATUS','VISA_CLASS','TOTAL_WORKER_POSITIONS','PW_WAGE_LEVEL'])
            w.writerows([['Example Inc','CERTIFIED','H-1B',2,'III'],['Example Inc','CERTIFIED','H-1B1',20,'IV'],['Example Inc','CERTIFIED-WITHDRAWN','H-1B',5,'I']])
        with core.connect() as con:
            self.assertEqual(h1b.import_lca(con,path,'2025'),1)
            info=core.employer_info(con,'Example',[{'name':'Example','h1b_names':['Example Inc']}])
            self.assertEqual(info['rows'][0]['count'],2)
            self.assertEqual(info['rows'][0]['source'],'lca')
            self.assertIsNone(core.employer_info(con,'Example Labs',[]))

    def test_uscis_initial_and_continuing_totals(self):
        path=core.ROOT/'uscis.csv'
        path.write_text('Employer,Fiscal Year,Initial Approvals,Continuing Approvals\nExample Inc,2025,3,5\n')
        with core.connect() as con:
            h1b.import_uscis(con,path,'2025')
            info=core.employer_info(con,'Example',[])
        self.assertEqual(info['rows'][0]['source'],'uscis')
        self.assertEqual(info['rows'][0]['count'],8)
        self.assertEqual(info['rows'][0]['extra'],3)

    def test_xlsx_import_and_online_status(self):
        import openpyxl
        path=core.ROOT/'records.xlsx'
        wb=openpyxl.Workbook();ws=wb.active
        ws.append(['EMPLOYER_NAME','CASE_STATUS','VISA_CLASS','TOTAL_WORKER_POSITIONS'])
        ws.append(['Example Inc','CERTIFIED','H-1B',4])
        wb.save(path);wb.close()
        with core.connect() as con:
            self.assertEqual(h1b.import_lca(con,path,'2026'),1)
            self.assertEqual(con.execute('SELECT count FROM h1b').fetchone()[0],4)
            cfg,_,_=core.load()
            comps=[{'name':'Example','ats':'greenhouse','slug':'example'}]
            fixture={'jobs':[{'id':1,'title':'Data Analyst','location':{'name':'New York, NY'},'content':'SQL'}]}
            ats.scan(con,comps,cfg,fetch=lambda _:fixture,sleep=0)
            self.assertEqual(con.execute('SELECT is_open FROM jobs').fetchone()[0],1)
            ats.scan(con,comps,cfg,fetch=lambda _: {'jobs':[]},sleep=0)
            self.assertEqual(con.execute('SELECT is_open FROM jobs').fetchone()[0],0)
            ats.scan(con,comps,cfg,fetch=lambda _:fixture,sleep=0)
            self.assertEqual(con.execute('SELECT is_open FROM jobs').fetchone()[0],1)

    def test_ats_update_preserves_application_and_refreshes_jd(self):
        cfg,_,_=core.load()
        fixture={'jobs':[{'id':1,'title':'Data Analyst','location':{'name':'New York, NY'},'absolute_url':'https://example.com/1','content':'SQL Python dashboards'}]}
        comps=[{'name':'Example','ats':'greenhouse','slug':'example'}]
        with core.connect() as con:
            ats.scan(con,comps,cfg,fetch=lambda _:fixture,sleep=0)
            con.execute("UPDATE jobs SET status='applied',notes='Keep' WHERE id='gh:example:1'")
            con.execute("INSERT INTO scores(job_id,score) VALUES('gh:example:1',80)")
            con.commit()
            fixture['jobs'][0]['content']='SQL Python dashboards updated'
            ats.scan(con,comps,cfg,fetch=lambda _:fixture,sleep=0)
            row=con.execute('SELECT * FROM jobs').fetchone()
            self.assertEqual(row['status'],'applied')
            self.assertEqual(row['notes'],'Keep')
            self.assertIn('updated',row['description'])
            self.assertEqual(con.execute('SELECT COUNT(*) FROM scores').fetchone()[0],0)

    def test_lever_includes_requirements_lists(self):
        fixture=[{'id':'1','text':'Data Analyst','descriptionPlain':'Overview','lists':[{'text':'Requirements','content':'<li>SQL and Python required</li>'}],'additionalPlain':'No sponsorship'}]
        job=list(ats.lever('example',lambda _:fixture))[0]
        self.assertIn('SQL and Python required',job['description'])
        self.assertIn('No sponsorship',job['description'])

    def test_malformed_ai_is_rejected(self):
        for score in [float('nan'),120,-1,True]:
            with self.assertRaises(ValueError):core.validate_ai({'score':score})
        with self.assertRaises(ValueError):core.validate_ai({'score':80,'hard':['invalid']})
        with self.assertRaises(ValueError):core.validate_ai({'score':80,'matched':{'sql':'yes'}})

    def test_http_csrf_invalid_input_export_and_persistence(self):
        http=server.ThreadingHTTPServer(('127.0.0.1',0),server.Handler)
        thread=threading.Thread(target=http.serve_forever,daemon=True);thread.start()
        base='http://127.0.0.1:'+str(http.server_port)
        def post(path,data,token=server.TOKEN):
            req=urllib.request.Request(base+path,data=json.dumps(data).encode(),headers={'Content-Type':'application/json','X-JobScout-Token':token})
            with urllib.request.urlopen(req) as r:return json.load(r)
        try:
            with urllib.request.urlopen(base+'/api/state') as r:
                state=json.load(r)
            self.assertEqual(state['csrf'],server.TOKEN)
            self.assertNotIn('api_key',json.dumps(state))
            with self.assertRaises(urllib.error.HTTPError) as exc:post('/api/jobs/add',self.example(),token='wrong')
            self.assertEqual(exc.exception.code,403)
            with self.assertRaises(urllib.error.HTTPError):post('/api/jobs/add',{'company':'bad'})
            added=post('/api/jobs/add',self.example())
            post('/api/jobs/update',{'id':added['id'],'status':'interview','notes':'=malicious()'})
            with urllib.request.urlopen(base+'/api/export') as r:
                contents=r.read().decode('utf-8-sig')
            self.assertIn("'=malicious()",contents)
            self.assertIn('interview',contents)
            post('/api/companies',{'companies':[{'name':'Example','ats':'lever','slug':'example','h1b_names':'Example Inc; Example LLC'}]})
            self.assertEqual(core.load()[1][0]['h1b_names'],['Example Inc','Example LLC'])
        finally:
            http.shutdown();http.server_close();thread.join()


if __name__=='__main__':unittest.main()
