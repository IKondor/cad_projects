"""Шкаф на балкон: два самостоятельных изделия — колонна и тумба.

Запуск:
    uv run python projects/balcony-cabinet/model.py

Описание изделий, инженерные решения и их обоснование — см. README.md.

Код разложен по файлам:
    variables.py — все входные и производные размеры (правь тут)
    utils.py     — вспомогательные функции, общие для колонны и тумбы
    column.py    — геометрия и деталировка колонны
    tumba.py     — геометрия и деталировка тумбы
    model.py     — этот файл: сборка обоих изделий, отчёт в консоль, экспорт

Система координат — см. utils.py (там же, где рисуется панель) и README.md.
"""

import cadquery as cq
import column
import tumba
import variables as v
from utils import report_check

from cadkit import (
    export,
    front_elevation,
    plan_view,
    shelf_check,
    show,
    side_elevation,
    spec_csv,
    spec_markdown,
)


def build() -> cq.Assembly:
    """Оба изделия вместе, как они встанут на балконе."""
    asm = cq.Assembly(name="balcony-cabinet")
    asm.add(column.build())
    asm.add(tumba.build())
    return asm


if __name__ == "__main__":
    model = build()
    col_spec = column.panels()
    base_spec = tumba.panels()

    side = "слева" if v.TALL_ON_LEFT else "справа"
    other = "справа" if v.TALL_ON_LEFT else "слева"

    print("ИЗДЕЛИЕ 1 — КОЛОННА")
    print(f"  габарит {v.W_COL:g} × {v.D_EXT:g} × {v.H_COL:g} мм, {side}, от пола до потолка")
    print(f"  внутри {v.BAY_COL:g} мм, нижний отсек {v.PRINTER_BAY_H:g} мм")
    print(f"  выше {v.COL_SHELVES} полок с шагом {column.shelf_step():.0f} мм в свету")
    print("ИЗДЕЛИЕ 2 — ТУМБА")
    print(f"  габарит {v.W_BASE:g} × {v.D_EXT:g} × {v.H_BASE:g} мм, {other}")
    print(f"  одна секция {v.BAY_BASE:g} мм, полезная высота {v.H_BASE_IN:g} мм")
    print(f"  столешница {v.T_TOP:g} мм, верх на {v.FOOT_H + v.H_BASE:g} мм от пола")
    print(f"  в один уровень с верхом первой полки колонны — {column.shelf_top(0):g} мм")
    print(f"Оба изделия глубиной {v.D_EXT:g} мм, фронт ровный, без ступеньки")
    print(f"Общая ширина {v.W_COL + v.W_BASE:g} мм, {v.PROTRUSION_TEXT}")
    print(f"До края балкона остаётся {v.BALCONY_DEPTH - v.D_EXT - v.T_DOOR:g} мм")
    if v.BASE_ABOVE_NICHE > 0:
        print(
            f"  ⚠ тумба выше ниши на {v.BASE_ABOVE_NICHE:g} мм —"
            f" проверить, что над нишей ничего не мешает"
        )
    print()

    fits = (
        v.PRINTER_W <= v.BAY_COL and v.PRINTER_D <= v.D_CARCASS and v.PRINTER_H <= v.PRINTER_BAY_H
    )
    print(
        f"3D-принтер {v.PRINTER_W:g}×{v.PRINTER_D:g}×{v.PRINTER_H:g}:"
        f" {'влезает' if fits else 'НЕ ЛЕЗЕТ'}"
    )
    print(f"  отсек {v.BAY_COL:g} × {v.D_CARCASS:g} × {v.PRINTER_BAY_H:g} мм\n")

    print("Высота колонны:")
    print(
        f"  корпус {v.H_COL:g} + опоры {v.FOOT_H:g} = {v.H_COL + v.FOOT_H:g} мм"
        f" при потолке {v.CEILING_H:g}, зазор {v.GAP_ACTUAL:g} мм"
    )
    print(
        f"  боковина {v.H_COL:g}×{v.D_CARCASS:g}; из листа {v.SHEET_L:g}×{v.SHEET_W:g}"
        f" при припуске {v.SHEET_TRIM:g} выходит {v.MAX_PART_L:g}×{v.SHEET_W - v.SHEET_TRIM:g}: "
        f"{'входит' if v.SIDE_FITS_SHEET else 'НЕ ВХОДИТ'}"
    )
    print(
        f"  поднять собранный корпус в вертикаль: диагональ {v.COL_DIAGONAL:.0f} мм"
        f" при потолке {v.CEILING_H:g} — {'можно' if v.CAN_TILT_UP else 'НЕЛЬЗЯ, собирать стоя'}"
    )
    print()

    foot = "опора по центру" if v.CENTER_FOOT else "БЕЗ опоры по центру"
    print(f"Прочность (дно считается как {foot}):")
    report_check(
        f"полка колонны {v.BAY_COL:g} мм под {v.SHELF_LOAD:g} кг",
        shelf_check(v.BAY_COL, v.SHELF_D, v.T_SHELF, v.SHELF_LOAD),
    )
    report_check(
        f"столешница {v.T_TOP:g} мм, сидит {v.SEAT_LOAD:g} кг",
        shelf_check(
            v.BAY_BASE, v.TOP_DEPTH, v.T_TOP, v.SEAT_LOAD, point_load=True, sustained=False
        ),
    )
    report_check(
        f"дно тумбы, мешки {v.CEMENT_LOAD:g} кг",
        shelf_check(v.FLOOR_SPAN_BASE, v.D_CARCASS, v.T, v.CEMENT_LOAD),
    )
    report_check(
        f"дно колонны, принтер {v.PRINTER_LOAD:g} кг",
        shelf_check(v.FLOOR_SPAN_COL, v.D_CARCASS, v.T, v.PRINTER_LOAD),
    )
    print("  для сравнения — то же без опоры по центру дна:")
    report_check(
        f"дно тумбы, мешки {v.CEMENT_LOAD:g} кг",
        shelf_check(v.BAY_BASE, v.D_CARCASS, v.T, v.CEMENT_LOAD),
    )
    # Для справки: 28 мм — более ходовая толщина столешницы, чем 32.
    report_check(
        "столешница 28 мм вместо 32",
        shelf_check(v.BAY_BASE, v.TOP_DEPTH, 28.0, v.SEAT_LOAD, point_load=True, sustained=False),
    )
    print()

    print("## Изделие 1 — колонна\n")
    print(spec_markdown(col_spec))
    print("## Изделие 2 — тумба\n")
    print(spec_markdown(base_spec))

    out = export(model, "balcony-cabinet", __file__)
    target = out[0].parent

    # Каждое изделие отдельным файлом: заказывать и собирать их порознь.
    export(column.build(), "kolonna", __file__, formats=("step",))
    export(tumba.build(), "tumba", __file__, formats=("step",))
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
        f"колонна {v.W_COL:g}×{v.H_COL:g} {side}, тумба {v.W_BASE:g}×{v.H_BASE:g} {other}",
        f"оба глубиной {v.D_EXT:g}, на опорах {v.FOOT_H:g} мм, потолок {v.CEILING_H:g}",
        f"верх столешницы и первая полка колонны в уровень — {column.shelf_top(0):g} мм",
    )
    tone = v.PALETTES[v.PALETTE]
    front_elevation(
        model,
        target / "front.png",
        f"Шкаф на балкон — вид спереди ({v.PALETTE})",
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
            f"глубина {v.D_EXT:g} мм у обоих изделий",
            v.PROTRUSION_TEXT,
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
            f"колонна {v.W_COL:g}, тумба {v.W_BASE:g}, вместе {v.W_EXT:g}",
            f"глубина {v.D_EXT:g} у обоих",
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
