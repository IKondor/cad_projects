"""Ортогональные виды сборки в PNG.

Нужны для двух вещей: приложить к ТЗ понятную картинку и — не менее важно —
проверять себя. По 3D во вьюере легко перепутать право и лево; плоский вид
спереди с подписями не оставляет места для трактовок.

Работает для сборок из прямоугольных панелей: каждая деталь рисуется своим
габаритным прямоугольником. Для скруглений и вырезов вид будет приблизительным.

СОГЛАШЕНИЕ О ВИДЕ СПЕРЕДИ. Наблюдатель стоит перед изделием со стороны
малых Y и смотрит в сторону +Y, верх — +Z. При этом +X идёт ВПРАВО
(встань лицом на север, вверх — небо: правая рука показывает на восток).
Значит фасады изделия должны смотреть в сторону МАЛЫХ Y.
"""

from __future__ import annotations

from pathlib import Path

import cadquery as cq
import matplotlib

matplotlib.use("Agg")  # без GUI: скрипты должны работать headless

import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Rectangle  # noqa: E402

__all__ = ["front_elevation", "side_elevation", "plan_view"]


def _parts(asm: cq.Assembly) -> list[tuple[str, cq.occ_impl.geom.BoundBox]]:
    """Имена деталей и их габаритные ящики в глобальных координатах."""
    out = []
    for name, child in asm.objects.items():
        if child.obj is None:  # корень сборки
            continue
        out.append((name, child.obj.val().BoundingBox()))
    return out


def front_elevation(
    asm: cq.Assembly,
    path: Path,
    title: str = "",
    hide: tuple[str, ...] = (),
    dim_texts: tuple[str, ...] = (),
    body_color: str = "#e8d5b0",
    door_color: str = "#d9a441",
    accent: tuple[str, ...] = ("фасад",),
) -> Path:
    """Вид спереди в PNG.

    `hide` — подстроки имён деталей, которые не рисовать (например «фасад»,
    чтобы показать внутреннее устройство). `dim_texts` — строки подписи снизу.

    Цвета стоит передавать те же, что и в 3D-модели: тогда картинку можно
    показывать как вариант отделки, а не только как чертёж.
    """
    return _elevation(
        asm,
        path,
        axis="x",
        title=title or "Вид спереди",
        hide=hide,
        dim_texts=dim_texts,
        body_color=body_color,
        door_color=door_color,
        accent=accent,
    )


def side_elevation(
    asm: cq.Assembly,
    path: Path,
    title: str = "",
    hide: tuple[str, ...] = (),
    dim_texts: tuple[str, ...] = (),
    body_color: str = "#e8d5b0",
    door_color: str = "#d9a441",
    accent: tuple[str, ...] = ("фасад",),
) -> Path:
    """Вид сбоку в PNG. Показывает глубины — то, чего не видно на виде спереди.

    По горизонтали отложена Y: слева фасады изделия, справа стена.
    """
    return _elevation(
        asm,
        path,
        axis="y",
        title=title or "Вид сбоку",
        hide=hide,
        dim_texts=dim_texts,
        body_color=body_color,
        door_color=door_color,
        accent=accent,
    )


def plan_view(
    asm: cq.Assembly,
    path: Path,
    title: str = "",
    hide: tuple[str, ...] = (),
    dim_texts: tuple[str, ...] = (),
    body_color: str = "#e8d5b0",
    door_color: str = "#d9a441",
    z_range: tuple[float, float] | None = None,
    accent: tuple[str, ...] = ("фасад",),
) -> Path:
    """Вид сверху (горизонтальное сечение) в PNG.

    Единственный вид, на котором виден скос в плане. `z_range` ограничивает
    высоту, чтобы взять сечение на нужном уровне: без него верхние детали
    закроют нижние.

    Здесь деталь рисуется НЕ габаритным прямоугольником, а настоящим
    контуром в плане — иначе скос выглядел бы прямым углом.
    """
    parts = []
    for name, child in asm.objects.items():
        if child.obj is None or any(h.lower() in name.lower() for h in hide):
            continue
        bb = child.obj.val().BoundingBox()
        if z_range and (bb.zmax <= z_range[0] or bb.zmin >= z_range[1]):
            continue
        parts.append((name, child.obj))

    if not parts:
        raise ValueError("Нечего рисовать: все детали отфильтрованы")

    fig, ax = plt.subplots(figsize=(9, 8))
    xs, ys = [], []

    for name, shape in parts:
        is_door = any(a.lower() in name.lower() for a in accent)
        for poly in _plan_outlines(shape):
            px = [p[0] for p in poly]
            py = [p[1] for p in poly]
            xs += px
            ys += py
            ax.fill(
                px,
                py,
                facecolor=door_color if is_door else body_color,
                edgecolor="#5a4632",
                linewidth=0.8,
                alpha=0.45 if is_door else 1.0,
            )

    margin = max(max(xs) - min(xs), max(ys) - min(ys)) * 0.08
    ax.set_xlim(min(xs) - margin, max(xs) + margin)
    ax.set_ylim(min(ys) - margin, max(ys) + margin)
    ax.set_aspect("equal")
    ax.set_xlabel("X, мм  →  вправо, если смотреть на шкаф спереди")
    ax.set_ylabel("Y, мм  →  вглубь, к стене (стена сверху)")
    ax.grid(True, linewidth=0.3, alpha=0.4)

    header = title or "Вид сверху"
    if dim_texts:
        header += "\n" + "\n".join(dim_texts)
    ax.set_title(header, fontsize=10)

    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)
    return path


