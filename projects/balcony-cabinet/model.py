"""Шкаф на балкон: два самостоятельных изделия — колонна и тумба.

Запуск:
    uv run python projects/balcony-cabinet/model.py

Изделия стоят РЯДОМ на полу, а не одно на другом: колонна занимает свою
часть ниши от пола до потолка, тумба — оставшуюся ширину. У каждого свой
замкнутый корпус (дно, крыша, две боковины, задняя стенка) и своя
деталировка. Собираются порознь, на месте стягиваются между собой.

Глубина у обоих одинаковая, задние стенки и фасады в одной плоскости:
фронт получается ровным, без ступеньки.

Система координат: начало — левый ПЕРЕДНИЙ нижний угол всей конструкции.
    X — ширина, вправо, если смотреть на шкаф спереди,
    Y — глубина, вглубь к стене; фасады при Y < 0, задние стенки у стены,
    Z — высота от пола.

Наблюдатель стоит со стороны малых Y и смотрит в сторону +Y, верх — +Z;
при этом +X идёт вправо. Отсюда: колонна при `TALL_ON_LEFT = True` стоит
у X = 0 и видна СЛЕВА. Проверяется не на глаз, а видом спереди —
`out/front.png` генерируется при каждом запуске.

Конструктивные решения, каждое вынужденное:

1. Крыша тумбы — столешница, а не панель: на тумбе сидят, и ЛДСП 16 мм
   под сидящим человеком имеет запас по разрушению всего ×1,4.

2. Центральная стойка тумбе больше не нужна: пролёт сократился до 505 мм
   после того, как колонна забрала свою часть ширины.

3. Вес колонны идёт в пол напрямую по её собственным боковинам —
   ничего не опирается на столешницу.

ВНИМАНИЕ, два ограничения от высоты 2775 мм — печатаются при запуске:
боковина не влезает в лист 2750×1830, и собранную колонну невозможно
поднять из горизонтального положения в вертикальное.
"""

import math

import cadquery as cq

from cadkit import (
    Panel,
    export,
    front_elevation,
    plan_view,
    shelf_check,
    show,
    side_elevation,
    spec_csv,
    spec_markdown,
)

# --- Замеры помещения ------------------------------------------------------
# ПРЕДВАРИТЕЛЬНЫЕ. Уточнить лазерной рулеткой в трёх точках каждый размер —
# ниши на балконах почти всегда не прямоугольные.

NICHE_W = 1100.0  # ширина ниши
NICHE_D = 500.0  # глубина ниши
NICHE_H = 720.0  # высота ниши (ограничение для высоты тумбы)
CEILING_H = 2780.0  # пол → потолок
BALCONY_DEPTH = 780.0  # до края балкона — справочно, конструкция мельче

# Формат листа ЛДСП у поставщика — ходовой 2750×1830. Деталь ровно
# в размер листа не выпиливается: кромка листа бывает битой, и форматка
# снимает по несколько миллиметров с каждого края. SHEET_TRIM — этот
# припуск; из листа 2750 реально выходит деталь около 2730.
SHEET_L = 2750.0
SHEET_W = 1830.0
SHEET_TRIM = 20.0

# --- Монтажные зазоры ------------------------------------------------------
# Шкаф не может быть равен нише: его надо занести и выставить по уровню.
# Щели закрываются компенсационными планками, а не подгонкой панелей.

GAP_SIDE = 5.0  # до боковых стен, с каждой стороны
GAP_TOP = 5.0  # до потолка и до верха ниши

# --- Материалы -------------------------------------------------------------

T = 16.0  # ЛДСП корпусов
# Полки колонны 16 мм при глубине корпуса 390 (в свету 380) уже не проходят
# по прогибу под стандартные 20 кг: 3,4 мм при допуске 2,8. Мельче полка —
# меньше момент инерции, поэтому толщина компенсирует укоротившуюся глубину.
T_SHELF = 22.0
T_BACK = 4.0  # ХДФ задних стенок
T_DOOR = 16.0  # ЛДСП фасадов

# Крыша тумбы — не панель, а СТОЛЕШНИЦА: на тумбе сидят.
# Столешница уже куплена: реальная толщина 34 мм (расчётные 32 были
# предварительными, до покупки). Ширина по фронту — тоже готовый размер,
# см. W_BASE ниже; в свету по глубине лишнее отрезается на месте.
T_TOP = 34.0
TOP_OVERHANG = 20.0  # свес столешницы вперёд, за фасады

