"""Общие хелперы для CAD-проектов монорепо.

Единица измерения во всех проектах — МИЛЛИМЕТР. CadQuery сам по себе безразмерный,
поэтому договорённость держится соглашением: 2 метра == 2000.
"""

from cadkit.export import export, out_dir
from cadkit.panels import Panel, spec_csv, spec_markdown, totals
from cadkit.strength import MATERIALS, Material, max_span, shelf_check
from cadkit.view import show, viewer_available
from cadkit.views import front_elevation, plan_view, side_elevation

__all__ = [
    "MATERIALS",
    "Material",
    "Panel",
    "export",
    "front_elevation",
    "max_span",
    "out_dir",
    "plan_view",
    "shelf_check",
    "show",
    "side_elevation",
    "spec_csv",
    "spec_markdown",
    "totals",
    "viewer_available",
]
