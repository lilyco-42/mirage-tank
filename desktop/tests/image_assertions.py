"""Validate visible black/white output independently of the app and CLI formula."""
import io
from PIL import Image


def assert_picture(test, output, hidden, surface, high=100, low=128):
    image = Image.open(io.BytesIO(output)).convert('RGBA')
    dark = Image.open(io.BytesIO(hidden)).convert('L')
    light = Image.open(io.BytesIO(surface)).convert('L')
    test.assertEqual(image.size, dark.size)
    test.assertTrue(any(p[3] < 255 for p in image.getdata()))
    for pixel, source_dark, source_light in zip(image.getdata(), dark.getdata(), light.getdata()):
        red, green, blue, alpha = pixel
        test.assertEqual(red, green); test.assertEqual(green, blue)
        black = red * alpha / 255
        white = black + 255 - alpha
        test.assertLessEqual(abs(black - int(source_dark / 255 * high)), 3)
        test.assertLessEqual(abs(white - (low + int(source_light / 255 * (255-low)))), 3)