# --- Что внутри стоит ------------------------------------------------------

# 3D-принтер в нижнем отсеке колонны. Раньше его габарит задавал глубину
# всей конструкции — теперь принтер не в приоритете, и глубина зафиксирована
# отдельно (см. D_BODY в «Конструкции» ниже). Отсек по глубине принтер уже
# НЕ вмещает (390 мм корпуса против 500 мм принтера) — параметры оставлены
# для высоты отсека (PRINTER_H) и справочно, для расчёта нагрузки на дно.
PRINTER_D = 500.0
PRINTER_W = 400.0
PRINTER_H = 720.0
PRINTER_CLEAR_BACK = 50.0  # запас сзади на кабели и шлейфы — уже не влияет на глубину
PRINTER_CLEAR_TOP = 30.0  # запас сверху
PRINTER_LOAD = 30.0  # вес принтера, кг — уточнить по паспорту

SEAT_LOAD = 150.0  # на тумбе сидят, кг
CEMENT_LOAD = 30.0  # мешки гипса/цемента на дне тумбы, кг

# --- Конструкция -----------------------------------------------------------

TALL_ON_LEFT = True  # колонна слева, если смотреть спереди

# Ширина тумбы задаётся купленной столешницей: её размер по фронту (500 мм)
# уже готов и в этом направлении не режется — обрезается только глубина
# (см. TOP_DEPTH ниже, там запас). Колонна забирает всю оставшуюся ширину
# ниши, поэтому её ширина здесь не фиксируется, а считается ниже как остаток.
W_BASE = 500.0

# Глубина каркаса — общая у колонны и тумбы. Раньше её задавал 3D-принтер
# (500 + запас 50 = 550), теперь принтер не в приоритете, и глубина
# зафиксирована напрямую.
D_BODY = 390.0

COL_SHELVES = 5  # полок в колонне ВЫШЕ отсека принтера

SHELF_INSET = 10.0  # полка мельче корпуса, чтобы не упиралась в фасад
DOOR_GAP = 3.0  # зазор между фасадами и по краям
SHELF_LOAD = 20.0  # расчётная нагрузка на полку, кг

# Регулируемые опоры. На балконе пол почти всегда с уклоном, без опор
# корпус не выставить по уровню. Кроме углов ставится опора ПОД СЕРЕДИНОЙ
# дна: она вдвое режет пролёт дна, и тяжёлые вещи на дне (мешки, принтер)
# перестают его прогибать. Стоит копейки, считается ниже.
CENTER_FOOT = True

# Высота опор ВЫЧИТАЕТСЯ из высоты корпусов. 30 мм — рабочий номинал:
# ходовые регулируемые опоры имеют примерно такую базу и ход регулировки
# ±10 мм, а меньше 25 мм выбор опор резко сужается и регулировать
# уклон балконного пола становится нечем.
FOOT_H = 30.0

# Тумба — одна открытая секция без полок: в неё едут мешки гипса/цемента,
# в колонне для них места нет (там снизу принтер).

# --- Цвет ------------------------------------------------------------------
# Влияет ТОЛЬКО на просмотр и картинки. На деталировку и размеры — никак.
# `cq.Color` принимает имена CSS ("slategray"), hex ("#cfd3d6")
# и четыре float 0..1 (r, g, b, alpha).

PALETTE = "светло-серый"

PALETTES: dict[str, dict[str, str]] = {
    "светло-серый": {"каркас": "#cfd3d6", "фасад": "#dde1e4", "задняя": "#b0b4b7"},
    "белый": {"каркас": "#ededed", "фасад": "#f8f8f8", "задняя": "#c4c4c4"},
    "серый": {"каркас": "#9aa0a6", "фасад": "#7d848a", "задняя": "#6b7075"},
    "дуб": {"каркас": "#c8a165", "фасад": "#b5843a", "задняя": "#9a9a9a"},
    "венге": {"каркас": "#5a4433", "фасад": "#463327", "задняя": "#6e6e6e"},
}

# --- Производные размеры ---------------------------------------------------

W_EXT = NICHE_W - 2 * GAP_SIDE  # общий габарит по ширине
W_COL = W_EXT - W_BASE  # колонне достаётся остаток ширины

