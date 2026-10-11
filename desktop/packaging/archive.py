"""CI-only package manifest and portable delivery; no builds on local machines."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import zipfile

if os.environ.get('GITHUB_ACTIONS') != 'true':
    raise SystemExit('Packages only in GitHub Actions')
root=Path('dist/Lain42-Mirage-Studio')
for source in [Path('../LICENSE'),Path('README.md'),Path('SHARED-SOURCE-LICENSE'),Path('THIRD-PARTY-NOTICES.json')]:
    shutil.copyfile(source,root/source.name)
shutil.copyfile('../demo/Cargo.lock',root/'engine-Cargo.lock')
shutil.copyfile('ui/package-lock.json',root/'UI-package-lock.json')
manifest={'commit':os.environ['GITHUB_SHA'],'runner':os.environ['RUNNER_OS'],'engine':'mirage-tank/demo-cli',
          'shared_source_commit':'81b5d52fd04f3029b01251ee04d18d0760fde0bb',
          'files':{p.relative_to(root).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in root.rglob('*') if p.is_file()}}
(root/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
target=Path('dist')/('lain42-mirage-studio-'+os.environ['RUNNER_OS'].lower()+'.zip')
with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED) as archive:
    for p in root.rglob('*'):
        if p.is_file(): archive.write(p,p.relative_to(root.parent).as_posix())
digest=hashlib.sha256(target.read_bytes()).hexdigest()
target.with_suffix('.zip.sha256').write_text(digest+'\n',encoding='ascii')
Path('evidence/package.json').write_text(json.dumps({'commit':os.environ['GITHUB_SHA'],'bytes':target.stat().st_size,'sha256':digest}),encoding='utf-8')
