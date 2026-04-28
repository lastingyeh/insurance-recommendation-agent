from __future__ import annotations

from functools import lru_cache

from fastapi import Request

from app.container import AppContainer, build_app_container
from app.config import load_runtime_config


@lru_cache(maxsize=1)
def _get_cached_container() -> AppContainer:
    """
    獲取並快取應用程式容器實例。

    使用 lru_cache(maxsize=1) 確保在同一個執行環境中，
    只會建立並保存一個 AppContainer 實例，避免重複載入設定檔與建立物件。
    """
    return build_app_container(load_runtime_config())


def get_container(request: Request | None = None) -> AppContainer:
    """
    取得應用程式的相依性容器。

    此函式通常作為 FastAPI 的 Dependency Injection 使用。
    如果提供了 request 參數，它會優先嘗試從 app.state 中尋找已經綁定的容器。
    這在測試環境或生命週期事件中手動注入依賴時非常有用。
    如果找不到或是沒有提供 request，則會回退到使用快取的全域容器。

    Args:
        request: FastAPI 請求物件，非必填。

    Returns:
        AppContainer: 應用程式容器實例，包含所有需要的服務與相依性。
    """
    if request is not None:
        # 嘗試從 FastAPI 應用程式的狀態中取得容器
        container = getattr(request.app.state, "container", None)
        if container is not None:
            return container

    # 如果沒有找到，回傳快取的全域容器實例
    return _get_cached_container()


def reset_dependency_caches() -> None:
    """
    重設相依性快取。

    清除 _get_cached_container 的快取。
    這在單元測試或整合測試中，或是當執行階段設定發生改變而需要強制重新建立容器時非常有用。
    """
    _get_cached_container.cache_clear()