# Глубина общая у обоих изделий — фиксированная D_BODY (см. «Конструкцию»
# выше). Тумба не доходит до края балкона — это осознанно, ровный фронт
# важнее лишних сантиметров.
D_CARCASS = D_BODY  # каркас
D_EXT = D_CARCASS + T_BACK  # с задней стенкой
PROTRUSION = D_EXT + T_DOOR - NICHE_D  # насколько выступает из ниши; отрицательно — не достаёт
PROTRUSION_TEXT = (
    f"выступают из ниши на {PROTRUSION:g} мм"
    if PROTRUSION >= 0
    else f"не достают до края ниши {-PROTRUSION:g} мм"
)

SHELF_D = D_CARCASS - SHELF_INSET  # полки только в колонне
PRINTER_BAY_H = PRINTER_H + PRINTER_CLEAR_TOP  # нижний отсек колонны

# Высота колонны: меньшее из «до потолка» и «что выпиливается из листа».
# Деталь в размер листа не выпилить — форматка снимает битую кромку,
# поэтому из листа 2750 максимум выходит около 2730.
MAX_PART_L = SHEET_L - SHEET_TRIM
H_COL = min(CEILING_H - GAP_TOP - FOOT_H, MAX_PART_L)
GAP_ACTUAL = CEILING_H - FOOT_H - H_COL  # фактический зазор до потолка

# Высота тумбы задана НЕ нишей, а уровнем нижней полки колонны: верх
# столешницы и верх этой полки должны совпасть в одну линию. Отсюда
# высота корпуса тумбы = дно + отсек принтера + полка.
H_BASE = T + PRINTER_BAY_H + T_SHELF
BASE_ABOVE_NICHE = FOOT_H + H_BASE - NICHE_H  # насколько тумба выше ниши

# Столешница садится СВЕРХУ коробки тумбы, а не врезана в неё: коробка
# (боковины, задняя стенка) высотой H_BASE_BOX, столешница добавляет T_TOP
# сверху. Если бы боковины шли на всю H_BASE, они пересекались бы со
# столешницей на её толщине — боковина «налезала» бы на столешницу.
H_BASE_BOX = H_BASE - T_TOP

BAY_COL = W_COL - 2 * T  # ширина колонны в свету
BAY_BASE = W_BASE - 2 * T  # ширина тумбы в свету
H_COL_IN = H_COL - 2 * T  # полезная высота колонны
H_BASE_IN = H_BASE - T - T_TOP  # полезная высота тумбы

X_COL = 0.0 if TALL_ON_LEFT else W_BASE  # левая грань колонны
X_BASE = W_COL if TALL_ON_LEFT else 0.0  # левая грань тумбы

# Столешница накрывает корпус тумбы и её фасад, выступает вперёд.
TOP_DEPTH = D_EXT + T_DOOR + TOP_OVERHANG

# Фасады. У тумбы один, до низа столешницы. У колонны три; нижний РАВЕН
# фасаду тумбы, чтобы их верхние кромки встали в одну линию с нижней
# кромкой столешницы. Два верхних делят остаток.
DOOR_W_BASE = W_BASE - 2 * DOOR_GAP
DOOR_H_BASE = H_BASE - T_TOP - 2 * DOOR_GAP
DOOR_W_COL = W_COL - 2 * DOOR_GAP
DOOR_H_COL_LOW = DOOR_H_BASE
# Зазоров у трёх фасадов четыре: снизу, два между ними и сверху.
DOOR_H_COL_UP = math.floor((H_COL - DOOR_H_COL_LOW - 4 * DOOR_GAP) / 2)

# --- Проверки --------------------------------------------------------------

# Опора под серединой дна делит его пролёт пополам.
FLOOR_SPAN_COL = BAY_COL / 2 if CENTER_FOOT else BAY_COL
FLOOR_SPAN_BASE = BAY_BASE / 2 if CENTER_FOOT else BAY_BASE

SIDE_FITS_SHEET = H_COL <= MAX_PART_L and D_CARCASS <= SHEET_W - SHEET_TRIM
# Собранный корпус поднимают из горизонтали в вертикаль, поворачивая
# вокруг нижнего ребра: в проёме между полом и потолком должна пройти
# его диагональ, а не только высота.
COL_DIAGONAL = math.hypot(H_COL, D_EXT)
CAN_TILT_UP = COL_DIAGONAL <= CEILING_H


# --- Построение ------------------------------------------------------------


