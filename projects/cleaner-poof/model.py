"""Пуфик для робота-пылесоса Xiaomi Mijia M40 — три исполнения.

Запуск:
    uv run python projects/cleaner-poof/model.py

Код разложен по файлам:
    variables.py — все входные и производные размеры (правь тут)
    utils.py     — как рисуется деталь, как печатается проверка
    poof.py      — геометрия и деталировка, общие для всех исполнений
    model.py     — этот файл: отчёт, проверки прочности, экспорт

Описание конструкции и обоснование решений — README.md, исходное ТЗ — TODO.md.
"""

import cadquery as cq
import poof
import variables as v
from utils import ok, report_check

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

ACCENT = ("крышка",)


def build_all() -> cq.Assembly:
    """Три исполнения в ряд — чтобы разглядеть их во вьюере одновременно."""
    asm = cq.Assembly(name="cleaner-poof")
    step = v.D_TOTAL + 250.0
    for i, variant in enumerate(v.VARIANTS):
        asm.add(
            poof.build(variant, with_station=True),
            name=variant.key,
            loc=cq.Location(cq.Vector(0, -step * i, 0)),
        )
    return asm


def report_common() -> None:
    """То, что одинаково у всех трёх исполнений."""
    print("СТАНЦИЯ И РОБОТ")
    print(
        f"  станция {v.ST_W:g}×{v.ST_D:g}×{v.ST_H:g} (Ш×Г×В), из них башня {v.TOWER_D:g}"
        f" глубиной, поддон впереди {v.TOWER_Y0 - v.ST_Y0:g}"
    )
    print(
        f"  отсек в свету {v.BAY_ST:g}×{v.D_IN:g}, зазоры: бока {v.GAP_ST_SIDE:g},"
        f" зад {v.GAP_ST_BACK:g}, верх {v.GAP_ST_TOP:g}"
    )
    print(
        f"  проём для въезда {v.BAY_ST:g}×{v.ROBOT_PASS:g} мм при нужных"
        f" {v.SLOT_W:g}×{v.SLOT_H:g} — {ok(v.ROBOT_FITS)}"
    )
    print(
        f"  средняя поперечина на {v.Y_MID:g}..{v.Y_MID + v.BEAM:g},"
        f" башня начинается с {v.TOWER_Y0:g} — {ok(v.TOWER_CLEARS_MID)}"
    )
    print()

    print("ПРОФИЛЬ (одинаков у всех исполнений)")
    print(f"  габаритная глубина {v.D_TOTAL:g}: сиденье {v.SEAT_D:g} + ступень {v.STEP_TREAD:g}")
    print(
        f"  сиденье {v.SEAT_H:g} мм жёстко, {v.SEAT_H_SOFT:g} с продавленным"
        f" поролоном {v.FOAM:g} мм"
    )
    print(f"  ступень {v.STEP_H:g} мм, под ней просвет {v.ROBOT_PASS:g} мм")
    print(
        f"  от сиденья до подножки {v.FOOT_DROP:g} мм"
        f" — {ok(400 <= v.FOOT_DROP <= 440)} (комфортно 400–430, длина голени)"
    )
    print(f"  отсек хранения в свету {v.STORE_H:g} высотой, ниша под ним {v.NICHE_H:g}")
    print()

    print("ПРОЧНОСТЬ")
    print(f"  расчётная нагрузка на сиденье {v.SEAT_LOAD:g} кг, сосредоточенно, кратковременно")
    report_check(
        f"крышка МДФ {v.T_LID:g}, пролёт {v.LID_SPAN_Y:g}",
        shelf_check(
            v.LID_SPAN_Y, v.SEAT_D, v.T_LID, v.SEAT_LOAD, "МДФ", point_load=True, sustained=False
        ),
    )
    for thickness in (16.0, 34.0):
        report_check(
            f"  то же на МДФ {thickness:g} — для сравнения",
            shelf_check(
                v.LID_SPAN_Y,
                v.SEAT_D,
                thickness,
                v.SEAT_LOAD,
                "МДФ",
                point_load=True,
                sustained=False,
            ),
        )
    step_depth = v.Y_MID + v.BEAM - v.Y_FRONT
    floor_depth = v.Y_BACK_POST + v.BEAM - v.Y_FRONT

    def step_case(span: float) -> dict:
        return shelf_check(
            span, step_depth, v.T_FLOOR, v.SEAT_LOAD, v.FLOOR_MAT, point_load=True, sustained=False
        )

    report_check(
        f"ступень {v.FLOOR_MAT} {v.T_FLOOR:g}, {v.STEP_RIBS} ребра, пролёт {v.STEP_SPAN:g}",
        step_case(v.STEP_SPAN),
    )
    report_check("  она же на одном ребре (пролёт 200)", step_case(v.BAY_ST / 2))
    report_check(f"  она же без рёбер (пролёт {v.BAY_ST:g})", step_case(v.BAY_ST))
    report_check(
        f"дно отсека {v.FLOOR_MAT} {v.T_FLOOR:g} под {v.STORAGE_LOAD:g} кг",
        shelf_check(v.BAY_STORE, floor_depth, v.T_FLOOR, v.STORAGE_LOAD, v.FLOOR_MAT),
    )
    report_check(
        f"  дно, если на него ВСТАТЬ ногой ({v.SEAT_LOAD:g} кг)",
        shelf_check(
            v.BAY_STORE,
            floor_depth,
            v.T_FLOOR,
            v.SEAT_LOAD,
            v.FLOOR_MAT,
            point_load=True,
            sustained=False,
        ),
    )
    # Поперечина берёт примерно половину веса сидящего: вторую половину
    # крышка передаёт на противоположную обвязку.
    report_check(
        f"поперечина бруса {v.BEAM:g}×{v.BEAM:g}, пролёт {v.BAY_ST:g}",
        shelf_check(
            v.BAY_ST, v.BEAM, v.BEAM, v.SEAT_LOAD / 2, "брус", point_load=True, sustained=False
        ),
    )
    print()


