import json,unittest
from unittest.mock import patch
from urllib.parse import urlsplit,parse_qs
import china_sources as cn

class BaiduPublicTests(unittest.TestCase):
 def test_partial_public_search_dedup_and_complete_jd(self):
  calls=[]
  def public_page(url,body=None):
   self.assertIsNone(body);self.assertIn('/jobs/list?',url);calls.append(url)
   q=parse_qs(urlsplit(url).query);kind=q['recruitType'][0]
   data={'listData':{'keyWord':q['search'][0],'listDetailData':[{'postId':kind+'-1','name':'数据分析实习生' if kind=='INTERN' else '数据分析师','workPlace':'北京市','workContent':'使用 SQL Python 监控业务数据。','serviceCondition':'2027 届，经济或统计背景。','updateDate':'2026-10-27','projectType':'校招'}]}}
   return '<script>window.__INITIAL_DATA__ ='+json.dumps(data,ensure_ascii=False)+';</script>'
  with patch.object(cn,'read',public_page),patch.object(cn.time,'sleep'):
   result=cn.baidu_public({'url':'https://talent.baidu.com/jobs/list'})
  self.assertEqual(len(result['jobs']),2);self.assertFalse(result['complete'])
  self.assertEqual(len(calls),12)
  self.assertIn('SQL Python',result['jobs'][0]['description'])
  self.assertIn('/detail/GRADUATE/',result['jobs'][0]['url'])
 def test_search_that_does_not_apply_keyword_is_rejected(self):
  raw='<script>window.__INITIAL_DATA__ ='+json.dumps({'listData':{'keyWord':'','listDetailData':[]}})+'</script>'
  with patch.object(cn,'read',return_value=raw):
   with self.assertRaises(ValueError):cn.baidu_public({'url':'https://talent.baidu.com/jobs/list'})
