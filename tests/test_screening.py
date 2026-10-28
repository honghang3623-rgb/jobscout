import unittest
from screening import geography,authorization,constraints,facets

class ScreeningTests(unittest.TestCase):
 def job(self,**kw):return {'market':'us','title':'Data Analyst','location':'San Francisco, CA','description':'SQL Python analytics',**kw}
 def test_foreign_remote_is_not_american(self):
  for location in ['Chile, Remote','Argentina, Remote','Remote - Canada','Remote (LATAM)']:
   self.assertEqual(geography(self.job(location=location))['country'],'other')
  self.assertEqual(geography(self.job(location='Remote'))['country'],'unknown')
 def test_us_state_and_mainland_city_are_separate(self):
  self.assertEqual(geography(self.job())['regions'],['CA'])
  j=self.job(market='cn',location='浙江省·杭州市');self.assertEqual(geography(j)['regions'],['杭州'])
  self.assertEqual(geography(self.job(market='cn',location='香港特别行政区'))['country'],'other')
 def test_opt_is_not_future_sponsorship(self):
  policy=authorization('We cannot provide visa sponsorship now or in the future.')
  self.assertEqual(policy['code'],'no_future')
  self.assertEqual(authorization('Candidates on OPT are not eligible for this role.')['code'],'opt_excluded')
  self.assertEqual(authorization('We offer visa sponsorship for this position.')['code'],'supports')
  self.assertEqual(authorization('We consider all applicants regardless of citizenship status.')['code'],'unknown')
 def test_summer_2027_return_to_school(self):
  job=self.job(title='Data Analyst Intern Summer 2027',description='Candidates must return to school following the internship.')
  self.assertTrue(any(h['item']=='实习后返校' and h['status']=='不符合' for h in constraints(job)))
 def test_doctoral_only_and_masters_alternative(self):
  self.assertTrue(any(h['item']=='学历要求' for h in constraints(self.job(title='PhD Intern, Data Science (2027)'))))
  self.assertFalse(any(h['item']=='学历要求' for h in constraints(self.job(description='Currently pursuing a Masters or PhD in Statistics.'))))
 def test_optional_experience_is_separate(self):
  required=facets(self.job(description='2+ years of relevant data analysis experience required. SQL Python.'))
  optional=facets(self.job(description='2 years of analytics experience preferred.'))
  self.assertEqual(required['experience']['min_years'],2)
  self.assertIsNone(optional['experience']['min_years'])
 def test_track_new_graduate_and_skills(self):
  f=facets(self.job(title='Associate Data Analyst (College Grad 2027)',description='SQL, Python, Stata and econometrics.'))
  self.assertEqual(f['track'],'graduate');self.assertIn('Stata / 计量',f['skills'])

 def test_graduation_month_window_rejects_may_2027(self):
  for jd in ['graduation date between December 2027 and June 2028 (required).','You will graduate in fall 2027 or spring 2028 with a Masters degree.','with the expectation of graduating in December 2027 or spring/summer 2028.']:
   self.assertTrue(any(h['item']=='毕业窗口' and h['status']=='不符合' for h in constraints(self.job(title='Data Analyst Intern 2027',description=jd))))
  allowed=self.job(title='Data Analyst Intern 2027',description='graduating between December 2026 and June 2027.')
  self.assertFalse(any(h['item']=='毕业窗口' for h in constraints(allowed)))
 def test_explicit_visa_support_is_identified(self):
  self.assertEqual(authorization('Brattle will provide H-1B, E3 and TN visa support to full-time candidates who require visa support.')['code'],'supports')

 def test_washington_dc_is_not_washington_state(self):
  self.assertEqual(geography(self.job(location='Washington, District of Columbia, United States'))['regions'],['DC'])
  self.assertEqual(geography(self.job(location='Seattle, Washington, United States'))['regions'],['WA'])

 def test_source_intern_category_overrides_generic_title(self):
  job=self.job(market='cn',category='日常实习',title='数据分析师',location='北京')
  self.assertEqual(facets(job)['type'],'intern')
  self.assertEqual(facets(self.job(title='2027 Summer Analyst'))['type'],'intern')

 def test_china_cohort_and_official_window(self):
  for job in [self.job(market='cn',title='数据分析实习生【28届，面向转正】'),self.job(market='cn',description='毕业时间窗口：2027-06-01 ~ 2029-09-30')]:
   self.assertTrue(any(x['status']=='不符合' for x in constraints(job)))
  job=self.job(market='cn',title='2027/2028届数据分析师',description='毕业时间窗口：2026-11-01 ~ 2027-10-31')
  self.assertFalse(any(x['status']=='不符合' for x in constraints(job)))
 def test_technical_research_is_not_economic_research(self):
  j=self.job(market='cn',title='研究型实习生-数据库自动调优方案研究')
  self.assertEqual(facets(j)['direction']['code'],'quant')
 def test_china_multi_country_location_keeps_its_warning(self):
  x=geography(self.job(market='cn',location='上海市，美国'))
  self.assertEqual(x['country'],'cn');self.assertIn('境外',x['label'])
