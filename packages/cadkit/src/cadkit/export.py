"""Экспорт моделей в файлы.

STEP — основной обменный формат: его понимают все CAD, он хранит точную
геометрию (NURBS), а не триангуляцию. Именно STEP отдаём мебельщику/инженеру.

STL — триангулированный меш, годится для рендера (Blender) и 3D-печати,
но точность геометрии в нём теряется.
"""

from pathlib import Path

import cadquery as cq

__all__ = ["export", "out_dir"]


def out_dir(model_file: str) -> Path:
    """Каталог `out/` рядом с файлом модели. Создаётся при необходимости.

    Вызывать как `out_dir(__file__)` — тогда экспорт всегда ложится рядом
    с моделью, независимо от того, из какой директории запущен скрипт.
    """
    path = Path(model_file).resolve().parent / "out"
    path.mkdir(parents=True, exist_ok=True)
    return path


def export(
    model: cq.Workplane | cq.Assembly,
    name: str,
    model_file: str,
    formats: tuple[str, ...] = ("step", "stl"),
) -> list[Path]:
    """Выгрузить модель в `out/` рядом с файлом модели. Возвращает пути к файлам."""
    target = out_dir(model_file)
    written = []

    for fmt in formats:
        path = target / f"{name}.{fmt}"
        if isinstance(model, cq.Assembly):
            model.save(str(path))
        else:
            cq.exporters.export(model, str(path))
        written.append(path)

    return written
