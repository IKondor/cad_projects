"""Геометрия и деталировка пуфика. Один код на все три исполнения.

Конструкция — рамная. Вдоль изделия стоят одинаковые ПЛОСКИЕ РАМЫ из бруса
(по одной на каждую границу отсека: две крайние и по одной на каждую
перегородку), они связаны между собой поперечинами. Снаружи всё обшивается
ОСП, сверху ложатся откидные крышки из МДФ.

Отсеки идут слева направо: первый всегда под станцию пылесоса, дальше —
столько отсеков хранения, сколько задано в исполнении (0, 1 или 2).

Профиль изделия ступенчатый (см. README.md):
    задняя часть высокая — там башня станции, сверху сиденье;
    передняя низкая — ступень, под ней робот заезжает в станцию.

Обоснование размеров и узлов — README.md.
"""

from __future__ import annotations

import cadquery as cq
import variables as v
from utils import panel, tone
from variables import Variant

from cadkit import Panel

BEAM_MAT = f"Брус сосна {v.BEAM:g}×{v.BEAM:g}"
OSB_MAT = f"ОСП-3 {v.T_OSB:g} мм"
LID_MAT = f"МДФ {v.T_LID:g} мм"
FLOOR_MAT = f"{v.FLOOR_MAT} {v.T_FLOOR:g} мм"

_ALONG = "резать вдоль листа"
_SEAL = "торцы загрунтовать: рядом мокрая станция"


# --- Разбивка по ширине ----------------------------------------------------


def bays(variant: Variant) -> list[tuple[float, float, str]]:
    """Отсеки слева направо: (левая грань в свету, ширина, назначение)."""
    out = [(v.X_BAY_ST, v.BAY_ST, "станция")]
    x = v.X_BAY_ST + v.BAY_ST + v.BEAM
    for _ in range(variant.bays):
        out.append((x, v.BAY_STORE, "хранение"))
        x += v.BAY_STORE + v.BEAM
    return out


def frames(variant: Variant) -> list[float]:
    """Левые грани брусьев, на которых стоят рамы: края и перегородки."""
    xs = [v.T_OSB]
    for x0, width, _ in bays(variant):
        xs.append(x0 + width)
    return xs


def lid_zones(variant: Variant) -> list[tuple[float, float, str]]:
    """Крышки: (X начала, ширина, назначение отсека).

    Крышка накрывает свой отсек до наружного габарита по краям изделия
    и до середины перегородки — между отсеками, с зазором на открывание.
    """
    total = variant.width
    zones = []
    sections = bays(variant)
    for i, (x0, width, kind) in enumerate(sections):
        left = 0.0 if i == 0 else x0 - v.BEAM / 2 + v.LID_GAP / 2
        right = total if i == len(sections) - 1 else x0 + width + v.BEAM / 2 - v.LID_GAP / 2
        zones.append((left, right - left, kind))
    return zones


# --- Геометрия -------------------------------------------------------------


def _frame(x0: float, body: cq.Color, idx: int) -> cq.Assembly:
    """Одна плоская рама из бруса: три стойки и связи между ними."""
    asm = cq.Assembly(name=f"Рама {idx}")
    b = v.BEAM

    # Передняя стойка низкая: выше неё ступени нет, там открытый проём.
    asm.add(panel(b, b, v.Z_FLOOR_BOT, (x0, v.Y_FRONT, 0)), name=f"Стойка перед {idx}", color=body)
    asm.add(panel(b, b, v.Z_POST_TOP, (x0, v.Y_MID, 0)), name=f"Стойка средняя {idx}", color=body)
    asm.add(panel(b, b, v.Z_POST_TOP, (x0, v.Y_BACK_POST, 0)), name=f"Стойка зад {idx}", color=body)

    # Продольные связи врезаны между стойками — по паре на каждом уровне.
    front_len = v.Y_MID - v.Y_FRONT - b
    back_len = v.Y_BACK_POST - v.Y_MID - b
    for z, tag in ((0.0, "низ"), (v.Z_STEP_BEAM, "ступень")):
        asm.add(
            panel(b, front_len, b, (x0, v.Y_FRONT + b, z)),
            name=f"Связь {tag} перед {idx}",
            color=body,
        )
        asm.add(
            panel(b, back_len, b, (x0, v.Y_MID + b, z)),
            name=f"Связь {tag} зад {idx}",
            color=body,
        )

    # Верхняя обвязка ложится СВЕРХУ на стойки и проходит над станцией:
    # поэтому её положение по глубине не спорит с габаритом башни.
    asm.add(
        panel(b, v.Y_BACK_POST + b - v.Y_MID, b, (x0, v.Y_MID, v.Z_POST_TOP)),
        name=f"Обвязка боковая {idx}",
        color=body,
    )
    return asm


