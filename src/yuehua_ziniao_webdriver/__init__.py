"""紫鸟浏览器自动化 Python SDK

一个用于控制紫鸟浏览器的 Python 库，提供店铺管理、浏览器自动化等功能。

基本使用:
    >>> from yuehua_ziniao_webdriver import ZiniaoClient, ZiniaoConfig
    >>> 
    >>> config = ZiniaoConfig(
    ...     client_path=r"D:\ziniao\ziniao.exe",
    ...     company="企业名",
    ...     username="用户名",
    ...     password="密码"
    ... )
    >>> 
    >>> with ZiniaoClient(config) as client:
    ...     # 通过名称打开店铺
    ...     session = client.open_store_by_name("我的店铺")
    ...     if session.check_ip():
    ...         tab = session.get_tab()
    ...         tab.get("https://example.com")
"""

__version__ = "0.1.6"
__author__ = "Yuehua"
__email__ = "shengxi_2000@outlook.com"

# ============================================================================
# 核心类（推荐使用）
# ============================================================================

from .client import ZiniaoClient
from .config import ZiniaoConfig
from .browser import BrowserSession

# ============================================================================
# 异常类
# ============================================================================

from .exceptions import (
    ZiniaoError,
    ConfigurationError,
    AuthenticationError,
    ClientNotStartedError,
    BrowserStartError,
    ProcessError,
    CommunicationError,
    TimeoutError,
    StoreError,
    StoreNotFoundError,
    MultipleStoresFoundError,
    StoreOperationError,
    IPCheckError,
    CoreUpdateError,
    UnsupportedVersionError,
)

# ============================================================================
# 类型定义
# ============================================================================

from .types import (
    Store,
    StoreInfo,
    BrowserStartResult,
    StoreOpenOptions,
    VersionType,
    PlatformType,
)

# ============================================================================
# 工具函数
# ============================================================================

from .utils import (
    get_platform,
    is_windows,
    is_mac,
    is_linux,
    delete_cache,
    get_cache_size,
    format_bytes,
    setup_logging,
)

# ============================================================================
# 向后兼容的低层 API（高级用户）
# ============================================================================

from .http_client import HttpClient
from .process import ProcessManager
from .store import StoreManager
from .browser import get_browser

# ============================================================================
# 导出列表
# ============================================================================

__all__ = [
    # 版本信息
    "__version__",
    "__author__",
    "__email__",
    
    # 核心类
    "ZiniaoClient",
    "ZiniaoConfig",
    "BrowserSession",
    
    # 异常类
    "ZiniaoError",
    "ConfigurationError",
    "AuthenticationError",
    "ClientNotStartedError",
    "BrowserStartError",
    "ProcessError",
    "CommunicationError",
    "TimeoutError",
    "StoreError",
    "StoreNotFoundError",
    "MultipleStoresFoundError",
    "StoreOperationError",
    "IPCheckError",
    "CoreUpdateError",
    "UnsupportedVersionError",
    
    # 类型定义
    "Store",
    "StoreInfo",
    "BrowserStartResult",
    "StoreOpenOptions",
    "VersionType",
    "PlatformType",
    
    # 工具函数
    "get_platform",
    "is_windows",
    "is_mac",
    "is_linux",
    "delete_cache",
    "get_cache_size",
    "format_bytes",
    "setup_logging",
    
    # 低层 API
    "HttpClient",
    "ProcessManager",
    "StoreManager",
    "get_browser",
]
