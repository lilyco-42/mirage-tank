"""One explicit CLI adapter; HTTP clients cannot choose an executable or command."""
import os
from pathlib import Path
import struct
import sys

from .paths import child


def executable():
    configured = os.environ.get('LAIN42_MIRAGE_CLI')
    suffix = '.exe' if sys.platform == 'win32' else ''
    path = Path(configured) if configured else Path(getattr(sys, '_MEIPASS', Path(__file__).parents[1])) / 'bin' / ('demo-cli' + suffix)
    return str(path.resolve()) if path.is_file() else None


class MirageAdapter:
    def command(self, root, out, request):
        exe = executable()
        if not exe:
            raise ValueError('合成引擎缺失，请下载完整桌面包')
        hidden, surface = child(root, request.hidden), child(root, request.surface)
        if any(not p.is_file() or p.suffix.lower() not in {'.png', '.jpg', '.jpeg'} for p in (hidden, surface)):
            raise ValueError('请同时选择隐藏图和表面图，支持 PNG / JPEG')
        return [exe, str(hidden), str(surface), str(out / 'mirage.png'), str(request.hidden_max), str(request.surface_min)]

    def result(self, text):
        return {'message': text.strip()[:1000]}

    def validate_output(self, out, request, result):
        file = out / 'mirage.png'
        with file.open('rb') as source:
            header = source.read(33)
        if len(header) != 33 or header[:8] != b'\x89PNG\r\n\x1a\n' or header[12:16] != b'IHDR' or header[25] != 6:
            raise ValueError('引擎没有产生含透明通道的 PNG')
        width, height = struct.unpack('>II', header[16:24])
        if not 1 <= width * height <= 16_000_000:
            raise ValueError('图片尺寸无效')
        result.update(width=width, height=height, hidden_max=request.hidden_max, surface_min=request.surface_min)
