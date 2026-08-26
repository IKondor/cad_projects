"""Базовая CAD-сцена квартиры по поэтажному плану.

Запуск:
    uv run python projects/home/model.py

Сцена намеренно состоит из несущих/перегородочных стен, пола, проёмов и окон:
это лёгкий и точный контекст для мебели, а не тяжёлый фотореалистичный BIM.
Габариты сверены с размерами на предоставленном плане. Значения, которых на
плане нет (высота потолка, толщины стен, точные створки), вынесены в параметры
и должны быть заменены контрольным обмером перед заказом мебели.
"""

from __future__ import annotations

from collections.abc import Iterable

import cadquery as cq

from cadkit import export, out_dir, show

# --- Исходные размеры ------------------------------------------------------
# Единица всего проекта — миллиметр. Размеры с плана: 5.94 × (3.43 + 3.27) м.

MAIN_W = 5940.0
NORTH_D = 3430.0
SOUTH_D = 3270.0
TOTAL_D = NORTH_D + SOUTH_D

# У плана ступенчатый контур. Ноль X — левый нижний угол спальни (длинной
# нижней части 4.54 м); верхний объём смещён на 610 мм влево.
TOP_LEFT_X = -610.0
TOP_RIGHT_X = TOP_LEFT_X + MAIN_W
BEDROOM_RIGHT_X = 4540.0
WEST_LEFT_X = -2650.0
WEST_TOP_Y = 5350.0
LODGIA_RIGHT_X = 5870.0
LODGIA_SILL_Y = 320.0

# Требуют лазерной проверки до изготовления мебели.
CEILING_H = 2700.0
EXTERIOR_WALL = 180.0
PARTITION_WALL = 100.0
FLOOR_T = 60.0
DOOR_H = 2100.0
WINDOW_SILL_H = 900.0
WINDOW_H = 1400.0
GLASS_T = 12.0

# Граница между верхними комнатами и центральной частью квартиры.
SPLIT_Y = SOUTH_D


def _box(x0: float, y0: float, x1: float, y1: float, z0: float, height: float) -> cq.Workplane:
    """Прямоугольный параллелепипед по двум углам основания."""
    return (
        cq.Workplane("XY")
        .box(abs(x1 - x0), abs(y1 - y0), height)
        .translate(((x0 + x1) / 2, (y0 + y1) / 2, z0 + height / 2))
    )


def _wall_x(
    x0: float,
    x1: float,
    y: float,
    thickness: float,
    openings: Iterable[tuple[float, float, float, float]] = (),
) -> cq.Workplane:
    """Стена по X; проём задаётся как (от_X, до_X, от_Z, до_Z)."""
    wall = _box(x0, y - thickness / 2, x1, y + thickness / 2, 0, CEILING_H)
    for start, end, z0, z1 in openings:
        wall = wall.cut(_box(start, y - thickness, end, y + thickness, z0, z1 - z0))
    return wall


def _wall_y(
    x: float,
    y0: float,
    y1: float,
    thickness: float,
    openings: Iterable[tuple[float, float, float, float]] = (),
) -> cq.Workplane:
    """Стена по Y; проём задаётся как (от_Y, до_Y, от_Z, до_Z)."""
    wall = _box(x - thickness / 2, y0, x + thickness / 2, y1, 0, CEILING_H)
    for start, end, z0, z1 in openings:
        wall = wall.cut(_box(x - thickness, start, x + thickness, end, z0, z1 - z0))
    return wall


def _window_x(x0: float, x1: float, y: float) -> cq.Workplane:
    return _box(x0, y - GLASS_T / 2, x1, y + GLASS_T / 2, WINDOW_SILL_H, WINDOW_H)


def _window_y(
    x: float,
    y0: float,
    y1: float,
    *,
    sill_height: float = WINDOW_SILL_H,
    height: float = WINDOW_H,
) -> cq.Workplane:
    return _box(x - GLASS_T / 2, y0, x + GLASS_T / 2, y1, sill_height, height)


