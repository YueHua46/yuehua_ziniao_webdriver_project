"""浏览器会话管理模块

提供浏览器会话的管理和操作功能。
"""

import time
import logging
import socket
import threading
from typing import Optional, Callable, Any, List, Dict
from urllib.parse import quote

import requests
from DrissionPage import Chromium
from DrissionPage.common import By

from .exceptions import IPCheckError, ZiniaoError

logger = logging.getLogger(__name__)


class CdpTcpProxy:
    """将对外 CDP 端口转发到本机浏览器调试端口。"""

    def __init__(
        self,
        listen_host: str,
        listen_port: int,
        target_host: str,
        target_port: int,
    ) -> None:
        self.listen_host = listen_host
        self.listen_port = listen_port
        self.target_host = target_host
        self.target_port = target_port
        self._server: Optional[socket.socket] = None
        self._closed = threading.Event()
        self._threads: List[threading.Thread] = []

    def start(self) -> None:
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind((self.listen_host, self.listen_port))
        server.listen(128)
        self._server = server

        thread = threading.Thread(target=self._accept_loop, daemon=True)
        thread.start()
        self._threads.append(thread)

        logger.info(
            "CDP 代理已启动：%s:%s -> %s:%s",
            self.listen_host,
            self.listen_port,
            self.target_host,
            self.target_port,
        )

    def stop(self) -> None:
        self._closed.set()
        if self._server is not None:
            try:
                self._server.close()
            except OSError:
                pass
            self._server = None

    def _accept_loop(self) -> None:
        assert self._server is not None

        while not self._closed.is_set():
            try:
                client_socket, _ = self._server.accept()
            except OSError:
                break

            thread = threading.Thread(
                target=self._handle_client,
                args=(client_socket,),
                daemon=True,
            )
            thread.start()
            self._threads.append(thread)

    def _handle_client(self, client_socket: socket.socket) -> None:
        try:
            target_socket = socket.create_connection(
                (self.target_host, self.target_port),
                timeout=10,
            )
        except OSError:
            client_socket.close()
            return

        threads = [
            threading.Thread(
                target=self._pipe,
                args=(client_socket, target_socket),
                daemon=True,
            ),
            threading.Thread(
                target=self._pipe,
                args=(target_socket, client_socket),
                daemon=True,
            ),
        ]

        for thread in threads:
            thread.start()
            self._threads.append(thread)

    @staticmethod
    def _pipe(source: socket.socket, target: socket.socket) -> None:
        try:
            while True:
                data = source.recv(65536)
                if not data:
                    break
                target.sendall(data)
        except OSError:
            pass
        finally:
            for sock in (source, target):
                try:
                    sock.shutdown(socket.SHUT_RDWR)
                except OSError:
                    pass
                try:
                    sock.close()
                except OSError:
                    pass


