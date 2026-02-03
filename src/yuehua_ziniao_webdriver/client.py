"""主客户端模块

提供 ZiniaoClient 主类，是 SDK 的核心接口。
"""

import json
import logging
import time
import uuid
from typing import List, Dict, Optional, Union

from .config import ZiniaoConfig
from .types import Store, ConfigSource
from .http_client import HttpClient
from .process import ProcessManager
from .store import StoreManager
from .browser import BrowserSession
from .exceptions import (
    ClientNotStartedError,
    UnsupportedVersionError,
    CoreUpdateError,
    ConfigurationError
)

logger = logging.getLogger(__name__)


class ZiniaoClient:
    """紫鸟浏览器客户端
    
    这是 SDK 的主要入口类，提供所有核心功能。
    
    使用示例:
        ```python
        from yuehua_ziniao_webdriver import ZiniaoClient, ZiniaoConfig
        
        config = ZiniaoConfig(
            client_path=r"D:\ziniao\ziniao.exe",
            company="企业名",
            username="用户名",
            password="密码"
        )
        
        client = ZiniaoClient(config)
        client.start()
        
        # 通过名称打开店铺
        session = client.open_store_by_name("我的店铺")
        
        client.stop()
        ```
    """
    
    def __init__(self, config: ConfigSource) -> None:
        """初始化紫鸟客户端
        
        Args:
            config: 配置对象、配置字典或配置文件路径
            
        Raises:
            ConfigurationError: 配置无效
        """
        # 解析配置
        self.config = self._parse_config(config)
        
        # 初始化组件
        self.http_client = HttpClient(
            port=self.config.socket_port,
            timeout=self.config.request_timeout,
            max_retries=self.config.max_retries,
            retry_delay=self.config.retry_delay
        )
        
        self.process_manager = ProcessManager(
            client_path=self.config.client_path,
            socket_port=self.config.socket_port,
            version=self.config.version
        )
        
        self.store_manager = StoreManager(
            http_client=self.http_client,
            user_info=self.config.get_user_info()
        )
        
        self._started = False
        
        logger.info(f"紫鸟客户端已初始化：{self.config}")
    
    def _parse_config(self, config: ConfigSource) -> ZiniaoConfig:
        """解析配置
        
        Args:
            config: 配置源
            
        Returns:
            ZiniaoConfig: 解析后的配置对象
            
        Raises:
            ConfigurationError: 配置解析失败
        """
        if isinstance(config, ZiniaoConfig):
            return config
        
        elif isinstance(config, dict):
            return ZiniaoConfig.from_dict(config)  # type: ignore
        
        elif isinstance(config, str):
            # 假设是文件路径
            return ZiniaoConfig.from_json_file(config)
        
        else:
            raise ConfigurationError(
                f"不支持的配置类型：{type(config)}",
                {"type": str(type(config))}
            )
    
    def start(
        self,
        kill_existing: bool = False,
        update_core: bool = False,
        wait_time: int = 5
    ) -> None:
        """启动紫鸟客户端
        
        Args:
            kill_existing: 是否自动关闭已存在的进程，默认 False（会询问用户）
            update_core: 是否在启动后更新内核，默认 False
            wait_time: 启动后等待时间（秒），默认 5
            
        Raises:
            BrowserStartError: 启动失败
        """
        if self._started:
            logger.warning("客户端已启动，跳过重复启动")
            return
        
        logger.info("=== 启动紫鸟客户端 ===")
        
        # 关闭已存在的进程
        if not self.process_manager.kill_existing_process():
            logger.info("用户取消启动")
            return
        
        # 启动客户端
        self.process_manager.start_browser(wait_time=wait_time)
        
        self._started = True
        
        # 更新内核（如果需要）
        if update_core:
            logger.info("=== 更新浏览器内核 ===")
            self.update_core()
    
    def stop(self) -> None:
        """关闭紫鸟客户端
        
        会先关闭客户端进程，然后发送退出命令。
        """
        if not self._started:
            logger.warning("客户端未启动，无需关闭")
            return
        
        logger.info("=== 关闭紫鸟客户端 ===")
        
        try:
            # 发送退出命令
            self._send_exit()
            
            # 等待一下让客户端处理
            time.sleep(2)
            
            # 终止进程（如果还在运行）
            self.process_manager.terminate()
            
        except Exception as e:
            logger.error(f"关闭客户端时出错：{e}")
        
        finally:
            self._started = False
            logger.info("客户端已关闭")
    
    def update_core(self, max_wait_time: int = 300) -> None:
        """更新浏览器内核
        
        需要客户端版本 5.285.7 以上。
        会循环调用直到更新完成或超时。
        
        Args:
            max_wait_time: 最大等待时间（秒），默认 300（5分钟）
            
        Raises:
            ClientNotStartedError: 客户端未启动
            UnsupportedVersionError: 版本不支持
            CoreUpdateError: 更新失败
        """
        if not self._started:
            raise ClientNotStartedError()
        
        logger.info("开始更新内核...")
        
        start_time = time.time()
        
        while True:
            # 检查超时
            if time.time() - start_time > max_wait_time:
                raise CoreUpdateError(
                    f"更新内核超时（{max_wait_time} 秒）",
                    {"max_wait_time": max_wait_time}
                )
            
            # 发送更新请求
            data = {
                "action": "updateCore",
                "requestId": str(uuid.uuid4()),
            }
            data.update(self.config.get_user_info())
            
            result = self.http_client.send_request(data, retry_on_none=True)
            
            if result is None:
                logger.info("等待客户端启动...")
                time.sleep(2)
                continue
            
            status_code = result.get("statusCode")
            
            if status_code is None or status_code == -10003:
                raise UnsupportedVersionError(
                    "updateCore",
                    required_version="5.285.7"
                )
            
            elif status_code == 0:
                logger.info("内核更新完成")
                return
            
            else:
                logger.info(
                    f"等待更新内核：{json.dumps(result, ensure_ascii=False)}"
                )
                time.sleep(2)
    
    def get_store_list(self, use_cache: bool = False) -> List[Store]:
        """获取店铺列表
        
        Args:
            use_cache: 是否使用缓存，默认 False
            
        Returns:
            List[Store]: 店铺列表
            
        Raises:
            ClientNotStartedError: 客户端未启动
            StoreOperationError: 获取失败
        """
        if not self._started:
            raise ClientNotStartedError()
        
        return self.store_manager.get_store_list(use_cache=use_cache)
    
    def find_stores_by_name(
        self,
        name: str,
        exact_match: bool = False
    ) -> List[Store]:
        """通过名称搜索店铺
        
        Args:
            name: 店铺名称
            exact_match: 是否精确匹配，False 则模糊匹配
            
        Returns:
            List[Store]: 匹配的店铺列表
            
        Raises:
            ClientNotStartedError: 客户端未启动
        """
        if not self._started:
            raise ClientNotStartedError()
        
        return self.store_manager.find_stores_by_name(
            name,
            exact_match_mode=exact_match
        )
    
    def open_store(
        self,
        store_id: str,
        **options
    ) -> BrowserSession:
        """通过店铺 ID 打开店铺
        
        Args:
            store_id: 店铺 ID 或 OAuth 标识
            **options: 打开店铺的选项
            
        Returns:
            BrowserSession: 浏览器会话对象
            
        Raises:
            ClientNotStartedError: 客户端未启动
            StoreOperationError: 打开失败
        """
        if not self._started:
            raise ClientNotStartedError()
        
        return self.store_manager.open_store(store_id, **options)
    
    def open_store_by_name(
        self,
        store_name: str,
        exact_match: bool = False,
        **options
    ) -> BrowserSession:
        """通过店铺名称打开店铺
        
        Args:
            store_name: 店铺名称（支持模糊匹配）
            exact_match: 是否精确匹配，默认 False（模糊匹配）
            **options: 打开店铺的选项
            
        Returns:
            BrowserSession: 浏览器会话对象
            
        Raises:
            ClientNotStartedError: 客户端未启动
            StoreNotFoundError: 未找到匹配的店铺
            MultipleStoresFoundError: 找到多个匹配的店铺
            StoreOperationError: 打开失败
        """
        if not self._started:
            raise ClientNotStartedError()
        
        return self.store_manager.open_store_by_name(
            store_name,
            exact_match_mode=exact_match,
            **options
        )
    
    def open_stores_by_names(
        self,
        store_names: List[str],
        max_workers: int = 3,
        exact_match: bool = False,
        **options
    ) -> Dict[str, BrowserSession]:
        """并发打开多个店铺（通过店铺名称）
        
        Args:
            store_names: 店铺名称列表
            max_workers: 最大并发数，默认 3
            exact_match: 是否精确匹配，默认 False
            **options: 打开店铺的选项
            
        Returns:
            Dict[str, BrowserSession]: 店铺名称到浏览器会话的映射
            
        Note:
            如果某个店铺打开失败，会记录错误但不会中断其他店铺的打开。
            返回的字典中只包含成功打开的店铺。
            
        Raises:
            ClientNotStartedError: 客户端未启动
        """
        if not self._started:
            raise ClientNotStartedError()
        
        return self.store_manager.open_stores_by_names(
            store_names,
            max_workers=max_workers,
            exact_match_mode=exact_match,
            **options
        )
    
    def close_store(self, store_id: str) -> None:
        """关闭店铺
        
        Args:
            store_id: 店铺 ID/OAuth
            
        Raises:
            ClientNotStartedError: 客户端未启动
            StoreOperationError: 关闭失败
        """
        if not self._started:
            raise ClientNotStartedError()
        
        self.store_manager.close_store(store_id)
    
    def _send_exit(self) -> None:
        """发送退出命令到客户端"""
        data = {
            "action": "exit",
            "requestId": str(uuid.uuid4())
        }
        data.update(self.config.get_user_info())
        
        logger.debug("发送退出命令...")
        
        try:
            self.http_client.send_request(data)
        except Exception as e:
            logger.warning(f"发送退出命令失败：{e}")
    
    def is_started(self) -> bool:
        """检查客户端是否已启动
        
        Returns:
            bool: 已启动返回 True
        """
        return self._started
    
    def is_process_running(self) -> bool:
        """检查客户端进程是否正在运行
        
        Returns:
            bool: 运行中返回 True
        """
        return self.process_manager.is_running()
    
    def __enter__(self) -> "ZiniaoClient":
        """上下文管理器入口，自动启动客户端"""
        if not self._started:
            self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """上下文管理器退出，自动关闭客户端"""
        self.stop()
    
    def __repr__(self) -> str:
        return (
            f"ZiniaoClient(version='{self.config.version}', "
            f"port={self.config.socket_port}, started={self._started})"
        )