def _bay(x0: float, width: float, kind: str, body: cq.Color, idx: int) -> cq.Assembly:
    """Наполнение одного отсека: поперечины и горизонтальные плиты."""
    asm = cq.Assembly(name=f"Отсек {idx} — {kind}")
    b = v.BEAM

    # Верхние поперечины держат крышку по переднему и заднему краю.
    asm.add(
        panel(width, b, b, (x0, v.Y_MID, v.Z_POST_TOP)),
        name=f"Поперечина верх перед {idx}",
        color=body,
    )
    asm.add(
        panel(width, b, b, (x0, v.Y_BACK_POST, v.Z_POST_TOP)),
        name=f"Поперечина верх зад {idx}",
        color=body,
    )
    # Нижняя поперечина связывает рамы понизу; в отсеке станции она за
    # станцией и роботу не мешает.
    asm.add(panel(width, b, b, (x0, v.Y_BACK_POST, 0)), name=f"Поперечина низ {idx}", color=body)

    # Поперечины уровня ступени. Их низ — потолок гаража робота.
    for y, tag in ((v.Y_FRONT, "перед"), (v.Y_MID, "середина")):
        asm.add(
            panel(width, b, b, (x0, y, v.Z_STEP_BEAM)),
            name=f"Поперечина ступени {tag} {idx}",
            color=body,
        )

    if kind == "станция":
        # Настил ступени лежит на пролёте во всю ширину отсека — под ногой
        # 120 кг МДФ 16 такого пролёта не держит, поэтому пролёт разбит
        # продольными рёбрами. Они на высоте поперечин, роботу под ними
        # свободно: он проходит ниже, по полу.
        for rib in range(1, v.STEP_RIBS + 1):
            asm.add(
                panel(
                    b,
                    v.Y_MID - v.Y_FRONT - b,
                    b,
                    (x0 + width * rib / (v.STEP_RIBS + 1) - b / 2, v.Y_FRONT + b, v.Z_STEP_BEAM),
                ),
                name=f"Ребро настила {idx}.{rib}",
                color=body,
            )
        floor_to = v.Y_MID + b
    else:
        # В отсеке хранения та же плита продолжается назад и работает дном.
        asm.add(
            panel(width, b, b, (x0, v.Y_BACK_POST, v.Z_STEP_BEAM)),
            name=f"Поперечина ступени зад {idx}",
            color=body,
        )
        floor_to = v.Y_BACK_POST + b

    asm.add(
        panel(width, floor_to - v.Y_FRONT, v.T_FLOOR, (x0, v.Y_FRONT, v.Z_FLOOR_BOT)),
        name=f"Настил {idx}",
        color=body,
    )
    return asm


