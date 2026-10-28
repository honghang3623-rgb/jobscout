import unittest
from datetime import date
from recruitment_intel import deadline_info
from market_rules import assess_china

class RecruitmentTests(unittest.TestCase):
    def test_unknown_is_not_rolling(self):
        self.assertEqual(deadline_info({},date(2026,10,27))['status'],'unknown')
    def test_conflicting_dates_are_not_silently_selected(self):
        result=deadline_info({'deadline':'2026-10-31','description':'网申截止时间：2026年10月28日'},date(2026,10,27))
        self.assertEqual(result['status'],'conflict')
        self.assertEqual(len(result['dates']),2)
    def test_deadline_boundary(self):
        for day,status in [(27,'urgent'),(26,'expired'),(31,'soon')]:
            result=deadline_info({'deadline':f'2026-10-{day}'},date(2026,10,27))
            self.assertEqual(result['status'],status)
    def test_two_years_mandatory_not_recommended(self):
        for text in ['2年数据分析经验','3年及以上银行业或大型金融机构数据治理及数据质量管理相关工作经验']:
            result=assess_china({'title':'数据分析','location':'上海','description':'任职要求：'+text},'SQL Python BI 数据分析')
            self.assertTrue(any(h['status']=='不符合' and h['item']=='经验要求' for h in result['hard']))
    def test_optional_years_and_fresh_grads_need_review(self):
        result=assess_china({'title':'数据分析','location':'上海','description':'任职要求：2年数据分析经验优先，优秀应届生亦可'},'SQL Python BI 数据分析')
        self.assertFalse(any(h['status']=='不符合' for h in result['hard']))
    def test_doctorate_only_excludes_masters_profile(self):
        result=assess_china({'title':'金融量化博士实习生','location':'上海','description':'SQL Python 数据分析'},'硕士 SQL Python')
        self.assertTrue(any(h['item']=='学历要求' and h['status']=='不符合' for h in result['hard']))
    def test_quant_engine_is_stretch_even_with_generic_title(self):
        result=assess_china({'title':'27届校招-风险管理（AI应用方向）','location':'上海','description':'量化引擎与尾部风险预测。任职要求：PyTorch，随机过程与文献复现'},'SQL Python BI 数据分析')
        self.assertEqual(result['match_tier'],'stretch')