def _plan_outlines(shape: cq.Workplane) -> list[list[tuple[float, float]]]:
    """Контуры детали в плане — по нижней горизонтальной грани.

    Для призматических панелей (а это все детали корпусной мебели) нижняя
    грань полностью описывает форму в плане, включая скосы.
    """
    solid = shape.val()
    bb = solid.BoundingBox()
    outlines = []

    for face in solid.Faces():
        fbb = face.BoundingBox()
        is_horizontal = abs(fbb.zlen) < 1e-6
        if not is_horizontal or abs(fbb.zmin - bb.zmin) > 1e-6:
            continue
        for wire in face.Wires():
            pts = [(v.X, v.Y) for v in wire.Vertices()]
            if len(pts) >= 3:
                outlines.append(pts)

    return outlines


def _elevation(
    asm: cq.Assembly,
    path: Path,
    axis: str,
    title: str,
    hide: tuple[str, ...],
    dim_texts: tuple[str, ...],
    body_color: str,
    door_color: str,
    accent: tuple[str, ...] = ("фасад",),
) -> Path:
    """Общая машинерия обоих видов. `axis` — что откладывать по горизонтали."""
    parts = [(n, bb) for n, bb in _parts(asm) if not any(h.lower() in n.lower() for h in hide)]
    if not parts:
        raise ValueError("Нечего рисовать: все детали отфильтрованы")

    if axis == "x":
        # Рисуем от дальних к ближним, чтобы передние перекрывали задние.
        parts.sort(key=lambda p: -p[1].ymin)
        span = lambda bb: (bb.xmin, bb.xlen)  # noqa: E731
        label = "X, мм  →  вправо, если смотреть на шкаф спереди"
        figsize = (7, 11)
    else:
        parts.sort(key=lambda p: -p[1].xmin)
        span = lambda bb: (bb.ymin, bb.ylen)  # noqa: E731
        label = "Y, мм  →  вглубь, к стене (слева фасады)"
        figsize = (7, 11)

    fig, ax = plt.subplots(figsize=figsize)

    for name, bb in parts:
        is_door = any(a.lower() in name.lower() for a in accent)
        start, length = span(bb)
        ax.add_patch(
            Rectangle(
                (start, bb.zmin),
                length,
                bb.zlen,
                facecolor=door_color if is_door else body_color,
                edgecolor="#5a4632",
                linewidth=0.8,
                alpha=0.45 if is_door else 1.0,
            )
        )

    starts = [span(bb)[0] for _, bb in parts]
    ends = [span(bb)[0] + span(bb)[1] for _, bb in parts]
    zs = [bb.zmin for _, bb in parts] + [bb.zmax for _, bb in parts]
    margin = max(max(ends) - min(starts), max(zs) - min(zs)) * 0.08

    ax.set_xlim(min(starts) - margin, max(ends) + margin)
    ax.set_ylim(min(zs) - margin, max(zs) + margin)
    ax.set_aspect("equal")
    ax.set_xlabel(label)
    ax.set_ylabel("Z, мм  →  вверх от пола")
    ax.grid(True, linewidth=0.3, alpha=0.4)

    header = title
    if dim_texts:
        header += "\n" + "\n".join(dim_texts)
    ax.set_title(header, fontsize=10)

    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)
    return path
