"""Вспомогательные функции, специфичные для этого проекта.

Общая для колонны и тумбы механика: как рисуется панель, в какой цвет
красится каркас/фасад, как печатается строка результата проверки прочности.
Универсальные вещи (расчёт прогиба, экспорт, чертежи) — в пакете `cadkit`.

Система координат: начало — левый ПЕРЕДНИЙ нижний угол всей конструкции.
    X — ширина, вправо, если смотреть на шкаф спереди,
    Y — глубина, вглубь к стене; фасады при Y < 0, открытая (задняя)
        сторона корпуса — у стены,
    Z — высота от пола.
Подробнее, включая положение наблюдателя, — см. README.md.
"""

import cadquery as cq
import variables as v

__all__ = ["panel", "tone", "report_check"]


def panel(
    length: float, depth: float, height: float, at: tuple[float, float, float]
) -> cq.Workplane:
    """Прямоугольная деталь с углом в точке `at`."""
    return cq.Workplane("XY").box(length, depth, height, centered=False).translate(at)


def tone() -> tuple[cq.Color, cq.Color]:
    """Цвет каркаса и цвет фасада для текущей палитры (`v.PALETTE`)."""
    palette = v.PALETTES[v.PALETTE]
    return (
        cq.Color(palette["каркас"]),
        cq.Color(palette["фасад"]),
    )


def report_check(label: str, check: dict) -> None:
    """Напечатать одну строку результата `shelf_check` из cadkit."""
    verdict = "проходит" if check["проходит"] else "НЕ ПРОХОДИТ"
    shown = check["прогиб через годы, мм"] or check["прогиб сразу, мм"]
    horizon = "через годы" if check["постоянная"] else "мгновенно"
    print(
        f"  {label:<38} {verdict:<11} прогиб {shown:>5} мм {horizon}"
        f", допуск {check['допустимо, мм']:g}, запас ×{check['запас по разрушению']}"
    )
