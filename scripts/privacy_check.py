"""Conservative publication guard. Reports locations/categories, never matching secrets."""
import re
import subprocess
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def paths():
    result=subprocess.run(['git','rev-parse','--show-toplevel'],cwd=ROOT,capture_output=True,text=True)
    if result.returncode==0 and Path(result.stdout.strip())==ROOT:
        result=subprocess.run(['git','ls-files','--cached','--others','--exclude-standard','-z'],cwd=ROOT,capture_output=True,check=True)
        return sorted(set(p for p in result.stdout.decode().split('\0') if p))
    result=[]
    for p in ROOT.rglob('*'):
        if not p.is_file():continue
        relative=p.relative_to(ROOT)
        if any(x in relative.parts for x in ['data','.git','__pycache__','.venv']):continue
        if p.parent==ROOT and p.name in ['profile.md','profile_cn.md']:continue
        result.append(str(relative))
    return sorted(result)


RULES={
 'credential-like value':r'(?:sk-ant-[A-Za-z0-9_-]{20,}|gh[pousr]_[A-Za-z0-9]{25,}|github_pat_[A-Za-z0-9_]{30,}|AKIA[A-Z0-9]{16}|-----BEGIN (?:RSA |OPENSSH )?PRIVATE KEY-----)',
 'absolute personal directory':r'(?:[/]Users[/][^/\s]+|[/]home[/][^/\s]+|[A-Z]:\\Users\\[^\\\s]+)',
 'contact address':r'\b[A-Za-z0-9._%+-]+@(?!(?:example\.(?:com|org)|users\.noreply\.github\.com)\b)[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b',
 'phone-like field':r'(?i)(?:phone|mobile|电话|手机)[\s\"\x27:=]{0,10}(?:\+?86[- ]?)?1[3-9]\d{9}',
}

def main():
    failures=[];files=paths()
    for name in files:
        p=Path(name);parts=p.parts
        if parts[0] in ['data','backups','vendor'] or name in ['profile.md','profile_cn.md'] or p.suffix.lower() in ['.db','.sqlite','.docx','.pdf','.xlsx','.csv','.log','.pem','.key'] or p.name.startswith('.env') and p.name!='.env.example':
            failures.append((name,'private/generated artifact'));continue
        if p.suffix.lower() in ['.png','.jpg','.jpeg','.webp']:continue
        try:text=(ROOT/p).read_text(encoding='utf-8')
        except (UnicodeDecodeError,OSError):failures.append((name,'unexpected binary/unreadable file'));continue
        for category,pattern in RULES.items():
            if re.search(pattern,text):failures.append((name,category))
    for name,category in failures:print(f'FAIL {name}: {category}')
    if failures:return 1
    print(f'Privacy guard passed: {len(files)} publication files; no prohibited artifacts or matching contact/credential patterns.')
    return 0

if __name__=='__main__':raise SystemExit(main())
