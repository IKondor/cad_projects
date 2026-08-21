#!/usr/bin/env python3
"""
Вставка шкафа (STL) в фото балкона с ГЕОМЕТРИЧЕСКИ ТОЧНЫМ позиционированием.

Камера решена по самому фото (см. CALIBRATION ниже) — ничего "додумывать" не нужно.
Меняешь цвет -> геометрия остаётся пиксель-в-пиксель той же.

    python3 cabinet_composite.py            # бежевый
    python3 cabinet_composite.py 4A4C4E out.png

Зависимости: pillow, numpy
"""
import struct, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

STL   = "balcony-cabinet.stl"
PHOTO = "1786795826829_image.png"          # исходное фото балкона 1086x1448

# ---------------------------------------------------------------- CALIBRATION
# Решено по линиям на фото (LSD): вертикали в кадре вертикальны (крен ~0),
# линия примыкания задней стены к полу горизонтальна => чистая 1-точечная
# перспектива. Мир: X вправо, Y от задней стены к зрителю, Z вверх,
# начало координат — нижний левый угол ниши (стык простенка и задней стены).
F      = 1195.0                 # фокус, px (сенсор 36 мм -> ~39.6 мм экв. по ширине)
CX, CY = 492.0, 664.0           # главная точка, px
CAM    = np.array([0.4233, 2.662, 1.35])   # позиция камеры, м
# Проверки: потолок у задней стены -> y=31 px (измерено 31);
#           пол у задней стены     -> y=1270 px (измерено 1270);
#           ниша 1.109 x 2.760 м, глубина 0.390 м.

# Фасады (модельные мм): x0, x1, z0, z1 — для прорисовки швов
DOORS = [(3, 587, 33, 781), (3, 587, 784, 1769),
         (3, 587, 1772, 2757), (593, 1087, 33, 781)]


def load_stl(path):
    d = open(path, 'rb').read()
    n = struct.unpack('<I', d[80:84])[0]
    t = np.array([struct.unpack('<12f', d[84 + 50 * i:84 + 50 * i + 48])[3:12]
                  for i in range(n)])
    return t.reshape(n, 3, 3)


def to_world(v):
    """модель (мм): x=ширина, y=0 фасад .. 390 задняя стенка, z=высота"""
    return np.stack([v[..., 0] / 1000.0,
                     (390.0 - v[..., 1]) / 1000.0,
                     v[..., 2] / 1000.0], -1)


def project(p):
    depth = CAM[1] - p[..., 1]
    return np.stack([CX + F * (p[..., 0] - CAM[0]) / depth,
                     CY - F * (p[..., 2] - CAM[2]) / depth], -1), depth


def render(color=(216, 209, 196), out="out.png", shadow=True, seams=True, ss=3):
    tri = to_world(load_stl(STL))
    uv, d = project(tri)
    keep = (d > 0.05).all(1)
    tri, uv, d = tri[keep], uv[keep], d[keep]

    nrm = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
    nrm /= np.linalg.norm(nrm, axis=1, keepdims=True) + 1e-9
    light = np.array([-0.5, 0.45, 0.74]); light /= np.linalg.norm(light)
    shade = 0.66 + 0.34 * np.abs(nrm @ light)          # свет из окна справа-сверху

    img = Image.open(PHOTO).convert('RGBA')
    w, h = img.size

    if shadow:
        s = Image.new('RGBA', (w, h), (0, 0, 0, 0))
        ImageDraw.Draw(s).polygon([(255, 1335), (870, 1305), (910, 1430), (225, 1448)],
                                  fill=(45, 40, 35, 80))
        img = Image.alpha_composite(img, s.filter(ImageFilter.GaussianBlur(30)))

    layer = Image.new('RGBA', (w * ss, h * ss), (0, 0, 0, 0))
    dr = ImageDraw.Draw(layer)
    c = np.array(color, float)
    for i in np.argsort(-d.mean(1)):                    # painter's algorithm
        dr.polygon([tuple(p * ss) for p in uv[i]],
                   fill=tuple(int(np.clip(v, 0, 255)) for v in c * shade[i]) + (255,))

    if seams:
        for x0, x1, z0, z1 in DOORS:
            q, _ = project(to_world(np.array(
                [[x0, -16, z0], [x1, -16, z0], [x1, -16, z1], [x0, -16, z1]], float)))
            q = [tuple(p * ss) for p in q]
            dr.line(q + [q[0]], fill=(96, 90, 82, 150), width=int(1.1 * ss))

    layer = layer.resize((w, h), Image.LANCZOS)
    Image.alpha_composite(img, layer).convert('RGB').save(out)
    print("saved", out)


if __name__ == "__main__":
    hexcol = sys.argv[1] if len(sys.argv) > 1 else "D8D1C4"
    name = sys.argv[2] if len(sys.argv) > 2 else "out.png"
    render(tuple(int(hexcol[i:i + 2], 16) for i in (0, 2, 4)), name)