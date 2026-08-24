"""Вспомогательные функции проекта: как рисуется деталь и как печатается проверка.

Универсальные вещи (прогиб, экспорт, чертежи) — в пакете `cadkit`.
"""

import cadquery as cq
import variables as v

__all__ = ["panel", "tone", "report_check", "ok"]


def panel(
    length: float, depth: float, height: float, at: tuple[float, float, float]
) -> cq.Workplane:
    """Прямоугольная деталь с углом в точке `at`. length по X, depth по Y."""
    return cq.Workplane("XY").box(length, depth, height, centered=False).translate(at)


def tone() -> tuple[cq.Color, cq.Color]:
    """Цвет каркаса и цвет крышки для текущей палитры (`v.PALETTE`)."""
    palette = v.PALETTES[v.PALETTE]
    return cq.Color(palette["каркас"]), cq.Color(palette["крышка"])


def ok(flag: bool) -> str:
    return "✓" if flag else "✗ НЕ ПРОХОДИТ"


def report_check(label: str, check: dict) -> None:
    """Напечатать одну строку результата `shelf_check` из cadkit."""
    verdict = "проходит" if check["проходит"] else "НЕ ПРОХОДИТ"
    shown = check["прогиб через годы, мм"] or check["прогиб сразу, мм"]
    horizon = "через годы" if check["постоянная"] else "мгновенно"
    print(
        f"  {label:<44} {verdict:<11} прогиб {shown:>5} мм {horizon}"
        f", допуск {check['допустимо, мм']:g}, запас ×{check['запас по разрушению']}"
    )
