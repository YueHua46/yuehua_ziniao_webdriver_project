"""异常定义模块

定义所有自定义异常类，提供清晰的错误层次结构。
"""

from typing import Optional, Any


class ZiniaoError(Exception):
    """紫鸟浏览器 SDK 基础异常类
    
    所有自定义异常的基类。
    """
    
    def __init__(self, message: str, details: Optional[Any] = None) -> None:
        """初始化异常
        
        Args:
            message: 错误消息
            details: 额外的错误详情（可选）
        """
        self.message = message
        self.details = details
        super().__init__(message)
    
    def __str__(self) -> str:
        if self.details:
            return f"{self.message} (详情: {self.details})"
        return self.message


class ConfigurationError(ZiniaoError):
    """配置错误
    
    当配置参数无效或缺失时抛出。
    """
    pass


class AuthenticationError(ZiniaoError):
    """认证失败错误
    
    当登录紫鸟客户端失败时抛出。
    """
    pass


class ClientNotStartedError(ZiniaoError):
    """客户端未启动错误
    
    当尝试操作未启动的客户端时抛出。
    """
    
    def __init__(self, message: str = "紫鸟客户端尚未启动，请先调用 start() 方法") -> None:
        super().__init__(message)


class BrowserStartError(ZiniaoError):
    """浏览器启动失败错误
    
    当启动紫鸟客户端进程失败时抛出。
    """
    pass


class ProcessError(ZiniaoError):
    """进程操作错误
    
    当进程管理操作失败时抛出（如关闭进程失败）。
    """
    pass


class CommunicationError(ZiniaoError):
    """通信错误
    
    当与紫鸟客户端 HTTP 通信失败时抛出。
    """
    pass


class TimeoutError(ZiniaoError):
    """超时错误
    
    当操作超时时抛出。
    """
    pass


class StoreError(ZiniaoError):
    """店铺操作基础错误
    
    所有店铺相关错误的基类。
    """
    pass


class StoreNotFoundError(StoreError):
    """店铺未找到错误
    
    当按名称或 ID 查找店铺但未找到时抛出。
    """
    
    def __init__(
        self, 
        store_identifier: str, 
        search_type: str = "名称"
    ) -> None:
        """初始化错误
        
        Args:
            store_identifier: 店铺标识（名称或 ID）
            search_type: 搜索类型（"名称" 或 "ID"）
        """
        message = f"未找到匹配的店铺：{search_type}='{store_identifier}'"
        super().__init__(message, {"identifier": store_identifier, "type": search_type})
        self.store_identifier = store_identifier
        self.search_type = search_type


class MultipleStoresFoundError(StoreError):
    """找到多个店铺错误
    
    当按名称搜索店铺但找到多个匹配结果时抛出。
    """
    
    def __init__(
        self, 
        store_name: str, 
        count: int,
        store_names: Optional[list] = None
    ) -> None:
        """初始化错误
        
        Args:
            store_name: 搜索的店铺名称
            count: 找到的店铺数量
            store_names: 找到的店铺名称列表（可选）
        """
        if store_names:
            message = (
                f"找到 {count} 个匹配的店铺：'{store_name}'。"
                f"匹配的店铺：{', '.join(store_names)}"
            )
        else:
            message = f"找到 {count} 个匹配的店铺：'{store_name}'"
        
        super().__init__(
            message, 
            {"search_name": store_name, "count": count, "stores": store_names}
        )
        self.store_name = store_name
        self.count = count
        self.store_names = store_names


class StoreOperationError(StoreError):
    """店铺操作失败错误
    
    当打开、关闭店铺等操作失败时抛出。
    """
    
    def __init__(
        self, 
        operation: str, 
        store_id: str, 
        status_code: Optional[int] = None,
        message: Optional[str] = None
    ) -> None:
        """初始化错误
        
        Args:
            operation: 操作类型（如 "打开"、"关闭"）
            store_id: 店铺 ID
            status_code: 状态码（可选）
            message: 错误消息（可选）
        """
        error_msg = f"{operation}店铺失败：{store_id}"
        if status_code is not None:
            error_msg += f"，状态码：{status_code}"
        if message:
            error_msg += f"，消息：{message}"
        
        super().__init__(
            error_msg,
            {
                "operation": operation,
                "store_id": store_id,
                "status_code": status_code,
                "message": message
            }
        )
        self.operation = operation
        self.store_id = store_id
        self.status_code = status_code


class IPCheckError(ZiniaoError):
    """IP 检测错误
    
    当 IP 检测失败或超时时抛出。
    """
    pass


class CoreUpdateError(ZiniaoError):
    """内核更新错误
    
    当更新浏览器内核失败时抛出。
    """
    pass


class UnsupportedVersionError(ZiniaoError):
    """不支持的版本错误
    
    当客户端版本不支持某个功能时抛出。
    """
    
    def __init__(
        self, 
        feature: str, 
        required_version: Optional[str] = None
    ) -> None:
        """初始化错误
        
        Args:
            feature: 不支持的功能名称
            required_version: 需要的版本（可选）
        """
        message = f"当前客户端版本不支持功能：{feature}"
        if required_version:
            message += f"，请升级到 {required_version} 或更高版本"
        
        super().__init__(message, {"feature": feature, "required_version": required_version})
        self.feature = feature
        self.required_version = required_version
