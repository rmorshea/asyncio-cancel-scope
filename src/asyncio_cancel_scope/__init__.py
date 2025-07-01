from __future__ import annotations

from importlib.metadata import PackageNotFoundError
from importlib.metadata import version

from asyncio_cancel_scope.core import cancel_group as cancel_group
from asyncio_cancel_scope.core import cancel_scope as cancel_scope

try:
    __version__ = version(__name__)
except PackageNotFoundError:  # nocov
    __version__ = "0.0.0"
