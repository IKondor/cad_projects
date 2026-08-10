"""Общие хелперы для CAD-проектов монорепо.

Единица измерения во всех проектах — МИЛЛИМЕТР. CadQuery сам по себе безразмерный,
поэтому договорённость держится соглашением: 2 метра == 2000.
"""

from cadkit.export import export, out_dir
from cadkit.view import show, viewer_available

__all__ = ["export", "out_dir", "show", "viewer_available"]
