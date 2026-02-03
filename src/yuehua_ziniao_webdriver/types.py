"""类型定义模块

定义所有用于类型提示的 TypedDict、协议和类型别名。
"""

import sys
from typing import Any, Dict, List, Optional, Protocol, Union

# Python 3.8 兼容性处理
if sys.version_info >= (3, 8):
    from typing import Literal, TypedDict
else:
    from typing_extensions import Literal, TypedDict


# ============================================================================
# 店铺相关类型
# ============================================================================

class StoreInfo(TypedDict, total=False):
    """店铺信息"""
    browserOauth: str  # 店铺 OAuth 标识（必需）
    browserName: str  # 店铺名称（必需）
    browserId: Optional[str]  # 店铺 ID
    
    
class Store(TypedDict, total=False):
    """店铺对象（扩展版）"""
    browserOauth: str
    browserName: str
    browserId: Optional[str]
    # 可能的其他字段
    browserType: Optional[str]
    createTime: Optional[str]
    updateTime: Optional[str]


# ============================================================================
# 浏览器相关类型
# ============================================================================

class BrowserStartResult(TypedDict, total=False):
    """打开店铺返回结果"""
    statusCode: int  # 状态码，0 表示成功
    debuggingPort: int  # 调试端口
    browserOauth: str  # 店铺 OAuth 标识
    browserId: Optional[str]  # 店铺 ID
    ipDetectionPage: str  # IP 检测页面 URL
    launcherPage: str  # 启动页面 URL
    message: Optional[str]  # 错误消息


class BrowserStopResult(TypedDict):
    """关闭店铺返回结果"""
    statusCode: int
    message: Optional[str]


class BrowserListResult(TypedDict):
    """获取店铺列表返回结果"""
    statusCode: int
    browserList: List[Store]
    message: Optional[str]


# ============================================================================
# HTTP 通信相关类型
# ============================================================================

class HttpRequestData(TypedDict, total=False):
    """HTTP 请求数据"""
    action: str  # 操作类型
    requestId: str  # 请求 ID
    company: str  # 企业名称
    username: str  # 用户名
    password: str  # 密码
    # 其他可选字段
    browserId: Optional[str]
    browserOauth: Optional[str]
    isHeadless: Optional[int]
    isWebDriverReadOnlyMode: Optional[int]
    cookieTypeSave: Optional[int]
    injectJsInfo: Optional[str]


class HttpResponse(TypedDict, total=False):
    """HTTP 响应数据"""
    statusCode: int
    message: Optional[str]
    data: Optional[Dict[str, Any]]


# ============================================================================
# 配置相关类型
# ============================================================================

VersionType = Literal["v5", "v6"]
"""紫鸟客户端版本类型"""

PlatformType = Literal["Windows", "Darwin", "Linux"]
"""操作系统平台类型"""


class ConfigDict(TypedDict, total=False):
    """配置字典"""
    client_path: str  # 客户端路径（必需）
    socket_port: int  # 通信端口
    company: str  # 企业名称
    username: str  # 用户名
    password: str  # 密码
    version: VersionType  # 客户端版本
    request_timeout: int  # 请求超时时间（秒）
    max_retries: int  # 最大重试次数
    retry_delay: float  # 重试延迟（秒）


# ============================================================================
# 店铺操作选项
# ============================================================================

class StoreOpenOptions(TypedDict, total=False):
    """打开店铺的选项"""
    isWebDriverReadOnlyMode: int  # 只读模式，默认 0
    isprivacy: int  # 隐私模式，默认 0
    isHeadless: int  # 无头模式，默认 0
    cookieTypeSave: int  # Cookie 保存类型，默认 0
    jsInfo: str  # 注入的 JS 信息
    isWaitPluginUpdate: int  # 是否等待插件更新，默认 0
    cookieTypeLoad: int  # Cookie 加载类型，默认 0
    runMode: str  # 运行模式，默认 "1"
    isLoadUserPlugin: bool  # 是否加载用户插件，默认 False
    pluginIdType: int  # 插件 ID 类型，默认 1
    privacyMode: int  # 隐私模式，默认 0


# ============================================================================
# 协议定义
# ============================================================================

class BrowserSessionProtocol(Protocol):
    """浏览器会话协议"""
    
    def check_ip(self, ip_check_url: Optional[str] = None, timeout: int = 60) -> bool:
        """检查 IP 是否可用"""
        ...
    
    def get_tab(self):
        """获取当前标签页"""
        ...
    
    def close(self) -> None:
        """关闭浏览器会话"""
        ...
    
    def __enter__(self):
        """上下文管理器入口"""
        ...
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器退出"""
        ...


# ============================================================================
# 类型别名
# ============================================================================

ConfigSource = Union["ZiniaoConfig", ConfigDict, str]
"""配置源类型：可以是配置对象、字典或文件路径"""

StoreIdentifier = Union[str, int]
"""店铺标识：可以是 browserOauth 字符串或 browserId 数字"""
