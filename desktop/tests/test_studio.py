import asyncio
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch
import zipfile

from fastapi.testclient import TestClient
from PIL import Image

from fixture import fixtures
from studio.adapters import executable
from studio.app import create_app
from studio.jobs import Jobs
from studio.paths import child, Workspaces


def assert_picture(test, output, hidden, surface, high=100, low=128):
    image = Image.open(io.BytesIO(output)).convert('RGBA')
    dark = Image.open(io.BytesIO(hidden)).convert('L')
    light = Image.open(io.BytesIO(surface)).convert('L')
    test.assertEqual(image.size, dark.size)
    test.assertTrue(any(p[3] < 255 for p in image.getdata()))
    # Verify what users actually see after alpha compositing on black and white,
    # not a mirror of the Rust pixel formula.
    for pixel, source_dark, source_light in zip(image.getdata(), dark.getdata(), light.getdata()):
        red, green, blue, alpha = pixel
        test.assertEqual(red, green); test.assertEqual(green, blue)
        black = red * alpha / 255
        white = black + 255 - alpha
        test.assertLessEqual(abs(black - int(source_dark / 255 * high)), 3)
        test.assertLessEqual(abs(white - (low + int(source_light / 255 * (255-low)))), 3)


class StudioTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.client = TestClient(self.app, base_url='http://127.0.0.1:8043')
        self.client.__enter__()
        self.assertEqual(self.client.get('/').status_code, 200)
        self.hidden, self.surface = fixtures()

    def tearDown(self):
        self.client.__exit__(None, None, None)

    def upload(self, hidden=None, surface=None):
        response = self.client.post('/api/workspaces', files={'hidden': ('secret.png', self.hidden if hidden is None else hidden, 'image/png'), 'surface': ('cover.png', self.surface if surface is None else surface, 'image/png')})
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()

    def complete(self, workspace, **parameters):
        started = self.client.post('/api/jobs', json={'session':workspace['id'], 'hidden':workspace['hidden'], 'surface':workspace['surface'], **parameters})
        self.assertEqual(started.status_code,200,started.text)
        job = started.json()
        for _ in range(120):
            job = self.client.get('/api/jobs/'+job['id']).json()
            if job['state'] not in {'queued','running'}: return job
            time.sleep(.1)
        self.fail('CLI task did not finish')

    def test_real_engine_composites_and_export_and_delete(self):
        workspace = self.upload()
        for high, low in [(100,128), (65,190)]:
            job = self.complete(workspace, hidden_max=high, surface_min=low)
            self.assertEqual(job['state'],'done',job)
            prefix = '/api/jobs/'+job['id']+'/files/'
            png = self.client.get(prefix+'mirage.png')
            self.assertEqual(png.status_code,200)
            assert_picture(self,png.content,self.hidden,self.surface,high,low)
            with zipfile.ZipFile(io.BytesIO(self.client.get(prefix+'export.zip').content)) as archive:
                self.assertEqual(archive.read('mirage.png'),png.content)
                self.assertEqual(json.loads(archive.read('result.json'))['hidden_max'],high)
            self.assertEqual(self.client.get(prefix+'not-uploaded.png').status_code,404)
        root = self.app.state.workspaces.get(workspace['id'])
        self.assertEqual(self.client.delete('/api/workspaces/'+workspace['id']).status_code,200)
        self.assertFalse(root.exists())
        self.assertEqual(self.client.get('/api/jobs/'+job['id']).status_code,404)

    def test_bad_images_fail_and_fresh_work_still_succeeds(self):
        workspace = self.upload(hidden=b'not a PNG')
        self.assertEqual(self.complete(workspace)['state'],'failed')
        self.client.delete('/api/workspaces/'+workspace['id'])
        self.assertEqual(self.complete(self.upload())['state'],'done')

    def test_local_boundaries_and_strict_parameters(self):
        self.assertEqual(TestClient(self.app,base_url='http://127.0.0.1:8043').get('/api/capabilities').status_code,403)
        self.assertEqual(self.client.get('/api/capabilities',headers={'Origin':'https://evil.example'}).status_code,403)
        self.assertEqual(self.client.get('/',headers={'Host':'evil.example'}).status_code,403)
        workspace = self.upload()
        base = {'session':workspace['id'],'hidden':workspace['hidden'],'surface':workspace['surface']}
        for value in [0,128,True,'100']:
            self.assertEqual(self.client.post('/api/jobs',json={**base,'hidden_max':value}).status_code,422)
        self.assertEqual(self.client.post('/api/jobs',json={**base,'command':'whoami'}).status_code,422)
        self.assertEqual(self.client.post('/api/jobs',json={**base,'hidden':'../secret.png'}).status_code,400)
        self.assertEqual(self.client.post('/api/workspaces',files={'hidden':('script.exe',b'data'),'surface':('cover.png',self.surface)}).status_code,400)
        self.assertEqual(self.client.post('/api/workspaces',files={'hidden':('empty.png',b''),'surface':('cover.png',self.surface)}).status_code,400)
        self.assertEqual(len(self.app.state.workspaces.items),1)
        other = create_app()
        with TestClient(other,base_url='http://127.0.0.1:8043') as client:
            client.get('/')
            self.assertEqual(client.delete('/api/workspaces/'+workspace['id']).status_code,400)

    def test_legacy_cli_defaults_and_size_and_extension(self):
        with tempfile.TemporaryDirectory() as folder:
            base = Path(folder); (base/'h.png').write_bytes(self.hidden); (base/'s.png').write_bytes(self.surface)
            command = [executable(),str(base/'h.png'),str(base/'s.png'),str(base/'out.png')]
            self.assertEqual(subprocess.run(command,capture_output=True).returncode,0)
            assert_picture(self,(base/'out.png').read_bytes(),self.hidden,self.surface)
            self.assertNotEqual(subprocess.run(command+['0','128'],capture_output=True).returncode,0)
            self.assertNotEqual(subprocess.run(command[:-1]+[str(base/'out.jpg')],capture_output=True).returncode,0)
            Image.new('L',(4001,4001)).save(base/'large.png')
            self.assertNotEqual(subprocess.run([executable(),str(base/'large.png'),str(base/'s.png'),str(base/'large-out.png')],capture_output=True).returncode,0)
            self.assertFalse((base/'large-out.png').exists())


class Cancellation(unittest.IsolatedAsyncioTestCase):
    async def test_cancel_kills_real_process_and_deletion_removes_jobs(self):
        workspaces, jobs = Workspaces(), Jobs()
        root = workspaces.new('a'*32)
        class SlowAdapter:
            def command(self, *_): return [sys.executable,'-c','import time; time.sleep(60)']
        job = jobs.start('b'*32,'a'*32,root,SlowAdapter(),None)
        for _ in range(40):
            if jobs.items[job['id']].get('process'): break
            await asyncio.sleep(.05)
        process = jobs.items[job['id']]['process']
        self.assertIsNone(process.returncode)
        await jobs.cancel(job['id'])
        self.assertEqual(jobs.items[job['id']]['state'],'cancelled')
        self.assertIsNotNone(process.returncode)
        self.assertFalse(jobs.busy())
        await jobs.delete_session('a'*32)
        self.assertFalse(jobs.items)
        workspaces.close()