def _panel(
    length: float, depth: float, height: float, at: tuple[float, float, float]
) -> cq.Workplane:
    """Прямоугольная деталь с углом в точке `at`."""
    return cq.Workplane("XY").box(length, depth, height, centered=False).translate(at)


def _column_shelf_levels() -> list[float]:
    """Высоты полок колонны от низа её внутреннего объёма.

    Снизу — высокий отсек под 3D-принтер, выше — равные отсеки.
    """
    above = H_COL_IN - PRINTER_BAY_H - T_SHELF  # свободно над первой полкой
    step = (above - (COL_SHELVES - 1) * T_SHELF) / COL_SHELVES
    return [PRINTER_BAY_H + i * (step + T_SHELF) for i in range(COL_SHELVES)]


def _shelf_step() -> float:
    """Высота отсека между полками колонны в свету."""
    levels = _column_shelf_levels()
    return levels[1] - levels[0] - T_SHELF


def _shelf_top(i: int) -> float:
    """Верхняя плоскость i-й полки колонны, от пола."""
    return FOOT_H + T + _column_shelf_levels()[i] + T_SHELF


def _tone() -> tuple[cq.Color, cq.Color, cq.Color]:
    palette = PALETTES[PALETTE]
    return (
        cq.Color(palette["каркас"]),
        cq.Color(palette["фасад"]),
        cq.Color(palette["задняя"]),
    )


def build_column() -> cq.Assembly:
    """Изделие 1 — колонна от пола до потолка.

    Внизу отсек под 3D-принтер, выше полки. Стоит на полу собственными
    боковинами: на тумбу не опирается ничем.
    """
    body, front, back = _tone()

    carcass = cq.Assembly(name="Каркас")
    shelves = cq.Assembly(name="Полки")
    doors = cq.Assembly(name="Фасады")

    z0 = FOOT_H  # низ корпуса: опоры поднимают его над полом

    carcass.add(_panel(T, D_CARCASS, H_COL, (X_COL, 0, z0)), name="Боковина 1", color=body)
    carcass.add(
        _panel(T, D_CARCASS, H_COL, (X_COL + W_COL - T, 0, z0)), name="Боковина 2", color=body
    )
    carcass.add(_panel(BAY_COL, D_CARCASS, T, (X_COL + T, 0, z0)), name="Дно", color=body)
    carcass.add(
        _panel(BAY_COL, D_CARCASS, T, (X_COL + T, 0, z0 + H_COL - T)), name="Крыша", color=body
    )
    carcass.add(
        _panel(W_COL, T_BACK, H_COL, (X_COL, D_CARCASS, z0)), name="Задняя стенка", color=back
    )

    for i, dz in enumerate(_column_shelf_levels()):
        shelves.add(
            _panel(BAY_COL, SHELF_D, T_SHELF, (X_COL + T, SHELF_INSET, z0 + T + dz)),
            name=f"Полка {i + 1}",
            color=body,
        )

    # Нижний фасад закрывает отсек принтера, два верхних делят остаток.
    z = z0 + DOOR_GAP
    for i, height in enumerate([DOOR_H_COL_LOW, DOOR_H_COL_UP, DOOR_H_COL_UP]):
        doors.add(
            _panel(DOOR_W_COL, T_DOOR, height, (X_COL + DOOR_GAP, -T_DOOR, z)),
            name=f"Фасад {i + 1}",
            color=front,
        )
        z += height + DOOR_GAP

    asm = cq.Assembly(name="Колонна")
    asm.add(carcass)
    asm.add(shelves)
    asm.add(doors)
    return asm


