"""CI-only processing through the actual frozen app and its bundled Rust binary."""
import http.cookiejar
import json
import os
from pathlib import Path
import queue
import re
import subprocess
import sys
import threading
import time
import urllib.request
import unittest

from fixture import fixtures
from test_studio import assert_picture

if os.environ.get('GITHUB_ACTIONS') != 'true':
    raise SystemExit('Package acceptance only runs in GitHub Actions')
env = dict(os.environ); env.pop('LAIN42_MIRAGE_CLI',None)
process = subprocess.Popen([str(Path(sys.argv[1]).resolve())],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,env=env)
try:
    lines = queue.Queue()
    def collect():
        for line in process.stdout: lines.put(line.decode('utf-8',errors='replace'))
    threading.Thread(target=collect,daemon=True).start()
    url = None; deadline = time.time()+45
    while time.time()<deadline:
        if process.poll() is not None: raise RuntimeError('Packaged app exited early')
        try:
            line = lines.get(timeout=.2)
            found = re.search(r'http://127\.0\.0\.1:\d+/',line)
            if found: url=found[0]; break
        except queue.Empty: pass
    assert url, 'Missing startup URL'
    client = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
    for _ in range(80):
        try: client.open(url,timeout=3).read(); break
        except Exception: time.sleep(.2)
    hidden, surface = fixtures()
    boundary = 'mirage-ci-boundary'
    body=b''
    for name, data in [('hidden',hidden),('surface',surface)]:
        body += (f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"; filename="{name}.png"\r\nContent-Type: image/png\r\n\r\n').encode()+data+b'\r\n'
    body += f'--{boundary}--\r\n'.encode()
    def read(path, data=None, headers=None):
        return client.open(urllib.request.Request(url+path,data=data,headers=headers or {}),timeout=20).read()
    workspace=json.loads(read('api/workspaces',body,{'Content-Type':'multipart/form-data; boundary='+boundary}))
    job=json.loads(read('api/jobs',json.dumps({'session':workspace['id'],'hidden':workspace['hidden'],'surface':workspace['surface']}).encode(),{'Content-Type':'application/json'}))
    for _ in range(100):
        job=json.loads(read('api/jobs/'+job['id']))
        if job['state'] not in {'queued','running'}: break
        time.sleep(.1)
    assert job['state']=='done',job
    png=read('api/jobs/'+job['id']+'/files/mirage.png')
    assert_picture(unittest.TestCase(),png,hidden,surface)
    assert read('api/jobs/'+job['id']+'/files/export.zip')[:2]==b'PK'
    Path('evidence').mkdir(exist_ok=True)
    Path('evidence/bundle-smoke.json').write_text(json.dumps({'commit':os.environ['GITHUB_SHA'],'frozen_app':True,'bundled_cli':True,'real_compositing':True,'export_zip':True}),encoding='utf-8')
finally:
    process.terminate(); process.wait(timeout=15)
