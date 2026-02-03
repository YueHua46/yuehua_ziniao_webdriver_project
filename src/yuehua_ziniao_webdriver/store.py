"""店铺管理模块

提供店铺的打开、关闭、列表获取和搜索功能。
"""

import json
import logging
import uuid
from typing import List, Optional, Dict, Any
from concurrent.futures import ThreadPoolExecutor, as_completed

from .types import Store, StoreOpenOptions, BrowserStartResult
from .http_client import HttpClient
from .browser import BrowserSession
from .utils import fuzzy_match, exact_match
from .exceptions import (
    StoreNotFoundError,
    MultipleStoresFoundError,
    StoreOperationError,
    UnsupportedVersionError
)

logger = logging.getLogger(__name__)


class StoreManager:
    """店铺管理器
    
    负责店铺的各种操作。
    """
    
    def __init__(
        self,
        http_client: HttpClient,
        user_info: Dict[str, str]
    ) -> None:
        """初始化店铺管理器
        
        Args:
            http_client: HTTP 客户端
            user_info: 用户信息字典（company, username, password）
        """
        self.http_client = http_client
        self.user_info = user_info
        self._store_list_cache: Optional[List[Store]] = None
        
        logger.debug("初始化店铺管理器")
    
    def get_store_list(self, use_cache: bool = False) -> List[Store]:
        """获取店铺列表
        
        Args:
            use_cache: 是否使用缓存，默认 False
            
        Returns:
            List[Store]: 店铺列表
            
        Raises:
            StoreOperationError: 获取失败
        """
        # 如果使用缓存且缓存存在
        if use_cache and self._store_list_cache is not None:
            logger.debug("使用缓存的店铺列表")
            return self._store_list_cache
        
        request_id = str(uuid.uuid4())
        data = {
            "action": "getBrowserList",
            "requestId": request_id
        }
        data.update(self.user_info)
        
        logger.info("获取店铺列表...")
        
        result = self.http_client.send_request(data)
        
        if result is None:
            raise StoreOperationError(
                "获取",
                "all",
                message="HTTP 请求返回 None"
            )
        
        status_code = result.get("statusCode")
        
        if status_code == 0:
            browser_list = result.get("browserList", [])
            logger.info(f"成功获取店铺列表，共 {len(browser_list)} 个店铺")
            
            # 更新缓存
            self._store_list_cache = browser_list
            
            return browser_list
        else:
            error_msg = result.get("message", "未知错误")
            logger.error(f"获取店铺列表失败：statusCode={status_code}, message={error_msg}")
            raise StoreOperationError(
                "获取列表",
                "all",
                status_code=status_code,
                message=error_msg
            )
    
    def find_stores_by_name(
        self,
        name: str,
        exact_match_mode: bool = False,
        use_cache: bool = True
    ) -> List[Store]:
        """通过名称搜索店铺
        
        Args:
            name: 店铺名称
            exact_match_mode: 是否精确匹配，False 则模糊匹配
            use_cache: 是否使用缓存的店铺列表，默认 True
            
        Returns:
            List[Store]: 匹配的店铺列表
        """
        logger.debug(
            f"搜索店铺：name='{name}', exact_match={exact_match_mode}"
        )
        
        # 获取店铺列表
        store_list = self.get_store_list(use_cache=use_cache)
        
        # 搜索匹配的店铺
        matched_stores: List[Store] = []
        
        for store in store_list:
            store_name = store.get("browserName", "")
            
            if exact_match_mode:
                if exact_match(store_name, name):
                    matched_stores.append(store)
            else:
                if fuzzy_match(store_name, name):
                    matched_stores.append(store)
        
        logger.debug(f"找到 {len(matched_stores)} 个匹配的店铺")
        
        return matched_stores
    
    def open_store(
        self,
        store_identifier: str,
        **options
    ) -> BrowserSession:
        """打开店铺
        
        Args:
            store_identifier: 店铺标识（browserOauth 或 browserId）
            **options: 打开店铺的选项（参见 StoreOpenOptions）
            
        Returns:
            BrowserSession: 浏览器会话对象
            
        Raises:
            StoreOperationError: 打开失败
        """
        request_id = str(uuid.uuid4())
        
        # 构建请求数据
        data: Dict[str, Any] = {
            "action": "startBrowser",
            "isWaitPluginUpdate": options.get("isWaitPluginUpdate", 0),
            "isHeadless": options.get("isHeadless", 0),
            "requestId": request_id,
            "isWebDriverReadOnlyMode": options.get("isWebDriverReadOnlyMode", 0),
            "cookieTypeLoad": options.get("cookieTypeLoad", 0),
            "cookieTypeSave": options.get("cookieTypeSave", 0),
            "runMode": options.get("runMode", "1"),
            "isLoadUserPlugin": options.get("isLoadUserPlugin", False),
            "pluginIdType": options.get("pluginIdType", 1),
            "privacyMode": options.get("privacyMode", 0),
        }
        data.update(self.user_info)
        
        # 确定使用 browserId 还是 browserOauth
        if store_identifier.isdigit():
            data["browserId"] = store_identifier
        else:
            data["browserOauth"] = store_identifier
        
        # 注入 JS 信息（如果提供）
        js_info = options.get("jsInfo", "")
        if len(str(js_info)) > 2:
            data["injectJsInfo"] = json.dumps(js_info)
        
        logger.info(f"打开店铺：{store_identifier}")
        
        # 发送请求
        result = self.http_client.send_request(data)
        
        if result is None:
            raise StoreOperationError(
                "打开",
                store_identifier,
                message="HTTP 请求返回 None"
            )
        
        status_code = result.get("statusCode")
        
        if status_code == 0:
            # 打开成功
            debugging_port = result.get("debuggingPort")
            browser_oauth = result.get("browserOauth", store_identifier)
            ip_check_url = result.get("ipDetectionPage")
            launcher_page = result.get("launcherPage")
            
            # 获取店铺名称（尝试从缓存的店铺列表中查找）
            store_name = self._get_store_name(browser_oauth)
            
            logger.info(
                f"店铺打开成功：{store_name} (OAuth: {browser_oauth}, "
                f"Port: {debugging_port})"
            )
            
            # 创建浏览器会话
            session = BrowserSession(
                port=debugging_port,
                store_id=browser_oauth,
                store_name=store_name,
                ip_check_url=ip_check_url,
                launcher_page=launcher_page,
                close_callback=lambda sid: self.close_store(sid)
            )
            
            # 打开店铺后先做 IP 检测再打开店铺平台主页
            if ip_check_url:
                ip_ok = session.check_ip()
                if not ip_ok:
                    logger.warning("IP 检测未通过，仍将打开启动页")
            else:
                logger.warning("ipDetectionPage 为空，请升级紫鸟浏览器到最新版，跳过 IP 检测")
            if launcher_page:
                session.open_launcher_page()
            else:
                logger.warning("launcherPage 为空，无法打开店铺平台主页")

            return session
            
        else:
            error_msg = result.get("message", "未知错误")
            logger.error(
                f"打开店铺失败：{store_identifier}, "
                f"statusCode={status_code}, message={error_msg}"
            )
            raise StoreOperationError(
                "打开",
                store_identifier,
                status_code=status_code,
                message=error_msg
            )
    
    def open_store_by_name(
        self,
        store_name: str,
        exact_match_mode: bool = False,
        **options
    ) -> BrowserSession:
        """通过店铺名称打开店铺
        
        Args:
            store_name: 店铺名称
            exact_match_mode: 是否精确匹配，默认 False（模糊匹配）
            **options: 打开店铺的选项
            
        Returns:
            BrowserSession: 浏览器会话对象
            
        Raises:
            StoreNotFoundError: 未找到匹配的店铺
            MultipleStoresFoundError: 找到多个匹配的店铺
            StoreOperationError: 打开失败
        """
        logger.info(f"通过名称打开店铺：'{store_name}'")
        
        # 搜索店铺
        matched_stores = self.find_stores_by_name(
            store_name,
            exact_match_mode=exact_match_mode
        )
        
        # 检查结果
        if len(matched_stores) == 0:
            raise StoreNotFoundError(store_name, "名称")
        
        if len(matched_stores) > 1:
            store_names = [s.get("browserName", "") for s in matched_stores]
            raise MultipleStoresFoundError(
                store_name,
                len(matched_stores),
                store_names
            )
        
        # 打开店铺
        store = matched_stores[0]
        store_oauth = store.get("browserOauth")
        
        if not store_oauth:
            raise StoreOperationError(
                "打开",
                store_name,
                message="店铺 OAuth 标识为空"
            )
        
        return self.open_store(store_oauth, **options)
    
    def open_stores_by_names(
        self,
        store_names: List[str],
        max_workers: int = 3,
        exact_match_mode: bool = False,
        **options
    ) -> Dict[str, BrowserSession]:
        """并发打开多个店铺（通过店铺名称）
        
        Args:
            store_names: 店铺名称列表
            max_workers: 最大并发数，默认 3
            exact_match_mode: 是否精确匹配，默认 False
            **options: 打开店铺的选项
            
        Returns:
            Dict[str, BrowserSession]: 店铺名称到浏览器会话的映射
            
        Note:
            如果某个店铺打开失败，会记录错误但不会中断其他店铺的打开。
            返回的字典中只包含成功打开的店铺。
        """
        logger.info(f"并发打开 {len(store_names)} 个店铺，最大并发数：{max_workers}")
        
        sessions: Dict[str, BrowserSession] = {}
        
        def open_single_store(name: str) -> tuple[str, Optional[BrowserSession]]:
            """打开单个店铺的辅助函数"""
            try:
                session = self.open_store_by_name(
                    name,
                    exact_match_mode=exact_match_mode,
                    **options
                )
                return (name, session)
            except Exception as e:
                logger.error(f"打开店铺失败：{name}, 错误：{e}")
                return (name, None)
        
        # 使用线程池并发打开
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 提交所有任务
            futures = {
                executor.submit(open_single_store, name): name
                for name in store_names
            }
            
            # 收集结果
            for future in as_completed(futures):
                name, session = future.result()
                if session is not None:
                    sessions[name] = session
                    logger.info(f"店铺打开成功：{name}")
                else:
                    logger.warning(f"店铺打开失败：{name}")
        
        logger.info(
            f"并发打开完成：成功 {len(sessions)}/{len(store_names)} 个店铺"
        )
        
        return sessions
    
    def close_store(self, store_id: str) -> None:
        """关闭店铺
        
        Args:
            store_id: 店铺 ID/OAuth
            
        Raises:
            StoreOperationError: 关闭失败
        """
        request_id = str(uuid.uuid4())
        data = {
            "action": "stopBrowser",
            "requestId": request_id,
            "duplicate": 0,
            "browserOauth": store_id
        }
        data.update(self.user_info)
        
        logger.info(f"关闭店铺：{store_id}")
        
        result = self.http_client.send_request(data)
        
        if result is None:
            raise StoreOperationError(
                "关闭",
                store_id,
                message="HTTP 请求返回 None"
            )
        
        status_code = result.get("statusCode")
        
        if status_code == 0:
            logger.info(f"店铺关闭成功：{store_id}")
        else:
            error_msg = result.get("message", "未知错误")
            logger.error(
                f"关闭店铺失败：{store_id}, "
                f"statusCode={status_code}, message={error_msg}"
            )
            raise StoreOperationError(
                "关闭",
                store_id,
                status_code=status_code,
                message=error_msg
            )
    
    def _get_store_name(self, store_oauth: str) -> str:
        """从缓存中获取店铺名称
        
        Args:
            store_oauth: 店铺 OAuth 标识
            
        Returns:
            str: 店铺名称，未找到返回 OAuth
        """
        if self._store_list_cache:
            for store in self._store_list_cache:
                if store.get("browserOauth") == store_oauth:
                    return store.get("browserName", store_oauth)
        
        return store_oauth
    
    def clear_cache(self) -> None:
        """清除店铺列表缓存"""
        logger.debug("清除店铺列表缓存")
        self._store_list_cache = None
    
    def __repr__(self) -> str:
        cache_size = len(self._store_list_cache) if self._store_list_cache else 0
        return f"StoreManager(cached_stores={cache_size})"
