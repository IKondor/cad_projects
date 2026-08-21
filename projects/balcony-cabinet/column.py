"""Изделие 1 — колонна: геометрия и деталировка.

Внизу отсек под 3D-принтер, выше — полки. Стоит на полу собственными
боковинами, на тумбу не опирается ничем. Описание и обоснование решений —
см. README.md.
"""

import cadquery as cq
import variables as v
from utils import panel, tone

from cadkit import Panel

_VERT = "текстура вертикально"


def _shelf_levels() -> list[float]:
    """Высоты полок от низа внутреннего объёма колонны.

    Снизу — высокий отсек под 3D-принтер, выше — равные отсеки.
    """
    above = v.H_COL_IN - v.PRINTER_BAY_H - v.T_SHELF  # свободно над первой полкой
    step = (above - (v.COL_SHELVES - 1) * v.T_SHELF) / v.COL_SHELVES
    return [v.PRINTER_BAY_H + i * (step + v.T_SHELF) for i in range(v.COL_SHELVES)]


def shelf_step() -> float:
    """Высота отсека между полками в свету."""
    levels = _shelf_levels()
    return levels[1] - levels[0] - v.T_SHELF


def shelf_top(i: int) -> float:
    """Верхняя плоскость i-й полки, от пола."""
    return v.FOOT_H + v.T + _shelf_levels()[i] + v.T_SHELF


def build() -> cq.Assembly:
    """Собрать 3D-модель колонны."""
    body, front = tone()

    carcass = cq.Assembly(name="Каркас")
    shelves = cq.Assembly(name="Полки")
    doors = cq.Assembly(name="Фасады")

    z0 = v.FOOT_H  # низ корпуса: опоры поднимают его над полом

    carcass.add(
        panel(v.T, v.D_CARCASS, v.H_COL, (v.X_COL, 0, z0)), name="Боковина 1", color=body
    )
    carcass.add(
        panel(v.T, v.D_CARCASS, v.H_COL, (v.X_COL + v.W_COL - v.T, 0, z0)),
        name="Боковина 2",
        color=body,
    )
    carcass.add(
        panel(v.BAY_COL, v.D_CARCASS, v.T, (v.X_COL + v.T, 0, z0)), name="Дно", color=body
    )
    carcass.add(
        panel(v.BAY_COL, v.D_CARCASS, v.T, (v.X_COL + v.T, 0, z0 + v.H_COL - v.T)),
        name="Крыша",
        color=body,
    )

    for i, dz in enumerate(_shelf_levels()):
        shelves.add(
            panel(v.BAY_COL, v.SHELF_D, v.T_SHELF, (v.X_COL + v.T, v.SHELF_INSET, z0 + v.T + dz)),
            name=f"Полка {i + 1}",
            color=body,
        )

    # Нижний фасад закрывает отсек принтера, два верхних делят остаток.
    z = z0 + v.DOOR_GAP
    for i, height in enumerate([v.DOOR_H_COL_LOW, v.DOOR_H_COL_UP, v.DOOR_H_COL_UP]):
        doors.add(
            panel(v.DOOR_W_COL, v.T_DOOR, height, (v.X_COL + v.DOOR_GAP, -v.T_DOOR, z)),
            name=f"Фасад {i + 1}",
            color=front,
        )
        z += height + v.DOOR_GAP

    asm = cq.Assembly(name="Колонна")
    asm.add(carcass)
    asm.add(shelves)
    asm.add(doors)
    return asm


# --- Деталировка -------------------------------------------------------
# length — размер вдоль текстуры. У боковин и фасадов текстура вертикальная,
# у дна, крыш и полок — вдоль длинной стороны.
#
# Кромка: 2 мм на видимые торцы, 0.4 мм на скрытые. На балконе перепады
# влажности — открытый торец ЛДСП тянет влагу и разбухает необратимо,
# поэтому кромим всё, включая невидимое.
#
# Задней стенки нет, поэтому тыльные торцы боковин, дна, крыши и полок —
# ОТКРЫТЫЕ (раньше их закрывала накладная стенка), и кромятся как видимые,
# 2 мм, а не 0.4 как было бы за глухой стенкой. Тот же принцип — в tumba.py.


def panels() -> list[Panel]:
    """Деталировка колонны."""
    ldsp = f"ЛДСП {v.T:g} мм"
    tall = "" if v.SIDE_FITS_SHEET else f"НЕ ВЛЕЗАЕТ в лист {v.SHEET_L:g}×{v.SHEET_W:g}"

    return [
        Panel(
            "Боковина",
            v.H_COL,
            v.D_CARCASS,
            v.T,
            2,
            ldsp,
            "2/0.4/2/2",
            f"{_VERT}; {tall}" if tall else _VERT,
        ),
        Panel("Дно", v.D_CARCASS, v.BAY_COL, v.T, 1, ldsp, "2/2/0.4/0.4", ""),
        Panel("Крыша", v.D_CARCASS, v.BAY_COL, v.T, 1, ldsp, "2/2/0.4/0.4", ""),
        Panel(
            "Полка",
            v.SHELF_D,
            v.BAY_COL,
            v.T_SHELF,
            v.COL_SHELVES,
            f"ЛДСП {v.T_SHELF:g} мм",
            "2/2/0.4/0.4",
            "съёмная",
        ),
        Panel(
            "Фасад нижний",
            v.DOOR_H_COL_LOW,
            v.DOOR_W_COL,
            v.T_DOOR,
            1,
            f"ЛДСП {v.T_DOOR:g} мм",
            "2/2/2/2",
            f"{_VERT}; закрывает отсек принтера",
        ),
        Panel(
            "Фасад верхний",
            v.DOOR_H_COL_UP,
            v.DOOR_W_COL,
            v.T_DOOR,
            2,
            f"ЛДСП {v.T_DOOR:g} мм",
            "2/2/2/2",
            _VERT,
        ),
    ]
