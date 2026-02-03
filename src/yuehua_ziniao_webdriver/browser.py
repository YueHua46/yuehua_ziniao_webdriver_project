"""浏览器会话管理模块

提供浏览器会话的管理和操作功能。
"""

import time
import logging
from typing import Optional, Callable, Any

from DrissionPage import Chromium
from DrissionPage.common import By

from .exceptions import IPCheckError, ZiniaoError

logger = logging.getLogger(__name__)


class BrowserSession:
    """浏览器会话类
    
    封装 DrissionPage 的 Chromium 对象，提供便捷的操作接口。
    """
    
    def __init__(
        self,
        port: int,
        store_id: str,
        store_name: str,
        ip_check_url: Optional[str] = None,
        launcher_page: Optional[str] = None,
        close_callback: Optional[Callable[[str], None]] = None
    ) -> None:
        """初始化浏览器会话
        
        Args:
            port: 浏览器调试端口
            store_id: 店铺 ID/OAuth
            store_name: 店铺名称
            ip_check_url: IP 检测页面 URL（可选）
            launcher_page: 启动页面 URL（可选）
            close_callback: 关闭回调函数（可选）
        """
        self.port = port
        self.store_id = store_id
        self.store_name = store_name
        self.ip_check_url = ip_check_url
        self.launcher_page = launcher_page
        self.close_callback = close_callback
        self._browser: Optional[Chromium] = None
        self._closed = False
        
        logger.debug(
            f"初始化浏览器会话：store={store_name}, "
            f"port={port}, store_id={store_id}"
        )
        
        # 创建浏览器实例
        try:
            self._browser = Chromium(port)
            logger.info(f"成功连接到浏览器：{store_name}")
        except Exception as e:
            error_msg = f"连接到浏览器失败：{e}"
            logger.error(error_msg)
            raise ZiniaoError(error_msg, {"port": port, "error": str(e)})
    
    @property
    def browser(self) -> Chromium:
        """获取底层的 Chromium 浏览器对象
        
        Returns:
            Chromium: DrissionPage 浏览器对象
            
        Raises:
            ZiniaoError: 如果会话已关闭
        """
        if self._closed:
            raise ZiniaoError("浏览器会话已关闭")
        
        if self._browser is None:
            raise ZiniaoError("浏览器对象未初始化")
        
        return self._browser
    
    def get_tab(self, index: int = -1):
        """获取标签页
        
        Args:
            index: 标签页索引，-1 表示最新的标签页（默认）
            
        Returns:
            标签页对象
        """
        if index == -1:
            return self.browser.latest_tab
        else:
            tabs = self.browser.tabs
            if 0 <= index < len(tabs):
                return tabs[index]
            else:
                raise IndexError(f"标签页索引超出范围：{index}")
    
    def check_ip(
        self,
        ip_check_url: Optional[str] = None,
        timeout: int = 60
    ) -> bool:
        """检测 IP 是否可用
        
        Args:
            ip_check_url: IP 检测页面 URL，如果为 None 则使用初始化时的 URL
            timeout: 超时时间（秒），默认 60
            
        Returns:
            bool: IP 可用返回 True，否则返回 False
        """
        # 确定使用的 URL
        url = ip_check_url or self.ip_check_url
        
        if not url:
            logger.warning("IP 检测页面 URL 为空，跳过检测")
            return True
        
        try:
            logger.info(f"开始 IP 检测：{self.store_name}")
            
            tab = self.get_tab()
            tab.get(url)
            
            # 等待成功按钮出现
            success_button = tab.ele(
                (By.XPATH, '//button[contains(@class, "styles_btn--success")]'),
                timeout=timeout
            )
            
            if success_button:
                logger.info(f"IP 检测成功：{self.store_name}")
                return True
            else:
                logger.warning(f"IP 检测超时：{self.store_name}")
                return False
                
        except Exception as e:
            logger.error(f"IP 检测异常：{self.store_name}, 错误：{e}")
            return False
    
    def open_launcher_page(
        self,
        launcher_page: Optional[str] = None,
        wait_time: int = 6
    ) -> None:
        """打开启动页面（店铺平台主页）
        
        Args:
            launcher_page: 启动页面 URL，如果为 None 则使用初始化时的 URL
            wait_time: 打开后等待时间（秒），默认 6
            
        Raises:
            ZiniaoError: 如果启动页面 URL 为空
        """
        # 确定使用的 URL
        url = launcher_page or self.launcher_page
        
        if not url:
            raise ZiniaoError(
                "启动页面 URL 为空",
                {"store_name": self.store_name}
            )
        
        try:
            logger.info(f"打开启动页面：{self.store_name} -> {url}")
            
            tab = self.get_tab()
            tab.get(url)
            
            time.sleep(wait_time)
            
            logger.debug(f"启动页面已打开：{self.store_name}")
            
        except Exception as e:
            error_msg = f"打开启动页面失败：{e}"
            logger.error(error_msg)
            raise ZiniaoError(
                error_msg,
                {"store_name": self.store_name, "url": url, "error": str(e)}
            )
    
    def navigate(self, url: str, wait_time: float = 0) -> None:
        """导航到指定 URL
        
        Args:
            url: 目标 URL
            wait_time: 导航后等待时间（秒），默认 0
        """
        logger.debug(f"导航到：{url}")
        tab = self.get_tab()
        tab.get(url)
        
        if wait_time > 0:
            time.sleep(wait_time)
    
    def close(self) -> None:
        """关闭浏览器会话
        
        会调用初始化时传入的 close_callback 来关闭店铺。
        """
        if self._closed:
            logger.debug(f"浏览器会话已关闭：{self.store_name}")
            return
        
        logger.info(f"关闭浏览器会话：{self.store_name}")
        
        # 调用关闭回调
        if self.close_callback:
            try:
                self.close_callback(self.store_id)
                logger.debug(f"调用关闭回调成功：{self.store_name}")
            except Exception as e:
                logger.error(f"调用关闭回调失败：{self.store_name}, 错误：{e}")
        
        self._closed = True
        self._browser = None
    
    def is_closed(self) -> bool:
        """检查会话是否已关闭
        
        Returns:
            bool: 已关闭返回 True
        """
        return self._closed
    
    def __enter__(self) -> "BrowserSession":
        """上下文管理器入口"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """上下文管理器退出，自动关闭会话"""
        self.close()
    
    def __repr__(self) -> str:
        return (
            f"BrowserSession(store='{self.store_name}', "
            f"port={self.port}, closed={self._closed})"
        )


def get_browser(port: int) -> Chromium:
    """获取 DrissionPage 浏览器对象（原始方式）
    
    这是一个便捷函数，用于向后兼容。
    
    Args:
        port: 浏览器调试端口
        
    Returns:
        Chromium: DrissionPage 浏览器对象
    """
    logger.debug(f"获取浏览器对象：port={port}")
    return Chromium(port)