def _skin(variant: Variant, body: cq.Color) -> cq.Assembly:
    """Обшивка ОСП: боковины, задняя стенка, подступёнок."""
    asm = cq.Assembly(name="Обшивка")
    total = variant.width
    y_riser = v.Y_MID - v.T_OSB  # плоскость подступёнка

    for x0, tag in ((0.0, "лев"), (total - v.T_OSB, "прав")):
        asm.add(
            panel(v.T_OSB, v.Y_BACK - y_riser, v.Z_FRAME_TOP, (x0, y_riser, 0)),
            name=f"Обшивка бок верх {tag}",
            color=body,
        )
        asm.add(
            panel(v.T_OSB, y_riser - v.Y_FRONT, v.STEP_H, (x0, v.Y_FRONT, 0)),
            name=f"Обшивка бок низ {tag}",
            color=body,
        )

    inner = total - 2 * v.T_OSB

    # Задняя стенка с двумя вырезами: снизу под вилку с кабелем, сверху
    # под выход воздуха — станция сушит швабру горячим обдувом.
    back = panel(inner, v.T_OSB, v.Z_FRAME_TOP, (v.T_OSB, v.Y_BACK - v.T_OSB, 0))
    cable = panel(80.0, v.T_OSB, 60.0, (v.X_BAY_ST + 40.0, v.Y_BACK - v.T_OSB, v.BEAM + 20.0))
    vent = panel(
        250.0, v.T_OSB, 120.0, (v.X_BAY_ST + (v.BAY_ST - 250.0) / 2, v.Y_BACK - v.T_OSB, 430.0)
    )
    asm.add(back.cut(cable).cut(vent), name="Обшивка зад", color=body)

    # Подступёнок — вертикаль между ступенью и сиденьем. Стоит на настиле.
    asm.add(
        panel(inner, v.T_OSB, v.Z_FRAME_TOP - v.STEP_H, (v.T_OSB, y_riser, v.STEP_H)),
        name="Подступёнок",
        color=body,
    )
    return asm


def station(x0: float) -> cq.Assembly:
    """Габарит станции с роботом — справочно, в спецификацию не идёт."""
    ghost = cq.Color(0.35, 0.42, 0.5, 0.35)
    asm = cq.Assembly(name="Станция (габарит)")
    asm.add(
        panel(
            v.TOWER_W,
            v.TOWER_D,
            v.ST_H,
            (x0 + (v.BAY_ST - v.TOWER_W) / 2, v.TOWER_Y0, 0),
        ),
        name="Башня станции",
        color=ghost,
    )
    asm.add(
        panel(
            v.SLOT_W,
            v.TOWER_Y0 - v.ST_Y0,
            v.TRAY_H,
            (x0 + (v.BAY_ST - v.SLOT_W) / 2, v.ST_Y0, 0),
        ),
        name="Поддон станции",
        color=ghost,
    )
    return asm


def build(variant: Variant, with_station: bool = False) -> cq.Assembly:
    """Собрать 3D-модель исполнения."""
    body, lid = tone()
    asm = cq.Assembly(name=variant.key)

    for i, x0 in enumerate(frames(variant), 1):
        asm.add(_frame(x0, body, i))

    for i, (x0, width, kind) in enumerate(bays(variant), 1):
        asm.add(_bay(x0, width, kind, body, i))

    asm.add(_skin(variant, body))

    for i, (x0, width, kind) in enumerate(lid_zones(variant), 1):
        asm.add(
            panel(width, v.SEAT_D, v.T_LID, (x0, v.Y_MID - v.T_OSB, v.Z_FRAME_TOP)),
            name=f"Крышка {i} ({kind})",
            color=lid,
        )

    if with_station:
        asm.add(station(v.X_BAY_ST))
    return asm


# --- Деталировка -----------------------------------------------------------
# Для бруса length — длина заготовки, width и thickness — сечение.
# Для листов length идёт ВДОЛЬ листа: у ОСП вдоль главной оси модуль вдвое
# выше, и несущие детали (настилы, дно) обязаны быть ориентированы так.
# Кромка у ОСП и бруса не клеится — всё уходит под ткань и поролон,
# поэтому в графе кромки всюду нули; кромкуется только МДФ крышек.


