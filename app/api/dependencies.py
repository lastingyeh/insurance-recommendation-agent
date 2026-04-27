from __future__ import annotations

from functools import lru_cache

from fastapi import Request

from app.container import AppContainer, build_app_container
from app.config import load_runtime_config


@lru_cache(maxsize=1)
def _get_cached_container() -> AppContainer:
    return build_app_container(load_runtime_config())


def get_container(request: Request | None = None) -> AppContainer:
    if request is not None:
        container = getattr(request.app.state, "container", None)
        if container is not None:
            return container

    return _get_cached_container()


def reset_dependency_caches() -> None:
    _get_cached_container.cache_clear()
