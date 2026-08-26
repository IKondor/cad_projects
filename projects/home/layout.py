"""Единая система координат квартиры для мебели.

Начало координат находится в левом нижнем углу основной части квартиры на
плане. X направлена вправо, Y — к верхней стороне плана, Z — от чистого пола
вверх. Все значения — в миллиметрах.

`ROOM_ANCHORS` — устойчивые точки для будущих проектов. При уточнении обмеров
правятся размеры сцены, а не координаты каждого шкафа отдельно.
"""

from __future__ import annotations

import cadquery as cq

# Названия соответствуют помещениям на предоставленном поэтажном плане.
ROOM_ANCHORS: dict[str, tuple[float, float, float]] = {
    "bedroom_center": (2270.0, 1600.0, 0.0),
    "bedroom_south_wall": (2270.0, 180.0, 0.0),
    "bedroom_west_wall": (180.0, 1600.0, 0.0),
    "kitchen_dining_center": (800.0, 5050.0, 0.0),
    "northeast_room_center": (3800.0, 5050.0, 0.0),
    "bathroom_center": (-1325.0, 850.0, 0.0),
    "west_room_center": (-1630.0, 3500.0, 0.0),
    "entry_center": (3850.0, 3300.0, 0.0),
    "loggia_center": (5205.0, 1795.0, 0.0),
    "loggia_glazing": (5864.0, 1795.0, 0.0),
}


def anchor(name: str) -> tuple[float, float, float]:
    """Вернуть опорную точку помещения; сообщает доступные имена при опечатке."""
    try:
        return ROOM_ANCHORS[name]
    except KeyError as error:
        available = ", ".join(sorted(ROOM_ANCHORS))
        raise KeyError(f"Неизвестная опорная точка {name!r}. Доступны: {available}") from error


def place_at(
    model: cq.Workplane,
    name: str,
    offset: tuple[float, float, float] = (0.0, 0.0, 0.0),
) -> cq.Workplane:
    """Переместить модель в опорную точку комнаты с дополнительным смещением."""
    x, y, z = anchor(name)
    dx, dy, dz = offset
    return model.translate((x + dx, y + dy, z + dz))
