"""Просмотр моделей в OCP CAD Viewer.

Вьюер живёт в отдельном процессе (расширение VSCode «OCP CAD Viewer» либо
`uv run python -m ocp_vscode`), модель отправляется в него по localhost.

Если вьюер не запущен — тихо пропускаем просмотр, чтобы модели оставались
пригодными для headless-запуска из консоли и CI. Порт проверяем сами:
ocp_vscode при отсутствии вьюера падает с невнятным трейсбеком внутри
websockets вместо понятной ошибки.
"""

from __future__ import annotations

import os
import socket

__all__ = ["show", "viewer_available"]

DEFAULT_PORT = 3939


def _port() -> int:
    """Порт вьюера: переменная окружения OCP_PORT, иначе штатный 3939."""
    raw = os.environ.get("OCP_PORT")
    if raw and raw.isdigit():
        return int(raw)
    return DEFAULT_PORT


def viewer_available(timeout: float = 0.2) -> bool:
    """Слушает ли кто-нибудь порт вьюера."""
    try:
        with socket.create_connection(("127.0.0.1", _port()), timeout=timeout):
            return True
    except OSError:
        return False


def show(*models, names: list[str] | None = None, quiet: bool = True) -> bool:
    """Показать модели во вьюере. True — показали, False — вьюер недоступен."""
    if not viewer_available():
        if not quiet:
            raise RuntimeError(
                f"OCP CAD Viewer не слушает порт {_port()}. "
                "Запустите расширение в VSCode или `uv run python -m ocp_vscode`."
            )
        print(f"[cadkit] OCP CAD Viewer не запущен (порт {_port()}), просмотр пропущен.")
        return False

    from ocp_vscode import show as _show

    _show(*models, names=names)
    return True