def build() -> cq.Assembly:
    """Построить оболочку квартиры с проёмами, пригодную для расстановки мебели."""
    assembly = cq.Assembly(name="Квартира")

    # Контур повторяет ступенчатую форму плана. Справа — лоджия, а не вход.
    # Пол находится ниже уровня Z=0, чтобы мебель с Z=0 стояла на чистом полу.
    footprint = [
        (WEST_LEFT_X, 0),
        (LODGIA_RIGHT_X, 0),
        (LODGIA_RIGHT_X, SPLIT_Y),
        (TOP_RIGHT_X, SPLIT_Y),
        (TOP_RIGHT_X, TOTAL_D),
        (TOP_LEFT_X, TOTAL_D),
        (TOP_LEFT_X, WEST_TOP_Y),
        (WEST_LEFT_X, WEST_TOP_Y),
    ]
    floor = (
        cq.Workplane("XY").polyline(footprint).close().extrude(FLOOR_T).translate((0, 0, -FLOOR_T))
    )
    assembly.add(floor, name="Пол", color=cq.Color("#d9d4ca"))

    exterior = [
        # Наружные стены. Окна уже вырезаны из тел стен.
        ("Северная наружная", _wall_x(TOP_LEFT_X, TOP_RIGHT_X, TOTAL_D, EXTERIOR_WALL)),
        (
            "Восточная наружная верхняя",
            _wall_y(
                TOP_RIGHT_X,
                SPLIT_Y,
                TOTAL_D,
                EXTERIOR_WALL,
                ((4700, 5600, WINDOW_SILL_H, WINDOW_SILL_H + WINDOW_H),),
            ),
        ),
        # Нижняя правая часть — лоджия. Здесь нет наружной стены: вместо неё
        # витраж от чистого пола до потолка и две узкие стойки по краям.
        (
            "Лоджия верхняя стена",
            _wall_x(BEDROOM_RIGHT_X, LODGIA_RIGHT_X, SPLIT_Y, EXTERIOR_WALL),
        ),
        (
            "Лоджия нижняя перегородка",
            _wall_x(BEDROOM_RIGHT_X, LODGIA_RIGHT_X, LODGIA_SILL_Y, PARTITION_WALL),
        ),
        ("Южная наружная", _wall_x(WEST_LEFT_X, LODGIA_RIGHT_X, 0, EXTERIOR_WALL)),
        (
            "Западная наружная",
            _wall_y(
                WEST_LEFT_X,
                0,
                WEST_TOP_Y,
                EXTERIOR_WALL,
                ((2050, 2950, WINDOW_SILL_H, WINDOW_SILL_H + WINDOW_H),),
            ),
        ),
        ("Западный верх", _wall_x(WEST_LEFT_X, TOP_LEFT_X, WEST_TOP_Y, EXTERIOR_WALL)),
        ("Левый уступ", _wall_y(TOP_LEFT_X, WEST_TOP_Y, TOTAL_D, EXTERIOR_WALL)),
        ("Стойка лоджии нижняя", _wall_y(LODGIA_RIGHT_X, 0, LODGIA_SILL_Y, PARTITION_WALL)),
        ("Стойка лоджии верхняя", _wall_y(LODGIA_RIGHT_X, SPLIT_Y, SPLIT_Y + 100, PARTITION_WALL)),
    ]

    partitions = [
        # Верхние комнаты: 2.80 м и 2.84 м по чистому размеру на плане.
        (
            "Перегородка кухни",
            _wall_y(2240, SPLIT_Y, TOTAL_D, PARTITION_WALL, ((4850, 5650, 0, DOOR_H),)),
        ),
        # Верхняя граница центральной части: проходы к спальне и верхней правой комнате.
        (
            "Перегородка верхняя",
            _wall_x(
                TOP_LEFT_X,
                TOP_RIGHT_X,
                SPLIT_Y,
                PARTITION_WALL,
                ((-100, 700, 0, DOOR_H), (2500, 3400, 0, DOOR_H)),
            ),
        ),
        # Нижняя часть: санузел/западная комната, спальня и узкая правая ниша.
        (
            "Перегородка спальни",
            _wall_x(0, BEDROOM_RIGHT_X, 3200, PARTITION_WALL, ((2850, 3750, 0, DOOR_H),)),
        ),
        (
            "Перегородка санузла",
            _wall_x(WEST_LEFT_X, 0, 1730, PARTITION_WALL, ((-850, 50, 0, DOOR_H),)),
        ),
        (
            "Правая стена санузла",
            _wall_y(0, 0, 3200, PARTITION_WALL, ((2050, 2950, 0, DOOR_H),)),
        ),
        (
            "Перегородка правой ниши",
            _wall_y(
                BEDROOM_RIGHT_X, LODGIA_SILL_Y, SPLIT_Y, PARTITION_WALL, ((2000, 2900, 0, DOOR_H),)
            ),
        ),
        (
            "Перегородка западной комнаты",
            _wall_y(TOP_LEFT_X, 1730, WEST_TOP_Y, PARTITION_WALL, ((3050, 3950, 0, DOOR_H),)),
        ),
    ]

    for name, wall in exterior:
        assembly.add(wall, name=name, color=cq.Color("#8c8b87"))
    for name, wall in partitions:
        assembly.add(wall, name=name, color=cq.Color("#b4b1aa"))

    # Стекло позволяет отличать окна от дверных проёмов в 3D-вьюере и рендере.
    windows = [
        ("Окно западной комнаты", _window_y(WEST_LEFT_X, 2050, 2950)),
        ("Окно северо-восточной комнаты", _window_y(TOP_RIGHT_X, 4700, 5600)),
        (
            "Витраж лоджии",
            _window_y(LODGIA_RIGHT_X, LODGIA_SILL_Y, SPLIT_Y, sill_height=0, height=CEILING_H),
        ),
    ]
    for name, glass in windows:
        assembly.add(glass, name=name, color=cq.Color(0.45, 0.72, 0.86, 0.45))

    return assembly


if __name__ == "__main__":
    apartment = build()
    target = out_dir(__file__)

    # STEP — для CAD, STL — для стороннего рендера, PNG — быстрая проверка плана.
    for path in export(apartment, "apartment-shell", __file__):
        print(f"  → {path}")

    from cadkit.views import plan_view

    plan = plan_view(
        apartment,
        target / "plan.png",
        title="Квартира — базовая сцена для расстановки мебели",
        dim_texts=(
            f"Основной габарит: {MAIN_W / 1000:g} × {TOTAL_D / 1000:g} м",
            f"Высота для предварительной визуализации: {CEILING_H / 1000:g} м (уточнить обмером)",
        ),
        hide=("пол",),
        body_color="#c8c5bf",
        door_color="#a8d3e5",
        accent=("окно",),
    )
    print(f"  → {plan}")
    show(apartment)