def report_variant(variant: v.Variant) -> None:
    print(f"{variant.title.upper()} — {variant.key}")
    print(
        f"  габарит {variant.width:g} × {v.D_TOTAL:g} × {v.SEAT_H:g} мм"
        f" (Ш×Г×В), сидит {variant.seats} чел."
    )
    inside = ", ".join(f"{kind} {width:g}" for _, width, kind in poof.bays(variant))
    print(f"  отсеки в свету: {inside}")
    if variant.bays:
        volume = variant.bays * v.BAY_STORE * (v.Y_BACK_POST + v.BEAM - v.Y_MID) * v.STORE_H / 1e6
        niche = variant.bays * v.BAY_STORE * (v.Y_BACK_POST - v.Y_FRONT) * v.NICHE_H / 1e6
        print(f"  хранение сверху {volume:.0f} л, ниша под ступенью {niche:.0f} л")
    print(f"  крышек {len(poof.lid_zones(variant))}, бруса {poof.beam_meters(variant):.1f} п.м")
    print()


if __name__ == "__main__":
    print(
        f"ПУФИК ДЛЯ РОБОТА-ПЫЛЕСОСА — брус {v.BEAM:g}×{v.BEAM:g}, обшивка ОСП {v.T_OSB:g},"
        f" ступень и дно {v.FLOOR_MAT} {v.T_FLOOR:g}, крышки МДФ {v.T_LID:g}\n"
    )
    report_common()
    for variant in v.VARIANTS:
        report_variant(variant)

    target = None
    for variant in v.VARIANTS:
        model = poof.build(variant)
        paths = export(model, variant.key, __file__)
        target = paths[0].parent

        spec = poof.panels(variant)
        spec_csv(spec, target / f"specification-{variant.key}.csv")
        (target / f"specification-{variant.key}.md").write_text(
            f"# {variant.title}\n\n"
            f"Габарит {variant.width:g} × {v.D_TOTAL:g} × {v.SEAT_H:g} мм.\n\n"
            + spec_markdown(spec),
            encoding="utf-8",
        )

        tone = v.PALETTES[v.PALETTE]
        shown = poof.build(variant, with_station=True)
        dims = (
            f"{variant.width:g} × {v.D_TOTAL:g} × {v.SEAT_H:g} мм,"
            f" сиденье {v.SEAT_H_SOFT:g} с поролоном",
            f"ступень {v.STEP_H:g}, просвет для робота {v.ROBOT_PASS:g}",
        )
        front_elevation(
            shown,
            target / f"{variant.key}-front.png",
            f"{variant.title} — вид спереди",
            dim_texts=dims,
            body_color=tone["каркас"],
            door_color=tone["крышка"],
            accent=ACCENT,
        )
        side_elevation(
            shown,
            target / f"{variant.key}-side.png",
            f"{variant.title} — разрез сбоку (станция показана габаритом)",
            hide=("обшивка бок",),
            dim_texts=(
                f"сиденье {v.SEAT_D:g} глубиной, ступень {v.STEP_TREAD:g}",
                f"башня {v.ST_H:g} внутри, зазор сверху {v.GAP_ST_TOP:g}",
            ),
            body_color=tone["каркас"],
            door_color=tone["крышка"],
            accent=ACCENT,
        )
        # Тот же вид, но без обшивки и станции: видно, из чего собран каркас.
        front_elevation(
            poof.build(variant),
            target / f"{variant.key}-front-open.png",
            f"{variant.title} — каркас спереди, без обшивки",
            hide=("подступёнок", "обшивка"),
            dim_texts=(
                f"стойки и поперечины бруса {v.BEAM:g}×{v.BEAM:g}",
                f"ступень на {v.STEP_H:g}, рёбер под настилом {v.STEP_RIBS}",
            ),
            body_color=tone["каркас"],
            door_color=tone["крышка"],
            accent=ACCENT,
        )
        plan_view(
            shown,
            target / f"{variant.key}-plan.png",
            f"{variant.title} — план на уровне въезда робота",
            hide=("крышка", "настил", "обвязка", "подступёнок", "поперечина верх"),
            z_range=(0.0, v.ROBOT_PASS),
            dim_texts=(f"отсек станции {v.BAY_ST:g} в свету, станция {v.ST_W:g}",),
            body_color=tone["каркас"],
            door_color=tone["крышка"],
            accent=ACCENT,
        )

    print(f"Выгружено в {target}:")
    for path in sorted(target.iterdir()):
        print(f"  → {path.name}")

    show(build_all(), names=["cleaner-poof"])