def build_base() -> cq.Assembly:
    """Изделие 2 — тумба. Одна открытая секция, столешница сверху."""
    body, front, back = _tone()

    carcass = cq.Assembly(name="Каркас")
    doors = cq.Assembly(name="Фасады")

    z0 = FOOT_H  # низ корпуса: опоры поднимают его над полом

    carcass.add(_panel(T, D_CARCASS, H_BASE_BOX, (X_BASE, 0, z0)), name="Боковина 1", color=body)
    carcass.add(
        _panel(T, D_CARCASS, H_BASE_BOX, (X_BASE + W_BASE - T, 0, z0)),
        name="Боковина 2",
        color=body,
    )
    carcass.add(_panel(BAY_BASE, D_CARCASS, T, (X_BASE + T, 0, z0)), name="Дно", color=body)
    carcass.add(
        _panel(W_BASE, T_BACK, H_BASE_BOX, (X_BASE, D_CARCASS, z0)),
        name="Задняя стенка",
        color=back,
    )

    # Столешница: на ней сидят. Ставится СВЕРХУ коробки (боковины
    # заканчиваются на H_BASE_BOX), поэтому не пересекается с ними.
    # Больше ничего не несёт — колонна стоит на полу сама.
    carcass.add(
        _panel(W_BASE, TOP_DEPTH, T_TOP, (X_BASE, -(T_DOOR + TOP_OVERHANG), z0 + H_BASE_BOX)),
        name="Столешница",
        color=body,
    )

    doors.add(
        _panel(DOOR_W_BASE, T_DOOR, DOOR_H_BASE, (X_BASE + DOOR_GAP, -T_DOOR, z0 + DOOR_GAP)),
        name="Фасад 1",
        color=front,
    )

    asm = cq.Assembly(name="Тумба")
    asm.add(carcass)
    asm.add(doors)
    return asm


def build() -> cq.Assembly:
    """Оба изделия вместе, как они встанут на балконе."""
    asm = cq.Assembly(name="balcony-cabinet")
    asm.add(build_column())
    asm.add(build_base())
    return asm


# --- Деталировка -----------------------------------------------------------
# length — размер вдоль текстуры. У боковин и фасадов текстура вертикальная,
# у дна, крыш и полок — вдоль длинной стороны.
#
# Кромка: 2 мм на видимые торцы, 0.4 мм на скрытые. На балконе перепады
# влажности — открытый торец ЛДСП тянет влагу и разбухает необратимо,
# поэтому кромим всё, включая невидимое.

_VERT = "текстура вертикально"


def panels_column() -> list[Panel]:
    """Деталировка колонны."""
    ldsp = f"ЛДСП {T:g} мм"
    tall = "" if SIDE_FITS_SHEET else f"НЕ ВЛЕЗАЕТ в лист {SHEET_L:g}×{SHEET_W:g}"

    return [
        Panel(
            "Боковина",
            H_COL,
            D_CARCASS,
            T,
            2,
            ldsp,
            "2/0.4/2/0.4",
            f"{_VERT}; {tall}" if tall else _VERT,
        ),
        Panel("Дно", D_CARCASS, BAY_COL, T, 1, ldsp, "2/0.4/0.4/0.4", ""),
        Panel("Крыша", D_CARCASS, BAY_COL, T, 1, ldsp, "2/0.4/0.4/0.4", ""),
        Panel(
            "Полка",
            SHELF_D,
            BAY_COL,
            T_SHELF,
            COL_SHELVES,
            f"ЛДСП {T_SHELF:g} мм",
            "2/0.4/0.4/0.4",
            "съёмная",
        ),
        Panel(
            "Фасад нижний",
            DOOR_H_COL_LOW,
            DOOR_W_COL,
            T_DOOR,
            1,
            f"ЛДСП {T_DOOR:g} мм",
            "2/2/2/2",
            f"{_VERT}; закрывает отсек принтера",
        ),
        Panel(
            "Фасад верхний",
            DOOR_H_COL_UP,
            DOOR_W_COL,
            T_DOOR,
            2,
            f"ЛДСП {T_DOOR:g} мм",
            "2/2/2/2",
            _VERT,
        ),
        Panel(
            "Задняя стенка",
            H_COL,
            W_COL,
            T_BACK,
            1,
            f"ХДФ {T_BACK:g} мм",
            "0/0/0/0",
            "накладная",
        ),
    ]


def panels_base() -> list[Panel]:
    """Деталировка тумбы."""
    ldsp = f"ЛДСП {T:g} мм"
    return [
        Panel("Боковина", H_BASE_BOX, D_CARCASS, T, 2, ldsp, "2/0.4/2/0.4", _VERT),
        Panel("Дно", D_CARCASS, BAY_BASE, T, 1, ldsp, "2/0.4/0.4/0.4", ""),
        Panel(
            "Столешница",
            W_BASE,
            TOP_DEPTH,
            T_TOP,
            1,
            f"Столешница {T_TOP:g} мм",
            "2/2/2/2",
            "на ней сидят",
        ),
        Panel(
            "Фасад", DOOR_H_BASE, DOOR_W_BASE, T_DOOR, 1, f"ЛДСП {T_DOOR:g} мм", "2/2/2/2", _VERT
        ),
        Panel(
            "Задняя стенка",
            H_BASE_BOX,
            W_BASE,
            T_BACK,
            1,
            f"ХДФ {T_BACK:g} мм",
            "0/0/0/0",
            "накладная",
        ),
    ]


