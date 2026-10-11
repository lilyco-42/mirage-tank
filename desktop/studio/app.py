import secrets
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from urllib.parse import urlsplit

from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from pydantic import BaseModel, ConfigDict, Field
from starlette.staticfiles import StaticFiles

from .adapters import MirageAdapter, executable
from .jobs import Jobs
from .paths import MAX_FILE, MAX_UPLOAD, Workspaces, child

WEB = Path(__file__).parents[1] / 'frontend'


class JobInput(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    session: str = Field(pattern=r'^[a-f0-9]{32}$')
    hidden: str = Field(default='hidden.png', min_length=1, max_length=240)
    surface: str = Field(default='surface.png', min_length=1, max_length=240)
    hidden_max: int = Field(default=100, ge=1, le=127)
    surface_min: int = Field(default=128, ge=128, le=255)


def create_app():
    workspaces, jobs, token = Workspaces(), Jobs(), secrets.token_urlsafe(32)

    @asynccontextmanager
    async def lifespan(app):
        yield
        await jobs.close()
        workspaces.close()

    app = FastAPI(title='Lain42 Mirage Studio', lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)
    app.state.workspaces, app.state.jobs = workspaces, jobs

    @app.middleware('http')
    async def local_only(request: Request, call_next):
        host = request.headers.get('host', '')
        try:
            parsed = urlsplit('http://' + host)
            valid = parsed.hostname in {'127.0.0.1', 'localhost', '::1'} and parsed.username is None and not parsed.path
            origin = request.headers.get('origin')
            if origin:
                valid = valid and origin == 'http://' + host
            if request.url.path.startswith('/api/'):
                valid = valid and secrets.compare_digest(request.cookies.get('asset_session', ''), token)
            if not valid:
                return JSONResponse({'detail': '请从本机工具窗口打开'}, status_code=403)
            if int(request.headers.get('content-length', '0')) > MAX_UPLOAD + 1024 * 1024:
                return JSONResponse({'detail': '两张图片合计最多 32 MB'}, status_code=413)
        except (ValueError, TypeError):
            return JSONResponse({'detail': '无效请求'}, status_code=400)
        response = await call_next(request)
        response.headers.update({'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff',
            'Content-Security-Policy': "default-src 'self'; img-src 'self' data: blob:; style-src 'self'; script-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'"})
        return response

    @app.exception_handler(ValueError)
    async def invalid(request, error):
        return JSONResponse({'detail': str(error)[:1000]}, status_code=400)

    @app.get('/', response_class=HTMLResponse)
    def index():
        response = HTMLResponse((WEB / 'index.html').read_text(encoding='utf-8'))
        response.set_cookie('asset_session', token, httponly=True, samesite='strict')
        return response

    @app.get('/api/capabilities')
    def capabilities():
        return {'available': bool(executable()), 'max_file_mb': 16, 'max_pixels': 16_000_000}

    @app.post('/api/workspaces')
    async def upload(hidden: UploadFile = File(...), surface: UploadFile = File(...)):
        identifier = uuid.uuid4().hex
        root = workspaces.new(identifier)
        names, total = {}, 0
        try:
            for role, file in [('hidden', hidden), ('surface', surface)]:
                suffix = Path(file.filename or '').suffix.lower()
                if suffix not in {'.png', '.jpg', '.jpeg'}:
                    raise ValueError('只支持 PNG / JPEG 图片')
                name = role + suffix
                names[role] = name
                size = 0
                with child(root / 'input', name).open('xb') as target:
                    while chunk := await file.read(1024 * 1024):
                        size += len(chunk)
                        total += len(chunk)
                        if size > MAX_FILE or total > MAX_UPLOAD:
                            raise HTTPException(413, '单张最多 16 MB，两张合计最多 32 MB')
                        target.write(chunk)
                if not size:
                    raise ValueError('图片不能为空')
            return {'id': identifier, **names, 'bytes': total}
        except BaseException:
            workspaces.delete(identifier)
            raise
        finally:
            await hidden.close()
            await surface.close()

    @app.delete('/api/workspaces/{identifier}')
    async def delete(identifier: str):
        workspaces.get(identifier)
        await jobs.delete_session(identifier)
        workspaces.delete(identifier)
        return {'ok': True}

    @app.post('/api/jobs')
    async def start(body: JobInput):
        return jobs.start(uuid.uuid4().hex, body.session, workspaces.get(body.session), MirageAdapter(), body)

    def get_job(identifier):
        if identifier not in jobs.items:
            raise HTTPException(404, '任务已删除')
        return jobs.items[identifier]

    @app.get('/api/jobs/{identifier}')
    def status(identifier: str):
        return jobs.public(get_job(identifier))

    @app.post('/api/jobs/{identifier}/cancel')
    async def cancel(identifier: str):
        get_job(identifier)
        return await jobs.cancel(identifier)

    @app.get('/api/jobs/{identifier}/files/{name:path}')
    def download(identifier: str, name: str):
        job = get_job(identifier)
        if job['state'] != 'done':
            raise HTTPException(409, '任务尚未完成')
        if name not in {f['name'] for f in job['files']} | {'export.zip'}:
            raise HTTPException(404, '文件不存在')
        file = child(job['out'], name)
        return FileResponse(file, filename=file.name, content_disposition_type='inline' if file.suffix == '.png' else 'attachment')

    app.mount('/assets', StaticFiles(directory=WEB), name='assets')
    return app
