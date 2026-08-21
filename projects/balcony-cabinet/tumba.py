"""Изделие 2 — тумба: геометрия и деталировка.

Одна открытая секция без полок, столешница сверху. Описание и обоснование
решений — см. README.md.
"""

import cadquery as cq
import variables as v
from utils import panel, tone

from cadkit import Panel

_VERT = "текстура вертикально"


def build() -> cq.Assembly:
    """Собрать 3D-модель тумбы."""
    body, front = tone()

    carcass = cq.Assembly(name="Каркас")
    doors = cq.Assembly(name="Фасады")

    z0 = v.FOOT_H  # низ корпуса: опоры поднимают его над полом

    carcass.add(
        panel(v.T, v.D_CARCASS, v.H_BASE_BOX, (v.X_BASE, 0, z0)), name="Боковина 1", color=body
    )
    carcass.add(
        panel(v.T, v.D_CARCASS, v.H_BASE_BOX, (v.X_BASE + v.W_BASE - v.T, 0, z0)),
        name="Боковина 2",
        color=body,
    )
    carcass.add(
        panel(v.BAY_BASE, v.D_CARCASS, v.T, (v.X_BASE + v.T, 0, z0)), name="Дно", color=body
    )

    # Столешница: на ней сидят. Ставится СВЕРХУ коробки (боковины
    # заканчиваются на H_BASE_BOX), поэтому не пересекается с ними.
    # Больше ничего не несёт — колонна стоит на полу сама.
    carcass.add(
        panel(
            v.W_BASE,
            v.TOP_DEPTH,
            v.T_TOP,
            (v.X_BASE, -(v.T_DOOR + v.TOP_OVERHANG), z0 + v.H_BASE_BOX),
        ),
        name="Столешница",
        color=body,
    )

    doors.add(
        panel(
            v.DOOR_W_BASE,
            v.T_DOOR,
            v.DOOR_H_BASE,
            (v.X_BASE + v.DOOR_GAP, -v.T_DOOR, z0 + v.DOOR_GAP),
        ),
        name="Фасад 1",
        color=front,
    )

    asm = cq.Assembly(name="Тумба")
    asm.add(carcass)
    asm.add(doors)
    return asm


# --- Деталировка -------------------------------------------------------
# Правила по length/width и кромке — те же, что в column.py.


def panels() -> list[Panel]:
    """Деталировка тумбы."""
    ldsp = f"ЛДСП {v.T:g} мм"
    return [
        Panel("Боковина", v.H_BASE_BOX, v.D_CARCASS, v.T, 2, ldsp, "2/0.4/2/2", _VERT),
        Panel("Дно", v.D_CARCASS, v.BAY_BASE, v.T, 1, ldsp, "2/2/0.4/0.4", ""),
        Panel(
            "Столешница",
            v.W_BASE,
            v.TOP_DEPTH,
            v.T_TOP,
            1,
            f"Столешница {v.T_TOP:g} мм",
            "2/2/2/2",
            "на ней сидят",
        ),
        Panel(
            "Фасад",
            v.DOOR_H_BASE,
            v.DOOR_W_BASE,
            v.T_DOOR,
            1,
            f"ЛДСП {v.T_DOOR:g} мм",
            "2/2/2/2",
            _VERT,
        ),
    ]
