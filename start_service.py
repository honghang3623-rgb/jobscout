#!/usr/bin/env python3
"""Start a local server independently of the invoking terminal/chat session."""
import hashlib
import os
import plistlib
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
URL = 'http://127.0.0.1:8765'
LABEL = 'local.jobscout.'+hashlib.sha256(str(ROOT).encode()).hexdigest()[:10]


def ready():
    try:
        with urllib.request.urlopen(URL+'/api/task',timeout=1) as response:
            return response.status == 200
    except Exception:
        return False


def main():
    if ready() and '--restart' not in sys.argv:
        print(URL)
        return 0
    log=ROOT/'data/server.log'
    log.parent.mkdir(exist_ok=True)
    command=[sys.executable,str(ROOT/'server.py')]
    if sys.platform=='darwin':
        # Bootstrap a GUI-domain background agent from the project, not a login item.
        # KeepAlive makes crashes recoverable, and avoids launchctl submit/remove races.
        domain='gui/'+str(os.getuid())
        agent=ROOT/'data/service.plist'
        agent.write_bytes(plistlib.dumps({'Label':LABEL,'ProgramArguments':command,
            'WorkingDirectory':str(ROOT),'RunAtLoad':True,'KeepAlive':True,
            'ThrottleInterval':5,'ProcessType':'Background',
            'StandardOutPath':str(log),'StandardErrorPath':str(log)}))
        subprocess.run(['/bin/launchctl','bootout',domain+'/'+LABEL],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        subprocess.run(['/bin/launchctl','remove',LABEL],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        time.sleep(.5)
        result=subprocess.run(['/bin/launchctl','bootstrap',domain,str(agent)],capture_output=True,text=True)
        if result.returncode:
            print('后台服务启动失败：'+result.stderr.strip(),file=sys.stderr)
            return 1
    else:
        with log.open('ab') as out:
            subprocess.Popen(command,stdin=subprocess.DEVNULL,stdout=out,stderr=out,start_new_session=True)
    for _ in range(60):
        if ready():
            print(URL)
            return 0
        time.sleep(.25)
    print('启动未完成，请检查 '+str(log),file=sys.stderr)
    if log.exists():
        print(log.read_text(errors='replace')[-2000:],file=sys.stderr)
    return 1


if __name__=='__main__':
    raise SystemExit(main())