def panels(variant: Variant) -> list[Panel]:
    """Деталировка исполнения: брус, ОСП, МДФ."""
    n_frames = len(frames(variant))
    n_store = variant.bays
    b = v.BEAM
    total = variant.width
    y_riser = v.Y_MID - v.T_OSB

    front_len = v.Y_MID - v.Y_FRONT - b
    back_len = v.Y_BACK_POST - v.Y_MID - b

    out = [
        # --- каркас, брус ---
        Panel("Стойка передняя", v.Z_FLOOR_BOT, b, b, n_frames, BEAM_MAT, note="до низа настила"),
        Panel("Стойка средняя", v.Z_POST_TOP, b, b, n_frames, BEAM_MAT, note="несёт сиденье"),
        Panel("Стойка задняя", v.Z_POST_TOP, b, b, n_frames, BEAM_MAT),
        Panel(
            "Связь продольная передняя",
            front_len,
            b,
            b,
            2 * n_frames,
            BEAM_MAT,
            note="низ и уровень ступени",
        ),
        Panel(
            "Связь продольная задняя",
            back_len,
            b,
            b,
            2 * n_frames,
            BEAM_MAT,
            note="низ и уровень ступени",
        ),
        Panel(
            "Обвязка боковая",
            v.Y_BACK_POST + b - v.Y_MID,
            b,
            b,
            n_frames,
            BEAM_MAT,
            note="кладётся на стойки сверху",
        ),
    ]

    # Поперечины: длина равна ширине своего отсека, отсеки бывают двух ширин.
    for x0, width, kind in bays(variant):
        del x0
        qty_note = f"отсек {kind} {width:g} мм"
        count = 3 if kind == "станция" else 3  # верх ×2 + низ
        out.append(Panel("Поперечина верх/низ", width, b, b, count, BEAM_MAT, note=qty_note))
        out.append(
            Panel(
                "Поперечина ступени",
                width,
                b,
                b,
                2 if kind == "станция" else 3,
                BEAM_MAT,
                note=qty_note,
            )
        )
        if kind == "станция":
            out.append(
                Panel(
                    "Ребро настила",
                    front_len,
                    b,
                    b,
                    v.STEP_RIBS,
                    BEAM_MAT,
                    note=f"делит пролёт настила на {v.STEP_RIBS + 1}",
                )
            )

    # --- ОСП ---
    out += [
        Panel(
            "Обшивка бок, верх",
            v.Z_FRAME_TOP,
            v.Y_BACK - y_riser,
            v.T_OSB,
            2,
            OSB_MAT,
            note="высокая часть",
        ),
        Panel(
            "Обшивка бок, низ",
            v.STEP_H,
            y_riser - v.Y_FRONT,
            v.T_OSB,
            2,
            OSB_MAT,
            note="под ступенью",
        ),
        Panel(
            "Обшивка задняя",
            v.Z_FRAME_TOP,
            total - 2 * v.T_OSB,
            v.T_OSB,
            1,
            OSB_MAT,
            note="вырезы: кабель 80×60, продух 250×120",
        ),
        Panel("Подступёнок", v.Z_FRAME_TOP - v.STEP_H, total - 2 * v.T_OSB, v.T_OSB, 1, OSB_MAT),
        Panel(
            "Настил ступени (станция)",
            v.Y_MID + b - v.Y_FRONT,
            v.BAY_ST,
            v.T_FLOOR,
            1,
            FLOOR_MAT,
            note=f"по ней ходят ногами; {_SEAL}",
        ),
    ]
    if n_store:
        out.append(
            Panel(
                "Настил и дно (хранение)",
                v.Y_BACK_POST + b - v.Y_FRONT,
                v.BAY_STORE,
                v.T_FLOOR,
                n_store,
                FLOOR_MAT,
                note="ступень спереди, дно отсека сзади — одной плитой",
            )
        )

    # --- МДФ крышек ---
    for i, (x0, width, kind) in enumerate(lid_zones(variant), 1):
        del x0
        out.append(
            Panel(
                f"Крышка {i} ({kind})",
                v.SEAT_D,
                width,  # зазор между створками уже вычтен в lid_zones()
                v.T_LID,
                1,
                LID_MAT,
                edges="2/2/2/2",
                note="откидная, петли по задней кромке",
            )
        )
    return out


def beam_meters(variant: Variant) -> float:
    """Погонаж бруса, метров: по нему покупается материал."""
    return sum(p.length * p.qty for p in panels(variant) if p.material == BEAM_MAT) / 1000
