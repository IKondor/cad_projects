"""Деталировка: список панелей для раскроя и кромления.

Это то, что реально уезжает мебельщику. Геометрия нужна, чтобы увидеть изделие
и не ошибиться в стыковках, но заказ оформляется по таблице панелей.

Соглашение по размерам панели:
    length  — размер ВДОЛЬ текстуры (для ЛДСП с рисунком это важно),
    width   — поперёк текстуры,
    оба в миллиметрах, в чистовом размере (после кромления).

Кромка описывается по четырём сторонам панели строкой вида "2/0/1/1":
порядок L1/L2/W1/W2 — две длинные стороны, затем две короткие.
Цифра — толщина кромки в мм, 0 — без кромки.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

__all__ = ["Panel", "spec_markdown", "spec_csv", "totals"]


@dataclass(frozen=True)
class Panel:
    """Одна деталь раскроя."""

    name: str
    length: float
    width: float
    thickness: float
    qty: int
    material: str
    edges: str = "0/0/0/0"
    note: str = ""

    @property
    def area_m2(self) -> float:
        """Площадь всех экземпляров детали, м²."""
        return self.length * self.width * self.qty / 1e6

    @property
    def edge_len_m(self) -> float:
        """Суммарная длина кромки на всех экземплярах, погонные метры."""
        sides = self.edges.split("/")
        if len(sides) != 4:
            raise ValueError(
                f"{self.name}: кромка должна задаваться как 'L1/L2/W1/W2', а не {self.edges!r}"
            )

        lengths = (self.length, self.length, self.width, self.width)
        total = sum(dim for dim, thk in zip(lengths, sides, strict=True) if _thickness(thk) > 0)
        return total * self.qty / 1000


def _thickness(raw: str) -> float:
    raw = raw.strip()
    try:
        return float(raw.replace(",", "."))
    except ValueError:
        return 0.0


def totals(panels: list[Panel]) -> dict[str, float]:
    """Сводка по спецификации: количество, площадь, погонаж кромки."""
    return {
        "деталей, шт": sum(p.qty for p in panels),
        "площадь, м²": round(sum(p.area_m2 for p in panels), 3),
        "кромка, п.м": round(sum(p.edge_len_m for p in panels), 2),
    }


def spec_markdown(panels: list[Panel]) -> str:
    """Спецификация в виде markdown-таблицы — для ТЗ и переписки."""
    columns = [
        ("№", "---"),
        ("Деталь", "---"),
        ("Длина", "---:"),
        ("Ширина", "---:"),
        ("Толщ.", "---:"),
        ("Кол-во", "---:"),
        ("Материал", "---"),
        ("Кромка L1/L2/W1/W2", "---"),
        ("Примечание", "---"),
    ]
    head = (
        "| " + " | ".join(name for name, _ in columns) + " |\n"
        "|" + "|".join(align for _, align in columns) + "|\n"
    )
    # Длина и ширина — в ЦЕЛЫХ миллиметрах: раскрой всё равно ведётся с
    # допуском около ±1 мм, а дробные доли в таблице только мешают читать.
    # Толщина остаётся дробной — там бывает 0.4 мм кромка.
    rows = "".join(
        f"| {i} | {p.name} | {p.length:.0f} | {p.width:.0f} | {p.thickness:g} | {p.qty} "
        f"| {p.material} | {p.edges} | {p.note} |\n"
        for i, p in enumerate(panels, 1)
    )
    summary = "\n".join(f"- **{k}**: {v}" for k, v in totals(panels).items())
    return head + rows + "\n" + summary + "\n"


def spec_csv(panels: list[Panel], path: Path) -> Path:
    """Спецификация в CSV — многие мебельщики просят именно таблицу."""
    with path.open("w", newline="", encoding="utf-8-sig") as fh:
        writer = csv.writer(fh, delimiter=";")
        writer.writerow(
            [
                "№",
                "Деталь",
                "Длина, мм",
                "Ширина, мм",
                "Толщина, мм",
                "Кол-во",
                "Материал",
                "Кромка",
                "Примечание",
            ]
        )
        for i, p in enumerate(panels, 1):
            writer.writerow(
                [
                    i,
                    p.name,
                    f"{p.length:.0f}",
                    f"{p.width:.0f}",
                    f"{p.thickness:g}",
                    p.qty,
                    p.material,
                    p.edges,
                    p.note,
                ]
            )
    return path