class BrowserSession:
    """浏览器会话类
    
    封装 DrissionPage 的 Chromium 对象，提供便捷的操作接口。
    """
    
    def __init__(
        self,
        port: int,
        store_id: str,
        store_name: str,
        host: str = "127.0.0.1",
        proxy_host: Optional[str] = None,
        ip_check_url: Optional[str] = None,
        launcher_page: Optional[str] = None,
        close_callback: Optional[Callable[[str], None]] = None
    ) -> None:
        """初始化浏览器会话
        
        Args:
            port: 浏览器调试端口
            store_id: 店铺 ID/OAuth
            store_name: 店铺名称
            host: 浏览器 CDP 调试端口主机
            proxy_host: 对外暴露 CDP 调试端口的本机监听地址
            ip_check_url: IP 检测页面 URL（可选）
            launcher_page: 启动页面 URL（可选）
            close_callback: 关闭回调函数（可选）
        """
        self.port = port
        self.host = host
        self.proxy_host = proxy_host
        self.store_id = store_id
        self.store_name = store_name
        self.ip_check_url = ip_check_url
        self.launcher_page = launcher_page
        self.close_callback = close_callback
        self._browser: Optional[Chromium] = None
        self._cdp_proxy: Optional[CdpTcpProxy] = None
        self._closed = False
        
        logger.debug(
            f"初始化浏览器会话：store={store_name}, "
            f"host={host}, port={port}, store_id={store_id}"
        )
        
        # 创建浏览器实例
        try:
            if proxy_host:
                self._cdp_proxy = CdpTcpProxy(proxy_host, port, host, port)
                self._cdp_proxy.start()
            self._browser = Chromium(self._build_cdp_address(host, port))
            logger.info(f"成功连接到浏览器：{store_name}")
        except Exception as e:
            if self._cdp_proxy is not None:
                self._cdp_proxy.stop()
                self._cdp_proxy = None
            error_msg = f"连接到浏览器失败：{e}"
            logger.error(error_msg)
            raise ZiniaoError(
                error_msg,
                {"host": host, "port": port, "error": str(e)}
            )

    @staticmethod
    def _build_cdp_address(host: str, port: int) -> Any:
        """构建 DrissionPage 可识别的 CDP 地址。

        本机连接沿用整数端口，避免影响既有行为；远程连接使用 host:port。
        """
        if host in ("127.0.0.1", "localhost", "::1"):
            return port
        if ":" in host and not host.startswith("["):
            return f"[{host}]:{port}"
        return f"{host}:{port}"
    
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
        wait_time: int = 6,
        close_extra_tabs: bool = True,
        cleanup_timeout: float = 45,
        quiet_seconds: float = 8,
        poll_interval: float = 0.5,
    ) -> None:
        """打开启动页面（店铺平台主页）
        
        Args:
            launcher_page: 启动页面 URL，如果为 None 则使用初始化时的 URL
            wait_time: 打开后等待时间（秒），默认 6
            close_extra_tabs: 是否关闭启动页之外的多余标签页，默认 True
            cleanup_timeout: 最长清理等待时间（秒），默认 45
            quiet_seconds: 连续无多余标签页的稳定时间（秒），默认 8
            poll_interval: 标签页轮询间隔（秒），默认 0.5
            
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

            target_id = self._open_url_in_new_cdp_tab(url)
            if not target_id:
                tab = self.get_tab()
                tab.get(url)

            time.sleep(wait_time)

            if close_extra_tabs:
                self.close_extra_tabs(
                    keep_tab_id=target_id,
                    keep_url=url,
                    cleanup_timeout=cleanup_timeout,
                    quiet_seconds=quiet_seconds,
                    poll_interval=poll_interval,
                )

            logger.debug(f"启动页面已打开：{self.store_name}")
            
        except Exception as e:
            error_msg = f"打开启动页面失败：{e}"
            logger.error(error_msg)
            raise ZiniaoError(
                error_msg,
                {"store_name": self.store_name, "url": url, "error": str(e)}
            )

    def close_extra_tabs(
        self,
        keep_tab_id: Optional[str] = None,
        keep_url: Optional[str] = None,
        cleanup_timeout: float = 45,
        quiet_seconds: float = 8,
        poll_interval: float = 0.5,
    ) -> None:
        """关闭目标标签页之外的页面，持续等待到插件弹窗稳定消失。"""
        if not keep_tab_id:
            keep_tab_id = self._find_cdp_tab_id_by_url(keep_url) or self._active_cdp_tab_id()
        if not keep_tab_id:
            logger.warning("未找到需要保留的标签页，跳过多余 Tab 清理")
            return

        deadline = time.time() + cleanup_timeout
        quiet_since: Optional[float] = None

        while time.time() < deadline:
            closed_count = 0
            try:
                tabs = self._list_cdp_tabs()
                for tab in tabs:
                    tab_id = tab.get("id")
                    if tab.get("type") != "page" or not tab_id or tab_id == keep_tab_id:
                        continue
                    if self._close_cdp_tab(tab_id):
                        closed_count += 1

                self._activate_cdp_tab(keep_tab_id)
            except (requests.RequestException, ValueError) as e:
                logger.debug(f"清理多余 Tab 时 CDP 请求失败：{e}")
                quiet_since = None
                time.sleep(poll_interval)
                continue

            if closed_count:
                logger.info(f"已关闭 {closed_count} 个多余 Tab，继续等待插件延迟弹窗")
                quiet_since = None
            else:
                quiet_since = quiet_since or time.time()
                if time.time() - quiet_since >= quiet_seconds:
                    logger.debug("多余 Tab 清理完成，已进入稳定期")
                    break

            time.sleep(poll_interval)

    def _cdp_base_url(self) -> str:
        host = self.proxy_host or self.host
        if ":" in host and not host.startswith("["):
            host = f"[{host}]"
        return f"http://{host}:{self.port}"

    def _open_url_in_new_cdp_tab(self, url: str) -> Optional[str]:
        try:
            encoded_url = quote(url, safe="")
            response = requests.put(f"{self._cdp_base_url()}/json/new?{encoded_url}", timeout=10)
            if response.status_code == 405:
                response = requests.get(f"{self._cdp_base_url()}/json/new?{encoded_url}", timeout=10)
            response.raise_for_status()
            tab_info = response.json()
            tab_id = tab_info.get("id")
            if tab_id:
                self._activate_cdp_tab(tab_id)
            return tab_id
        except (requests.RequestException, ValueError) as e:
            logger.debug(f"通过 CDP 新建启动页失败，将回退到 DrissionPage：{e}")
            return None

    def _list_cdp_tabs(self) -> List[Dict[str, Any]]:
        response = requests.get(f"{self._cdp_base_url()}/json", timeout=5)
        response.raise_for_status()
        return response.json()

    def _active_cdp_tab_id(self) -> Optional[str]:
        tabs = self._list_cdp_tabs()
        for tab in tabs:
            if tab.get("type") == "page" and tab.get("webSocketDebuggerUrl"):
                return tab.get("id")
        return None

    def _find_cdp_tab_id_by_url(self, url: Optional[str]) -> Optional[str]:
        if not url:
            return None
        tabs = self._list_cdp_tabs()
        for tab in tabs:
            tab_url = str(tab.get("url") or "")
            if tab.get("type") == "page" and tab_url.startswith(url):
                return tab.get("id")
        return None

    def _close_cdp_tab(self, tab_id: str) -> bool:
        response = requests.get(f"{self._cdp_base_url()}/json/close/{tab_id}", timeout=5)
        return response.ok

    def _activate_cdp_tab(self, tab_id: str) -> None:
        response = requests.get(f"{self._cdp_base_url()}/json/activate/{tab_id}", timeout=5)
        response.raise_for_status()
    
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

        if self._cdp_proxy is not None:
            self._cdp_proxy.stop()
            self._cdp_proxy = None
        
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
            f"host='{self.host}', proxy_host='{self.proxy_host}', "
            f"port={self.port}, closed={self._closed})"
        )


def get_browser(port: int, host: str = "127.0.0.1") -> Chromium:
    """获取 DrissionPage 浏览器对象（原始方式）
    
    这是一个便捷函数，用于向后兼容。
    
    Args:
        port: 浏览器调试端口
        host: 浏览器 CDP 调试端口主机
        
    Returns:
        Chromium: DrissionPage 浏览器对象
    """
    logger.debug(f"获取浏览器对象：host={host}, port={port}")
    return Chromium(BrowserSession._build_cdp_address(host, port))