# --- Точка входа -----------------------------------------------------------


def _report(label: str, check: dict) -> None:
    verdict = "проходит" if check["проходит"] else "НЕ ПРОХОДИТ"
    shown = check["прогиб через годы, мм"] or check["прогиб сразу, мм"]
    horizon = "через годы" if check["постоянная"] else "мгновенно"
    print(
        f"  {label:<38} {verdict:<11} прогиб {shown:>5} мм {horizon}"
        f", допуск {check['допустимо, мм']:g}, запас ×{check['запас по разрушению']}"
    )


if __name__ == "__main__":
    model = build()
    col_spec = panels_column()
    base_spec = panels_base()

    side = "слева" if TALL_ON_LEFT else "справа"
    other = "справа" if TALL_ON_LEFT else "слева"

    print("ИЗДЕЛИЕ 1 — КОЛОННА")
    print(f"  габарит {W_COL:g} × {D_EXT:g} × {H_COL:g} мм, {side}, от пола до потолка")
    print(f"  внутри {BAY_COL:g} мм, нижний отсек {PRINTER_BAY_H:g} мм")
    print(f"  выше {COL_SHELVES} полок с шагом {_shelf_step():.0f} мм в свету")
    print("ИЗДЕЛИЕ 2 — ТУМБА")
    print(f"  габарит {W_BASE:g} × {D_EXT:g} × {H_BASE:g} мм, {other}")
    print(f"  одна секция {BAY_BASE:g} мм, полезная высота {H_BASE_IN:g} мм")
    print(f"  столешница {T_TOP:g} мм, верх на {FOOT_H + H_BASE:g} мм от пола")
    print(f"  в один уровень с верхом первой полки колонны — {_shelf_top(0):g} мм")
    print(f"Оба изделия глубиной {D_EXT:g} мм, фронт ровный, без ступеньки")
    print(f"Общая ширина {W_COL + W_BASE:g} мм, {PROTRUSION_TEXT}")
    print(f"До края балкона остаётся {BALCONY_DEPTH - D_EXT - T_DOOR:g} мм")
    if BASE_ABOVE_NICHE > 0:
        print(
            f"  ⚠ тумба выше ниши на {BASE_ABOVE_NICHE:g} мм —"
            f" проверить, что над нишей ничего не мешает"
        )
    print()

    fits = PRINTER_W <= BAY_COL and PRINTER_D <= D_CARCASS and PRINTER_H <= PRINTER_BAY_H
    print(
        f"3D-принтер {PRINTER_W:g}×{PRINTER_D:g}×{PRINTER_H:g}: {'влезает' if fits else 'НЕ ЛЕЗЕТ'}"
    )
    print(f"  отсек {BAY_COL:g} × {D_CARCASS:g} × {PRINTER_BAY_H:g} мм\n")

    print("Высота колонны:")
    print(
        f"  корпус {H_COL:g} + опоры {FOOT_H:g} = {H_COL + FOOT_H:g} мм"
        f" при потолке {CEILING_H:g}, зазор {GAP_ACTUAL:g} мм"
    )
    print(
        f"  боковина {H_COL:g}×{D_CARCASS:g}; из листа {SHEET_L:g}×{SHEET_W:g}"
        f" при припуске {SHEET_TRIM:g} выходит {MAX_PART_L:g}×{SHEET_W - SHEET_TRIM:g}: "
        f"{'входит' if SIDE_FITS_SHEET else 'НЕ ВХОДИТ'}"
    )
    print(
        f"  поднять собранный корпус в вертикаль: диагональ {COL_DIAGONAL:.0f} мм"
        f" при потолке {CEILING_H:g} — {'можно' if CAN_TILT_UP else 'НЕЛЬЗЯ, собирать стоя'}"
    )
    print()

    foot = "опора по центру" if CENTER_FOOT else "БЕЗ опоры по центру"
    print(f"Прочность (дно считается как {foot}):")
    _report(
        f"полка колонны {BAY_COL:g} мм под {SHELF_LOAD:g} кг",
        shelf_check(BAY_COL, SHELF_D, T_SHELF, SHELF_LOAD),
    )
    _report(
        f"столешница {T_TOP:g} мм, сидит {SEAT_LOAD:g} кг",
        shelf_check(BAY_BASE, TOP_DEPTH, T_TOP, SEAT_LOAD, point_load=True, sustained=False),
    )
    _report(
        f"дно тумбы, мешки {CEMENT_LOAD:g} кг",
        shelf_check(FLOOR_SPAN_BASE, D_CARCASS, T, CEMENT_LOAD),
    )
    _report(
        f"дно колонны, принтер {PRINTER_LOAD:g} кг",
        shelf_check(FLOOR_SPAN_COL, D_CARCASS, T, PRINTER_LOAD),
    )
    print("  для сравнения — то же без опоры по центру дна:")
    _report(
        f"дно тумбы, мешки {CEMENT_LOAD:g} кг",
        shelf_check(BAY_BASE, D_CARCASS, T, CEMENT_LOAD),
    )
    # Для справки: 28 мм — более ходовая толщина столешницы, чем 32.
    _report(
        "столешница 28 мм вместо 32",
        shelf_check(BAY_BASE, TOP_DEPTH, 28.0, SEAT_LOAD, point_load=True, sustained=False),
    )
    print()

    print("## Изделие 1 — колонна\n")
    print(spec_markdown(col_spec))
    print("## Изделие 2 — тумба\n")
    print(spec_markdown(base_spec))

    out = export(model, "balcony-cabinet", __file__)
    target = out[0].parent

    # Каждое изделие отдельным файлом: заказывать и собирать их порознь.
    export(build_column(), "kolonna", __file__, formats=("step",))
    export(build_base(), "tumba", __file__, formats=("step",))
    spec_csv(col_spec, target / "specification-kolonna.csv")
    spec_csv(base_spec, target / "specification-tumba.csv")
    (target / "specification.md").write_text(
        "# Изделие 1 — колонна\n\n"
        + spec_markdown(col_spec)
        + "\n# Изделие 2 — тумба\n\n"
        + spec_markdown(base_spec),
        encoding="utf-8",
    )

    dims = (
        f"колонна {W_COL:g}×{H_COL:g} {side}, тумба {W_BASE:g}×{H_BASE:g} {other}",
        f"оба глубиной {D_EXT:g}, на опорах {FOOT_H:g} мм, потолок {CEILING_H:g}",
        f"верх столешницы и первая полка колонны в уровень — {_shelf_top(0):g} мм",
    )
    tone = PALETTES[PALETTE]
    front_elevation(
        model,
        target / "front.png",
        f"Шкаф на балкон — вид спереди ({PALETTE})",
        dim_texts=dims,
        body_color=tone["каркас"],
        door_color=tone["фасад"],
    )
    front_elevation(
        model,
        target / "front-open.png",
        "Шкаф на балкон — вид спереди без фасадов",
        hide=("фасад",),
        dim_texts=dims,
        body_color=tone["каркас"],
        door_color=tone["фасад"],
    )
    side_elevation(
        model,
        target / "side.png",
        "Шкаф на балкон — вид сбоку",
        dim_texts=(
            f"глубина {D_EXT:g} мм у обоих изделий",
            PROTRUSION_TEXT,
        ),
        body_color=tone["каркас"],
        door_color=tone["фасад"],
    )
    # Вид сверху — контур обоих изделий на полу. Горизонтальные панели
    # скрыты, иначе дно и столешница закрыли бы его собой: остаются
    # вертикали и фасады, то есть то, что реально занимает место.
    plan_view(
        model,
        target / "plan.png",
        "Шкаф на балкон — горизонтальное сечение (колонна и тумба)",
        hide=("столешница", "дно", "крыша", "полка"),
        dim_texts=(
            f"колонна {W_COL:g}, тумба {W_BASE:g}, вместе {W_EXT:g}",
            f"глубина {D_EXT:g} у обоих",
        ),
        body_color=tone["каркас"],
        door_color=tone["фасад"],
    )

    extra = [
        "kolonna.step",
        "tumba.step",
        "specification-kolonna.csv",
        "specification-tumba.csv",
        "specification.md",
        "front.png",
        "front-open.png",
        "side.png",
        "plan.png",
    ]
    for path in [*out, *(target / n for n in extra)]:
        print(f"  → {path.name}")

    show(model, names=["balcony-cabinet"])
