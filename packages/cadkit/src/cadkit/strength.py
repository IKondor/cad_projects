"""Прикидочный расчёт полок на прогиб.

Для мебели «выдержит ли полка N кг» — почти всегда вопрос НЕ о разрушении,
а о прогибе. Запас по прочности у ЛДСП кратный, полка не ломается — она
провисает, и через год-два это выглядит как дешёвая мебель.

Ключевой эффект — ползучесть: под постоянной нагрузкой древесные плиты
продолжают деформироваться, и прогиб вырастает в 2-3 раза относительно
мгновенного. Считаем оба значения.

Модель: балка на двух опорах, равномерно распределённая нагрузка.
    прогиб  δ = 5·F·L³ / (384·E·I),   I = b·h³/12
    момент  M = F·L/8,                W = b·h²/6

Границы применимости — читать обязательно:
  * не учитывается вклад задней стенки и кромки/царги по переднему краю
    (они реально повышают жёсткость, так что расчёт консервативен);
  * опирание считается шарнирным; полка на жёстко закреплённых опорах
    прогнётся меньше;
  * нагрузка считается равномерной. Сосредоточенный груз посередине
    даёт прогиб примерно в 1,6 раза больше — см. `point_load=True`;
  * значения модуля упругости — справочные средние, разброс по партиям
    плиты легко ±30%.

Это инженерная прикидка, а не поверочный расчёт по нормам.
"""

from __future__ import annotations

from dataclasses import dataclass

__all__ = ["Material", "MATERIALS", "shelf_check", "max_span"]

G = 9.80665  # м/с²


@dataclass(frozen=True)
class Material:
    """Свойства листового материала."""

    name: str
    e_modulus: float  # модуль упругости, МПа
    bending_strength: float  # предел прочности при изгибе, МПа
    creep: float  # во сколько раз растёт прогиб под долгой нагрузкой


MATERIALS: dict[str, Material] = {
    "ЛДСП": Material("ЛДСП", e_modulus=2500, bending_strength=11, creep=2.5),
    "МДФ": Material("МДФ", e_modulus=3000, bending_strength=18, creep=2.5),
    "фанера": Material("фанера берёзовая", e_modulus=7000, bending_strength=40, creep=1.8),
    "массив": Material("массив сосны", e_modulus=10000, bending_strength=45, creep=1.6),
    # ОСП-3 (OSB-3) — влагостойкая ориентированно-стружечная плита. Значения
    # для НАПРАВЛЕНИЯ ВДОЛЬ главной оси (вдоль длинной стороны листа); поперёк
    # у ОСП модуль примерно вдвое ниже, поэтому детали, которые что-то несут,
    # надо резать вдоль. Ползучесть как у ДСП — плита прессованная, на смоле.
    "ОСП": Material("ОСП-3", e_modulus=3500, bending_strength=18, creep=2.5),
    # Сосновый брус каркаса — тот же массив сосны, отдельным именем для
    # читаемости расчётов: в мебели «массив» обычно про мебельный щит,
    # а тут именно брусок в раме.
    "брус": Material("брус сосновый", e_modulus=10000, bending_strength=45, creep=1.6),
}

# Практический критерий для мебельной полки: прогиб заметен глазом примерно
# от 1/200 пролёта. Это и берём как порог приемлемости.
ALLOWED_RATIO = 1 / 200


def shelf_check(
    span: float,
    depth: float,
    thickness: float,
    load_kg: float,
    material: str = "ЛДСП",
    point_load: bool = False,
    sustained: bool = True,
    layers: int = 1,
) -> dict[str, float | str | bool]:
    """Проверить полку. Все размеры в мм, нагрузка в кг.

    `span` — расстояние между опорами в свету, `depth` — глубина полки.

    `sustained` — постоянная ли нагрузка. Ползучесть накапливается только
    под долго лежащим грузом: книги, мешки, банки. Человек, который садится
    на тумбу, нагружает её эпизодически, и для такого случая надо смотреть
    мгновенный прогиб — ставь `sustained=False`.

    `layers` — сколько одинаковых плит работают параллельно (например, дно
    колонны, лежащее на крыше тумбы). НЕ склеенные между собой плиты делят
    нагрузку, но не суммируют толщину: жёсткость растёт линейно по числу
    слоёв, а не как куб суммарной толщины. Склеенные в монолит считай
    одной плитой соответствующей толщины.
    """
    if material not in MATERIALS:
        raise KeyError(f"Неизвестный материал {material!r}. Доступны: {', '.join(MATERIALS)}")

    mat = MATERIALS[material]
    force = load_kg * G  # Н
    moment_inertia = layers * depth * thickness**3 / 12  # мм⁴
    section_modulus = layers * depth * thickness**2 / 6  # мм³

    # Сосредоточенная нагрузка посередине даёт прогиб в 1,6 раза больше
    # при той же величине груза (коэффициент 1/48 против 5/384).
    coeff = (1 / 48) if point_load else (5 / 384)
    deflection = coeff * force * span**3 / (mat.e_modulus * moment_inertia)

    long_term = deflection * mat.creep
    allowed = span * ALLOWED_RATIO
    governing = long_term if sustained else deflection

    moment = force * span / (4 if point_load else 8)
    stress = moment / section_modulus

    return {
        "материал": mat.name,
        "пролёт, мм": span,
        "толщина, мм": thickness,
        "слоёв": layers,
        "нагрузка, кг": load_kg,
        "постоянная": sustained,
        "прогиб сразу, мм": round(deflection, 1),
        "прогиб через годы, мм": round(long_term, 1) if sustained else None,
        "допустимо, мм": round(allowed, 1),
        "проходит": governing <= allowed,
        "запас по разрушению": round(mat.bending_strength / stress, 1) if stress else float("inf"),
    }


def max_span(
    depth: float,
    thickness: float,
    load_kg: float,
    material: str = "ЛДСП",
    point_load: bool = False,
) -> float:
    """Максимальный пролёт, при котором полка проходит по прогибу, мм.

    Ищем перебором с шагом 5 мм — надёжнее, чем аналитика, и мгновенно.
    """
    best = 0.0
    for span in range(100, 3001, 5):
        if shelf_check(span, depth, thickness, load_kg, material, point_load)["проходит"]:
            best = float(span)
        else:
            break
    return best
