"""工具函数模块

提供平台检测、缓存管理等通用工具函数。
"""

import os
import platform
import shutil
import logging
from pathlib import Path
from typing import Optional

from .types import PlatformType
from .exceptions import ZiniaoError

logger = logging.getLogger(__name__)


# ============================================================================
# 平台检测
# ============================================================================

def get_platform() -> PlatformType:
    """获取当前操作系统平台
    
    Returns:
        PlatformType: "Windows", "Darwin" (macOS), 或 "Linux"
    """
    system = platform.system()
    if system in ("Windows", "Darwin", "Linux"):
        return system  # type: ignore
    return "Linux"  # 默认返回 Linux


def is_windows() -> bool:
    """判断是否为 Windows 平台
    
    Returns:
        bool: Windows 返回 True
    """
    return platform.system() == "Windows"


def is_mac() -> bool:
    """判断是否为 macOS 平台
    
    Returns:
        bool: macOS 返回 True
    """
    return platform.system() == "Darwin"


def is_linux() -> bool:
    """判断是否为 Linux 平台
    
    Returns:
        bool: Linux 返回 True
    """
    return platform.system() == "Linux"


# ============================================================================
# 缓存管理
# ============================================================================

def get_default_cache_path() -> Optional[str]:
    """获取默认的缓存路径
    
    仅适用于 Windows 平台。
    
    Returns:
        Optional[str]: 缓存路径，如果不是 Windows 返回 None
    """
    if not is_windows():
        return None
    
    local_appdata = os.getenv('LOCALAPPDATA')
    if local_appdata:
        return os.path.join(local_appdata, 'SuperBrowser')
    
    return None


def delete_cache(cache_path: Optional[str] = None) -> bool:
    """删除缓存目录
    
    仅适用于 Windows 平台。非必要操作，仅在店铺特别多、硬盘空间不够时使用。
    
    警告：
        - 当有店铺正在运行时，删除可能会失败
        - 此操作会删除所有店铺的缓存数据
    
    Args:
        cache_path: 自定义缓存路径，如果为 None 则使用默认路径
        
    Returns:
        bool: 成功删除返回 True，否则返回 False
    """
    if not is_windows():
        logger.warning("删除缓存功能仅支持 Windows 平台")
        return False
    
    # 确定缓存路径
    if cache_path is None:
        cache_path = get_default_cache_path()
    else:
        cache_path = os.path.join(cache_path, 'SuperBrowser')
    
    if cache_path is None:
        logger.error("无法确定缓存路径")
        return False
    
    # 检查路径是否存在
    if not os.path.exists(cache_path):
        logger.info(f"缓存路径不存在，无需删除：{cache_path}")
        return True
    
    # 删除缓存
    try:
        shutil.rmtree(cache_path)
        logger.info(f"成功删除缓存：{cache_path}")
        return True
    except PermissionError as e:
        logger.error(
            f"删除缓存失败（权限不足），可能有店铺正在运行：{cache_path}, "
            f"错误：{e}"
        )
        return False
    except Exception as e:
        logger.error(f"删除缓存失败：{cache_path}, 错误：{e}")
        return False


def get_cache_size(cache_path: Optional[str] = None) -> int:
    """获取缓存目录大小（字节）
    
    Args:
        cache_path: 自定义缓存路径，如果为 None 则使用默认路径
        
    Returns:
        int: 缓存大小（字节），如果路径不存在返回 0
    """
    if not is_windows():
        return 0
    
    # 确定缓存路径
    if cache_path is None:
        cache_path = get_default_cache_path()
    else:
        cache_path = os.path.join(cache_path, 'SuperBrowser')
    
    if cache_path is None or not os.path.exists(cache_path):
        return 0
    
    total_size = 0
    try:
        for dirpath, dirnames, filenames in os.walk(cache_path):
            for filename in filenames:
                filepath = os.path.join(dirpath, filename)
                if os.path.exists(filepath):
                    total_size += os.path.getsize(filepath)
    except Exception as e:
        logger.error(f"计算缓存大小失败：{e}")
    
    return total_size


def format_bytes(size_bytes: int) -> str:
    """格式化字节大小为人类可读格式
    
    Args:
        size_bytes: 字节数
        
    Returns:
        str: 格式化后的字符串（如 "1.5 GB"）
    """
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} PB"


# ============================================================================
# 路径处理
# ============================================================================

def normalize_path(path: str) -> str:
    """规范化路径
    
    将路径转换为绝对路径，并处理不同平台的路径分隔符。
    
    Args:
        path: 原始路径
        
    Returns:
        str: 规范化后的绝对路径
    """
    return os.path.abspath(os.path.expanduser(path))


def ensure_dir(directory: str) -> None:
    """确保目录存在，不存在则创建
    
    Args:
        directory: 目录路径
        
    Raises:
        ZiniaoError: 创建目录失败时
    """
    try:
        Path(directory).mkdir(parents=True, exist_ok=True)
    except Exception as e:
        raise ZiniaoError(f"创建目录失败：{directory}", {"error": str(e)})


# ============================================================================
# 字符串处理
# ============================================================================

def fuzzy_match(text: str, pattern: str, case_sensitive: bool = False) -> bool:
    """模糊匹配字符串
    
    检查 text 是否包含 pattern。
    
    Args:
        text: 被搜索的文本
        pattern: 搜索模式
        case_sensitive: 是否区分大小写，默认 False
        
    Returns:
        bool: 匹配返回 True
    """
    if not case_sensitive:
        text = text.lower()
        pattern = pattern.lower()
    
    return pattern in text


def exact_match(text: str, pattern: str, case_sensitive: bool = False) -> bool:
    """精确匹配字符串
    
    Args:
        text: 被比较的文本
        pattern: 比较模式
        case_sensitive: 是否区分大小写，默认 False
        
    Returns:
        bool: 完全匹配返回 True
    """
    if not case_sensitive:
        text = text.lower()
        pattern = pattern.lower()
    
    return text == pattern


# ============================================================================
# 日志配置
# ============================================================================

def setup_logging(
    level: int = logging.INFO,
    log_file: Optional[str] = None,
    format_string: Optional[str] = None
) -> None:
    """配置日志系统
    
    Args:
        level: 日志级别，默认 INFO
        log_file: 日志文件路径（可选），如果指定则同时输出到文件
        format_string: 自定义日志格式（可选）
    """
    if format_string is None:
        format_string = (
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    
    # 获取根 logger
    root_logger = logging.getLogger("yuehua_ziniao_webdriver")
    root_logger.setLevel(level)
    
    # 清除现有的 handlers
    root_logger.handlers.clear()
    
    # 控制台 handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_handler.setFormatter(logging.Formatter(format_string))
    root_logger.addHandler(console_handler)
    
    # 文件 handler（如果指定）
    if log_file:
        try:
            # 确保日志目录存在
            log_path = Path(log_file)
            log_path.parent.mkdir(parents=True, exist_ok=True)
            
            file_handler = logging.FileHandler(
                log_file,
                encoding='utf-8'
            )
            file_handler.setLevel(level)
            file_handler.setFormatter(logging.Formatter(format_string))
            root_logger.addHandler(file_handler)
            
            logger.info(f"日志文件：{log_file}")
        except Exception as e:
            logger.error(f"创建日志文件失败：{e}")
