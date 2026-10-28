import unittest
from unittest.mock import patch
import portal_sources as p

class EmployerFeedTests(unittest.TestCase):
 def test_alibaba_uses_official_batches_and_preserves_requirements(self):
  batches={'graduate':[{'id':'g','name':'2027届','remark':'2026-11-01 ~ 2027-10-31'}],'internship':[{'id':'i','name':'日常实习'}]}
  calls=[]
  def query(_,path,body=None):
   calls.append((path,body))
   if 'listBatch' in path:return {'success':True,'content':batches}
   return {'success':True,'content':{'datas':[{'id':body['batchId'],'name':'数据分析师','workLocations':['杭州','北京'],'circleNames':['示例业务线'],'description':'SQL 数据分析','requirement':'2027届本科及以上'}],'totalCount':1}}
  with patch.object(p.PublicSession,'request',return_value='__token__: "public-visitor"'),patch.object(p.PublicSession,'json',query),patch.object(p.time,'sleep'):
   result=p.alibaba({'url':'https://campus-talent.alibaba.com'})
  self.assertTrue(result['complete']);self.assertEqual(len(result['jobs']),2)
  self.assertIn('示例业务线',result['jobs'][0]['description']);self.assertIn('2027-10-31',result['jobs'][0]['description'])
  self.assertEqual(result['jobs'][0]['location'],'杭州 / 北京');self.assertIn('日常实习',result['jobs'][1]['category'])
  self.assertTrue(all('_csrf=' in x[0] for x in calls))
 def test_jd_repeated_page_raises_instead_of_closing_missing_jobs(self):
  response={'success':True,'body':{'items':[{'publishId':'1','positionName':'数据分析师'}],'totalNumber':200}}
  with patch.object(p.PublicSession,'request',return_value=''),patch.object(p.PublicSession,'json',return_value=response),patch.object(p.time,'sleep'):
   with self.assertRaisesRegex(ValueError,'分页未前进'):p.jd({})
 def test_xhs_feed_has_both_internships_and_graduate_jobs(self):
  response={'success':True,'data':{'total':2,'list':[{'positionId':1,'positionName':'数据分析实习生','workplace':'上海','duty':'SQL','qualification':'每周4天','recruitStatus':'in_recruitment'},{'positionId':2,'positionName':'数据分析师','jobProjectName':'2027校园招聘','qualification':'2027届','recruitStatus':'in_recruitment'}]}}
  with patch.object(p.PublicSession,'request',return_value=''),patch.object(p.PublicSession,'json',return_value=response):r=p.xiaohongshu({})
  self.assertEqual([j['category'] for j in r['jobs']],['实习','校园招聘']);self.assertIn('每周4天',r['jobs'][0]['description'])
 def test_meituan_handles_missing_city_and_preserves_actual_type(self):
  response={'data':{'page':{'totalCount':2},'list':[{'jobUnionId':'1','name':'数据分析师','cityList':None,'jobType':'1','jobRequirement':'2027届'},{'jobUnionId':'2','name':'数据分析实习生','cityList':[{'name':'上海'}],'jobType':'2','jobRequirement':'实习6个月'}]}}
  with patch.object(p.PublicSession,'json',return_value=response):r=p.meituan({})
  self.assertEqual(len(r['jobs']),2);self.assertEqual(r['jobs'][1]['category'],'实习');self.assertIn('实习6个月',r['jobs'][1]['description'])
 def test_youdao_does_not_mislabel_other_netease_businesses(self):
  response={'code':200,'data':{'total':2,'list':[{'id':1,'name':'数据分析师','productName':'网易游戏','requirement':'经验3年'},{'id':2,'name':'数据分析师','productName':'网易有道','workPlaceNameList':['北京'],'reqWorkYearsName':'3-5年','requirement':'SQL'}]}}
  with patch.object(p.PublicSession,'json',return_value=response):r=p.youdao({})
  self.assertEqual(len(r['jobs']),1);self.assertEqual(r['jobs'][0]['source_key'],'2');self.assertIn('3-5年',r['jobs'][0]['description']);self.assertIn('社会招聘',r['jobs'][0]['category'])
 def test_ant_uses_official_page_limit_and_china_graduation_dates(self):
  calls=[]
  def query(_,path,body=None):
   calls.append(body)
   return {'success':True,'totalCount':1,'content':[{'id':3,'name':'数据分析师','workLocations':['杭州'],'batchName':'2027届应届生招聘','graduationTime':{'from':'2026-10-31T16:00:00.000+00:00','to':'2027-10-30T16:00:00.000+00:00'},'requirement':'SQL / 2027届本科及以上'}]}
  with patch.object(p.PublicSession,'json',query):r=p.antgroup({})
  self.assertEqual(calls[0]['pageSize'],10);self.assertIn('2026-11-01 ~ 2027-10-31',r['jobs'][0]['description']);self.assertTrue(r['complete'])
 def test_browser_snapshot_never_imports_summary_only_or_claims_full_coverage(self):
  import json
  from datetime import datetime,timezone
  from pathlib import Path
  data={'checked_at':datetime.now(timezone.utc).isoformat(),'jobs':[{'source_key':'1','title':'数据分析师','url':'https://jobs.bytedance.com/campus/position/1/detail','full_detail':True,'description':'职位要求 SQL / 2027届'},{'source_key':'2','title':'数据分析师','description':'只读到列表摘要'}]}
  with patch.object(Path,'read_text',return_value=json.dumps(data)):r=p.public_browser({})
  self.assertEqual(len(r['jobs']),1);self.assertFalse(r['complete']);self.assertEqual(r['snapshot_at'],data['checked_at']);self.assertIn('非每日接口更新',r['jobs'][0]['description'])
