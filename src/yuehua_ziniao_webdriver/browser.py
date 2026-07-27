"""浏览器会话管理模块

提供浏览器会话的管理和操作功能。
"""

import time
import logging
import socket
import threading
from typing import Optional, Callable, Any, List, Dict
from urllib.parse import quote, urlparse

import requests
from DrissionPage import Chromium
from DrissionPage._base.driver import BrowserDriver
from DrissionPage._pages.chromium_tab import ChromiumTab
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
        self._active_tab = None
        self._preferred_target_id: Optional[str] = None
        self._cdp_proxy: Optional[CdpTcpProxy] = None
        self._closed = False
        
        logger.debug(
            f"初始化浏览器会话：store={store_name}, "
            f"host={host}, port={port}, store_id={store_id}"
        )
        
        try:
            if proxy_host:
                self._cdp_proxy = CdpTcpProxy(proxy_host, port, host, port)
                self._cdp_proxy.start()
            # startBrowser 返回时插件和页面 WebSocket 仍可能重建。此处只
            # 保存 CDP 地址，等 HTTP(S) 页面 target 稳定后再首次创建
            # DrissionPage Chromium，避免留下半初始化全局单例。
            logger.debug("浏览器会话已创建，等待业务页面后惰性连接：%s", store_name)
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

    @property
    def page(self):
        """获取已验证的当前业务标签页。

        调用方应复用此对象，不要再使用调试端口构造 ChromiumPage。
        """
        return self.get_tab()

    @staticmethod
    def _stop_driver(driver: Any) -> None:
        if driver is None:
            return
        try:
            driver.stop()
        except Exception as exc:
            logger.debug("停止旧 DrissionPage driver 时忽略异常：%s", exc)

    @classmethod
    def _clear_drissionpage_caches(
        cls,
        browser_id: Optional[str],
        target_ids: List[str],
    ) -> None:
        """Stop stale drivers and clear all three DrissionPage registries."""
        if not browser_id:
            return

        browser_registry = getattr(Chromium, "_BROWSERS", {})
        browser = browser_registry.get(browser_id)
        if browser is not None:
            # Prevent Driver.stop() callbacks from treating a reconnect as a
            # request to close or dispose the real Ziniao browser process.
            try:
                browser._disconnect_flag = True
            except Exception:
                pass
            drivers = [getattr(browser, "_driver", None)]
            drivers.extend(getattr(browser, "_drivers", {}).values())
            for values in getattr(browser, "_all_drivers", {}).values():
                drivers.extend(values)
            seen = set()
            for driver in drivers:
                if driver is not None and id(driver) not in seen:
                    seen.add(id(driver))
                    cls._stop_driver(driver)

        tab_registry = getattr(ChromiumTab, "_TABS", {})
        for target_id, tab in list(tab_registry.items()):
            tab_browser = getattr(tab, "browser", getattr(tab, "_browser", None))
            tab_browser_id = getattr(tab_browser, "id", None)
            if target_id not in target_ids and tab_browser_id != browser_id:
                continue
            cls._stop_driver(getattr(tab, "_driver", None))
            tab_registry.pop(target_id, None)

        cls._stop_driver(getattr(BrowserDriver, "BROWSERS", {}).get(browser_id))
        getattr(BrowserDriver, "BROWSERS", {}).pop(browser_id, None)

        lock = getattr(Chromium, "_lock", None)
        if lock is None:
            browser_registry.pop(browser_id, None)
        else:
            with lock:
                browser_registry.pop(browser_id, None)

    def _get_cdp_browser_id(self) -> Optional[str]:
        """Read the exact browser target ID without opening a WebSocket."""
        response = self._cdp_request("GET", "/json/version", timeout=5)
        response.raise_for_status()
        try:
            websocket_url = str(response.json().get("webSocketDebuggerUrl") or "")
            return websocket_url.rstrip("/").rsplit("/", 1)[-1] or None
        finally:
            response.close()

    def _web_targets(self) -> List[Dict[str, Any]]:
        """Read HTTP(S) page metadata without constructing any tab objects."""
        targets: List[Dict[str, Any]] = []
        for target in self._list_cdp_tabs():
            url = str(target.get("url") or "")
            if target.get("type") not in ("page", "webview"):
                continue
            if not target.get("id") or not target.get("webSocketDebuggerUrl"):
                continue
            if url.startswith(("http://", "https://")):
                targets.append(target)
        return targets

    def _select_web_target(
        self,
        index: int = -1,
        target_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        targets = self._web_targets()
        if target_id:
            for target in targets:
                if target.get("id") == target_id:
                    return target
            raise RuntimeError(f"业务标签页已关闭或不可访问：{target_id}")
        if not targets:
            raise RuntimeError("CDP 已连接，但尚未发现可访问的网页标签")
        if index == -1:
            return targets[0]
        if 0 <= index < len(targets):
            return targets[index]
        raise IndexError(f"标签页索引超出范围：{index}")

    def wait_for_web_page_target(
        self,
        url_prefix: Optional[str] = None,
        timeout: float = 30,
        poll_interval: float = 0.5,
        stable_polls: int = 2,
    ) -> bool:
        """Wait for a stable HTTP(S) page target using only the CDP HTTP API."""
        deadline = time.monotonic() + max(0.0, timeout)
        consecutive = 0
        while True:
            try:
                targets = self._web_targets()
                found = any(
                    not url_prefix
                    or str(target.get("url") or "").startswith(url_prefix)
                    for target in targets
                )
                consecutive = consecutive + 1 if found else 0
                if consecutive >= max(1, stable_polls):
                    return True
            except (requests.RequestException, ValueError, TypeError) as exc:
                consecutive = 0
                logger.debug("等待 CDP 网页 target：store=%s, error=%s", self.store_name, exc)
            if time.monotonic() >= deadline:
                return False
            remaining = max(0.0, deadline - time.monotonic())
            time.sleep(min(poll_interval, remaining))

    @staticmethod
    def _attach_target(browser: Chromium, target_id: str):
        """Construct exactly one ChromiumTab selected from CDP /json metadata."""
        return ChromiumTab(browser, target_id)

    def reconnect(
        self,
        timeout: float = 10,
        retry_interval: float = 0.5,
        require_web_page: bool = True,
        target_id: Optional[str] = None,
    ) -> Chromium:
        """丢弃旧对象并重新连接浏览器，可等待普通网页通道稳定。

        紫鸟返回调试端口时，CDP HTTP 接口可能已经可用，但页面
        WebSocket 通道仍会短暂断开。本方法仅在 CDP HTTP 已出现网页
        target 后创建 Chromium，并通过读取普通网页标签确认页面通道实际可用。插件的
        offscreen/background 标签可能始终无法连接，不作为健康检查依据。

        Args:
            timeout: 最长重连等待时间（秒），默认 10
            retry_interval: 重试间隔（秒），默认 0.5
            require_web_page: 是否要求存在可访问的 HTTP(S) 网页标签。
                初始化阶段应为 False，启动页打开后应为 True。

        Returns:
            Chromium: 新连接的浏览器对象

        Raises:
            ZiniaoError: 会话已关闭或在超时时间内无法建立稳定连接
        """
        if self._closed:
            raise ZiniaoError("浏览器会话已关闭")
        if timeout < 0:
            raise ValueError("timeout 不能小于 0")
        if retry_interval < 0:
            raise ValueError("retry_interval 不能小于 0")

        deadline = time.monotonic() + timeout
        last_error: Optional[Exception] = None
        previous_browser = self._browser
        self._browser = None
        self._active_tab = None
        address = self._build_cdp_address(self.host, self.port)

        if require_web_page and not self.wait_for_web_page_target(
            timeout=timeout,
            poll_interval=retry_interval,
        ):
            self._browser = previous_browser
            raise ZiniaoError(
                "CDP 已连接，但网页 target 尚未稳定",
                {"host": self.host, "port": self.port, "store_name": self.store_name},
            )

        while True:
            browser = None
            browser_id = None
            target_ids: List[str] = []
            try:
                targets = self._list_cdp_tabs()
                try:
                    browser_id = self._get_cdp_browser_id()
                except (requests.RequestException, ValueError, TypeError):
                    browser_id = None
                target_ids = [
                    str(target.get("id"))
                    for target in targets
                    if target.get("id")
                ]
                self._clear_drissionpage_caches(browser_id, target_ids)
                browser = Chromium(address)
                if require_web_page:
                    preferred_id = target_id or self._preferred_target_id
                    try:
                        selected = self._select_web_target(target_id=preferred_id)
                    except RuntimeError:
                        if target_id:
                            raise
                        self._preferred_target_id = None
                        selected = self._select_web_target()
                    self._active_tab = self._attach_target(
                        browser, str(selected["id"])
                    )
                self._browser = browser
                logger.info(f"浏览器连接已刷新：{self.store_name}")
                return browser
            except Exception as e:
                last_error = e
                self._browser = None
                if browser is not None:
                    self._clear_drissionpage_caches(browser_id, target_ids)
                if time.monotonic() >= deadline:
                    break
                logger.debug(
                    "CDP 页面通道尚未稳定，等待后重试：%s, 错误：%s",
                    self.store_name,
                    e,
                )
                remaining = max(0.0, deadline - time.monotonic())
                time.sleep(min(retry_interval, remaining))

        # 保留开店阶段已建立的对象。调用方通过 get_tab()/page 首次访问时
        # 还会惰性重连，短暂页面断开不能反向判定店铺启动失败。
        self._browser = previous_browser
        error_msg = f"重新连接浏览器失败：{last_error}"
        logger.debug("%s, store=%s", error_msg, self.store_name)
        raise ZiniaoError(
            error_msg,
            {
                "host": self.host,
                "port": self.port,
                "store_name": self.store_name,
                "error": str(last_error),
            },
        )
    
    def get_tab(self, index: int = -1):
        """获取标签页
        
        Args:
            index: 标签页索引，-1 表示最新的标签页（默认）
            
        Returns:
            可访问的 HTTP(S) 业务标签页对象
        """
        def select_tab(browser):
            active_id = getattr(self._active_tab, "tab_id", None)
            if index == -1 and active_id:
                try:
                    selected = self._select_web_target(target_id=active_id)
                except RuntimeError:
                    selected = self._select_web_target(index=index)
            else:
                selected = self._select_web_target(index=index)
            target_id = str(selected["id"])
            if (
                self._active_tab is not None
                and getattr(self._active_tab, "tab_id", None) == target_id
            ):
                return self._active_tab
            self._active_tab = self._attach_target(browser, target_id)
            return self._active_tab

        try:
            return select_tab(self.browser)
        except IndexError:
            raise
        except Exception as exc:
            logger.warning(
                "当前页面连接不可用，执行惰性重连：store=%s, error=%s",
                self.store_name,
                exc,
            )
            browser = self.reconnect(
                timeout=10,
                retry_interval=0.5,
                require_web_page=True,
            )
            return self._active_tab or select_tab(browser)
    
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
            target_id = self._open_url_in_new_cdp_tab(url)
            if not target_id:
                logger.warning("创建 IP 检测 target 失败：%s", self.store_name)
                return False

            scheme = urlparse(url).scheme.lower()
            target_state = self._wait_for_target_state(
                target_id,
                timeout=min(float(timeout), 10.0),
                poll_interval=0.5,
            )
            if target_state == "closed":
                logger.info("IP 检测 target 已自动关闭，检测流程完成：%s", self.store_name)
                return True
            if scheme == "chrome-extension":
                if target_state == "stable":
                    logger.info("紫鸟内部 IP 检测 target 已创建：%s", self.store_name)
                    return True
                logger.warning("紫鸟内部 IP 检测 target 未就绪：%s", self.store_name)
                return False
            if scheme not in ("http", "https"):
                logger.warning("跳过不支持的 IP 检测 URL：%s", scheme)
                return True
            if target_state != "stable":
                logger.warning("IP 检测页面尚未稳定：%s", self.store_name)
                return False

            browser = self.reconnect(
                timeout=min(float(timeout), 10.0),
                retry_interval=0.5,
                require_web_page=True,
                target_id=target_id,
            )
            tab = self._active_tab or self._attach_target(browser, target_id)
            
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
            if "target_id" in locals() and not self._target_exists(target_id):
                logger.info("IP 检测 target 已自动关闭，检测流程完成：%s", self.store_name)
                return True
            logger.warning(f"IP 检测暂不可用：{self.store_name}, 错误：{e}")
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
            else:
                self._preferred_target_id = target_id

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

    def _cdp_request(
        self,
        method: str,
        path: str,
        timeout: float,
    ) -> requests.Response:
        """Send a local CDP HTTP request without inheriting proxy settings."""
        session = requests.Session()
        session.trust_env = False
        session.keep_alive = False
        try:
            return session.request(
                method,
                f"{self._cdp_base_url()}{path}",
                timeout=timeout,
                headers={"Connection": "close"},
            )
        finally:
            session.close()

    def _open_url_in_new_cdp_tab(self, url: str) -> Optional[str]:
        response = None
        try:
            encoded_url = quote(url, safe="")
            response = self._cdp_request(
                "PUT", f"/json/new?{encoded_url}", timeout=10
            )
            if response.status_code == 405:
                response.close()
                response = self._cdp_request(
                    "GET", f"/json/new?{encoded_url}", timeout=10
                )
            response.raise_for_status()
            tab_info = response.json()
            tab_id = tab_info.get("id")
            if tab_id:
                self._activate_cdp_tab(tab_id)
            return tab_id
        except (requests.RequestException, ValueError) as e:
            logger.debug(f"通过 CDP 新建启动页失败，将回退到 DrissionPage：{e}")
            return None
        finally:
            if response is not None:
                response.close()

    def _list_cdp_tabs(self) -> List[Dict[str, Any]]:
        response = self._cdp_request("GET", "/json", timeout=5)
        response.raise_for_status()
        try:
            return response.json()
        finally:
            response.close()

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

    def _target_exists(self, target_id: str) -> bool:
        try:
            return any(
                target.get("id") == target_id
                for target in self._list_cdp_tabs()
            )
        except (requests.RequestException, ValueError, TypeError):
            return False

    def _wait_for_target_state(
        self,
        target_id: str,
        timeout: float,
        poll_interval: float = 0.5,
        stable_polls: int = 2,
    ) -> str:
        """Return ``stable``, ``closed``, or ``timeout`` for an exact target."""
        deadline = time.monotonic() + max(0.0, timeout)
        seen = False
        consecutive = 0
        while True:
            try:
                exists = any(
                    target.get("id") == target_id
                    for target in self._list_cdp_tabs()
                )
                if exists:
                    seen = True
                    consecutive += 1
                    if consecutive >= max(1, stable_polls):
                        return "stable"
                elif seen:
                    return "closed"
                else:
                    # /json/new already returned this exact ID. If it is gone
                    # before the first poll, Ziniao completed and closed it.
                    return "closed"
            except (requests.RequestException, ValueError, TypeError):
                consecutive = 0
            if time.monotonic() >= deadline:
                return "timeout"
            remaining = max(0.0, deadline - time.monotonic())
            time.sleep(min(poll_interval, remaining))

    def _close_cdp_tab(self, tab_id: str) -> bool:
        response = self._cdp_request("GET", f"/json/close/{tab_id}", timeout=5)
        try:
            return response.ok
        finally:
            response.close()

    def _activate_cdp_tab(self, tab_id: str) -> None:
        response = self._cdp_request(
            "GET", f"/json/activate/{tab_id}", timeout=5
        )
        try:
            response.raise_for_status()
        finally:
            response.close()
    
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
