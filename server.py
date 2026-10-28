#!/usr/bin/env python3
"""JobScout local application. Run python3 server.py --open."""
import argparse
import base64
import csv
import io
import json
import os
import re
import tempfile
import threading
import urllib.parse
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import platform_core as core
from jobscout import h1b
from jobscout.cli import load, load_local, save_companies, save_local

os.chdir(core.ROOT)
TOKEN = __import__('secrets').token_urlsafe(24)


class Handler(BaseHTTPRequestHandler):
    server_version = 'JobScout/1.0'

    def log_message(self, fmt, *args):
        if args and str(args[1] if len(args)>1 else '') not in ['200','304']:
            super().log_message(fmt,*args)

    def host_ok(self):
        return self.headers.get('Host','') in {f'127.0.0.1:{self.server.server_port}',f'localhost:{self.server.server_port}'}

    def send(self, data, status=200, mime='application/json; charset=utf-8', extra=None):
        body = data if isinstance(data,bytes) else json.dumps(data,ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header('Content-Type',mime)
        self.send_header('Content-Length',str(len(body)))
        self.send_header('Cache-Control','no-store')
        self.send_header('X-Content-Type-Options','nosniff')
        self.send_header('Referrer-Policy','no-referrer')
        self.send_header('Content-Security-Policy',"default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'")
        for k,v in (extra or {}).items():
            self.send_header(k,v)
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if not self.host_ok():
            return self.send({'error':'Invalid host'},403)
        path = urllib.parse.urlparse(self.path).path
        try:
            if path=='/api/state':
                data = core.state()
                data['csrf'] = TOKEN
                return self.send(data)
            if path=='/api/task':
                return self.send(core.TASK.snapshot())
            if path.startswith('/api/jobs/'):
                return self.send(core.detail(urllib.parse.unquote(path[len('/api/jobs/'):])) )
            if path=='/api/export':
                data = core.state()
                buffer = io.StringIO(newline='')
                columns = ['market','company','title','location','url','status','score','method','resume','notes','first_seen','scored_at']
                writer = csv.DictWriter(buffer,fieldnames=columns,extrasaction='ignore')
                writer.writeheader()
                for job in data['jobs']:
                    selected=urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query).get('market',['all'])[0]
                    if selected!='all' and job.get('market','us')!=selected:
                        continue
                    # Protect spreadsheet viewers from formulas embedded in scraped titles/notes.
                    writer.writerow({k: "'"+str(job.get(k,'')) if str(job.get(k,'')).startswith(('=','+','-','@')) else job.get(k,'') for k in columns})
                return self.send(('\ufeff'+buffer.getvalue()).encode(),mime='text/csv; charset=utf-8',extra={'Content-Disposition':'attachment; filename="jobscout-export.csv"'})
            files = {'/':'index.html','/app.js':'app.js','/reconnect.js':'reconnect.js','/style.css':'style.css','/icon.svg':'icon.svg','/manifest.webmanifest':'manifest.webmanifest'}
            if path not in files:
                return self.send({'error':'Not found'},404)
            mime = {'.html':'text/html','.js':'text/javascript','.css':'text/css','.svg':'image/svg+xml','.webmanifest':'application/manifest+json'}[Path(files[path]).suffix]
            return self.send((core.ROOT/'web'/files[path]).read_bytes(),mime=mime+'; charset=utf-8')
        except ValueError as e:
            return self.send({'error':str(e)},400)
        except Exception:
            return self.send({'error':'读取失败，请刷新后重试'},500)

    def do_POST(self):
        if not self.host_ok() or self.headers.get('X-JobScout-Token')!=TOKEN:
            return self.send({'error':'请刷新页面后重试'},403)
        expected = {f'http://127.0.0.1:{self.server.server_port}',f'http://localhost:{self.server.server_port}'}
        if self.headers.get('Origin') and self.headers['Origin'] not in expected:
            return self.send({'error':'Invalid origin'},403)
        url = urllib.parse.urlparse(self.path)
        try:
            size = int(self.headers.get('Content-Length','0'))
            if url.path=='/api/h1b/import':
                if size<=0 or size>200*1024*1024:
                    raise ValueError('请选择 200MB 以内的 CSV 或 XLSX 文件')
                q = urllib.parse.parse_qs(url.query)
                kind,fy = q.get('kind',['lca'])[0],q.get('fy',[''])[0]
                filename = q.get('filename',['data.csv'])[0]
                ext = Path(filename).suffix.lower()
                if kind not in ['lca','uscis'] or ext not in ['.csv','.xlsx'] or not re.fullmatch(r'20\d{2}',fy):
                    raise ValueError('请填写有效财年并选择 CSV / XLSX 文件')
                if core.TASK.snapshot()['running']:
                    raise ValueError('请等待当前任务完成后导入')
                temp = tempfile.NamedTemporaryFile(suffix=ext,dir=core.ROOT/'data',delete=False)
                try:
                    remaining = size
                    while remaining:
                        chunk = self.rfile.read(min(1024*1024,remaining))
                        if not chunk:
                            raise ValueError('文件上传中断')
                        temp.write(chunk)
                        remaining-=len(chunk)
                finally:
                    temp.close()
                def import_file():
                    try:
                        with core.LOCK,core.connect() as con:
                            n = (h1b.import_lca(con,temp.name,fy) if kind=='lca' else h1b.import_uscis(con,temp.name,fy))
                        if n==0:
                            raise ValueError('没有导入有效记录，请检查文件列名和内容')
                        return {'employers':n,'source':kind,'fiscal_year':fy}
                    finally:
                        Path(temp.name).unlink(missing_ok=True)
                try:
                    result=core.TASK.start('h1b_import',import_file)
                except Exception:
                    Path(temp.name).unlink(missing_ok=True)
                    raise
                return self.send(result)
            if size<0 or size>2*1024*1024:
                raise ValueError('请求内容过大')
            data=json.loads(self.rfile.read(size) or '{}')
            if not isinstance(data,dict):
                raise ValueError('请求格式错误')
            if url.path=='/api/jobs/add':
                return self.send(core.add_job(data))
            if url.path=='/api/jobs/update':
                return self.send(core.update_job(data))
            if url.path=='/api/scan':
                return self.send(core.TASK.start('scan',core.run_scan))
            if url.path=='/api/china/scan':
                return self.send(core.TASK.start('china_scan',core.run_china_scan))
            if url.path=='/api/rescore':
                def rescore():
                    with core.LOCK,core.connect() as con:
                        return {'scored':core.rescore_all(con)}
                return self.send(core.TASK.start('rules',rescore))
            if url.path=='/api/ai':
                ids=data.get('ids',[])
                if not isinstance(ids,list) or not ids or len(ids)>25 or any(not isinstance(x,str) for x in ids):
                    raise ValueError('请选择 1–25 个岗位')
                if not os.environ.get('ANTHROPIC_API_KEY'):
                    raise ValueError('请先在设置中配置 API 密钥')
                return self.send(core.TASK.start('ai',lambda: core.run_ai(ids)))
            if url.path=='/api/profile':
                text = data.get('profile','')
                if not isinstance(text,str) or len(text.strip())<20 or len(text)>50000:
                    raise ValueError('个人资料需要 20–50000 字')
                market=data.get('market','us')
                if market not in ['us','cn']:
                    raise ValueError('市场无效')
                with core.LOCK:
                    (core.ROOT/('profile_cn.md' if market=='cn' else 'profile.md')).write_text(text,encoding='utf-8')
                return self.send({'ok':True,'message':'已保存，原分析会标记为待更新'})
            if url.path=='/api/preferences':
                pref=core.preferences()
                if not re.fullmatch(r'(?:[01]\d|2[0-3]):[0-5]\d',data.get('daily_time','08:00')):
                    raise ValueError('请选择有效时间')
                if data.get('goal') not in ['2027 毕业后全职','2027 暑期实习','实习和全职都看']:
                    raise ValueError('请选择有效求职目标')
                pref.update({k:data[k] for k in ['daily_enabled','daily_time','goal'] if k in data})
                if data.get('intern_region',pref.get('intern_region','california')) not in ['california','any_us']:
                    raise ValueError('实习地区偏好无效')
                pref['intern_region']=data.get('intern_region',pref.get('intern_region','california'))
                pref['fulltime_region']='any_us'
                pref['daily_enabled']=bool(pref.get('daily_enabled'))
                with core.LOCK:
                    core.save_preferences(pref)
                return self.send({'ok':True})
            if url.path=='/api/settings':
                loc=load_local()
                model=data.get('model','').strip()
                if not re.fullmatch(r'[a-zA-Z0-9._:-]{3,100}',model):
                    raise ValueError('请填写有效模型名称')
                if data.get('clear_key'):
                    loc.pop('api_key',None)
                    os.environ.pop('ANTHROPIC_API_KEY',None)
                elif data.get('api_key','').strip():
                    key=data['api_key'].strip()
                    if not key.startswith('sk-ant-') or len(key)<20:
                        raise ValueError('请填写有效的 Anthropic API 密钥')
                    loc['api_key']=key
                    os.environ['ANTHROPIC_API_KEY']=key
                loc['model']=model
                with core.LOCK:
                    save_local(loc)
                return self.send({'ok':True})
            if url.path=='/api/companies':
                rows=data.get('companies',[])
                if not isinstance(rows,list) or len(rows)>1000:
                    raise ValueError('公司列表格式无效')
                seen=set()
                for c in rows:
                    if not isinstance(c,dict) or not c.get('name','').strip() or not re.fullmatch(r'[a-zA-Z0-9_-]+',c.get('slug','')) or c.get('ats') not in ['greenhouse','lever','ashby']:
                        raise ValueError('每家公司需要名称、有效 ATS 和 slug')
                    key=(c['ats'],c['slug'])
                    if key in seen:
                        raise ValueError('存在重复的 ATS / slug')
                    seen.add(key)
                    if isinstance(c.get('h1b_names'),list):
                        c['h1b_names']=';'.join(c['h1b_names'])
                with core.LOCK:
                    save_companies(rows)
                return self.send({'ok':True})
            return self.send({'error':'Not found'},404)
        except (ValueError,KeyError,TypeError) as e:
            return self.send({'error':str(e)},400)
        except Exception as e:
            return self.send({'error':'操作失败：'+str(e)},500)


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--port',type=int,default=8765)
    ap.add_argument('--open',action='store_true')
    ap.add_argument('--no-scheduler',action='store_true')
    args=ap.parse_args()
    core.initialize()
    with core.connect() as con:
        # Recover interrupted work honestly rather than showing a permanent spinner.
        con.execute("UPDATE runs SET state='interrupted',finished=? WHERE state='running'",(core.now(),))
        if not con.execute("SELECT 1 FROM meta WHERE key='initial_rules'").fetchone():
            core.rescore_all(con)
            con.execute("INSERT OR REPLACE INTO meta VALUES('initial_rules',?)",(core.VERSION,))
    server=ThreadingHTTPServer(('127.0.0.1',args.port),Handler)
    if not args.no_scheduler:
        threading.Thread(target=core.scheduler,daemon=True).start()
    url=f'http://127.0.0.1:{args.port}'
    print(f'JobScout is ready: {url}',flush=True)
    if args.open:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print('\nJobScout stopped.')
    finally:
        server.server_close()


if __name__=='__main__':
    main()
