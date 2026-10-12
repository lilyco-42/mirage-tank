"""Self-authored geometric images; never bundle third-party art as test assets."""
import io
from pathlib import Path
from PIL import Image, ImageDraw


def fixtures():
    hidden = Image.new('L', (128, 128), 24)
    draw = ImageDraw.Draw(hidden)
    draw.polygon([(12, 100), (64, 14), (116, 100)], fill=220)
    draw.rectangle((42, 75, 86, 112), fill=90)
    surface = Image.new('L', (128, 128), 220)
    draw = ImageDraw.Draw(surface)
    draw.ellipse((25, 20, 108, 103), fill=35)
    draw.ellipse((54, 10, 114, 80), fill=220)
    draw.rectangle((10, 110, 118, 116), fill=80)
    def encode(image):
        data = io.BytesIO(); image.save(data, 'PNG'); return data.getvalue()
    return encode(hidden), encode(surface)


if __name__ == '__main__':
    for name, data in zip(('hidden', 'surface'), fixtures()):
        Path('tests/' + name + '.png').write_bytes(data)
