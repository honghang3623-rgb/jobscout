import importlib.util
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import candidate

spec=importlib.util.spec_from_file_location('privacy_guard',Path(__file__).resolve().parents[1]/'scripts/privacy_check.py')
guard=importlib.util.module_from_spec(spec);spec.loader.exec_module(guard)

class PublicEditionTests(unittest.TestCase):
 def test_local_candidate_and_environment_override(self):
  with patch.dict(os.environ,{'JOBSCOUT_GRADUATION_MONTH':'2032-09'}):self.assertEqual(candidate.graduation(),(2032,9))
  with patch.dict(os.environ,{'JOBSCOUT_GRADUATION_MONTH':'invalid'}):
   with self.assertRaises(ValueError):candidate.graduation()
 def test_templates_are_fictional(self):
  root=Path(__file__).resolve().parents[1]
  self.assertIn('Fictional',(root/'examples/profile.md').read_text())
  self.assertIn('虚构',(root/'examples/profile_cn.md').read_text())
 def test_local_profiles_are_not_overwritten(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);(root/'examples').mkdir();(root/'examples/profile.md').write_text('fictional template')
   (root/'profile.md').write_text('local user edits')
   candidate.ensure_local_files(root)
   self.assertEqual((root/'profile.md').read_text(),'local user edits')
 def test_guard_detects_contacts_and_keys_without_printing_values(self):
  import re
  self.assertTrue(re.search(guard.RULES['credential-like value'],'sk-'+'ant-'+'x'*40))
  self.assertTrue(re.search(guard.RULES['contact address'],'someone'+'@'+'private.test'))
  self.assertFalse(re.search(guard.RULES['contact address'],'demo'+'@'+'example.com'))
