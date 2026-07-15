"""HTTP 通信客户端模块

封装与紫鸟客户端的 HTTP 通信，提供重试机制和错误处理。
"""

import json
import logging
import time
import uuid
from typing import Dict, Any, Optional

import requests

from .types import HttpRequestData, HttpResponse
from .exceptions import (
    CommunicationError,
    TimeoutError as ZiniaoTimeoutError,
    AuthenticationError
)

logger = logging.getLogger(__name__)


class HttpClient:
    """HTTP 通信客户端
    
    负责与紫鸟客户端进行 HTTP 通信。
    """
    
    def __init__(
        self,
        port: int,
        host: str = "127.0.0.1",
        timeout: int = 120,
        max_retries: int = 3,
        retry_delay: float = 2.0
    ) -> None:
        """初始化 HTTP 客户端
        
        Args:
            port: 通信端口
            host: 紫鸟 WebDriver HTTP 服务主机
            timeout: 请求超时时间（秒）
            max_retries: 最大重试次数
            retry_delay: 重试延迟时间（秒）
        """
        self.port = port
        self.host = host
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.base_url = self._build_base_url(host, port)
        
        logger.debug(
            f"初始化 HTTP 客户端：host={host}, port={port}, timeout={timeout}, "
            f"max_retries={max_retries}, retry_delay={retry_delay}"
        )

    @staticmethod
    def _build_base_url(host: str, port: int) -> str:
        if ":" in host and not host.startswith("["):
            host = f"[{host}]"
        return f"http://{host}:{port}"
    
    def send_request(
        self,
        data: Dict[str, Any],
        retry_on_none: bool = False
    ) -> Optional[HttpResponse]:
        """发送 HTTP 请求
        
        Args:
            data: 请求数据字典
            retry_on_none: 当返回 None 时是否重试，默认 False
            
        Returns:
            Optional[HttpResponse]: 响应数据，失败返回 None
            
        Raises:
            CommunicationError: 通信失败
            ZiniaoTimeoutError: 请求超时
            AuthenticationError: 认证失败
        """
        action = data.get("action", "unknown")
        request_id = data.get("requestId", "unknown")
        
        logger.debug(f"发送请求：action={action}, requestId={request_id}")
        
        # 重试逻辑
        last_exception: Optional[Exception] = None
        
        for attempt in range(self.max_retries + 1):
            try:
                # 发送 POST 请求
                response = requests.post(
                    self.base_url,
                    data=json.dumps(data).encode('utf-8'),
                    timeout=self.timeout
                )
                response.encoding = "utf-8"
                
                # 解析响应
                result = response.json()
                
                # 检查是否需要重试（返回 None）
                if result is None and retry_on_none and attempt < self.max_retries:
                    logger.warning(
                        f"请求返回 None，{self.retry_delay} 秒后重试 "
                        f"(尝试 {attempt + 1}/{self.max_retries})"
                    )
                    time.sleep(self.retry_delay)
                    continue
                
                # 检查状态码
                status_code = result.get("statusCode") if result else None
                
                # 认证失败
                if status_code == -10003:
                    error_msg = f"认证失败：{json.dumps(result, ensure_ascii=False)}"
                    logger.error(error_msg)
                    raise AuthenticationError(error_msg, result)
                
                logger.debug(
                    f"请求成功：action={action}, statusCode={status_code}"
                )
                
                return result
                
            except requests.Timeout as e:
                last_exception = e
                logger.warning(
                    f"请求超时：action={action}, attempt={attempt + 1}/{self.max_retries + 1}"
                )
                
                if attempt < self.max_retries:
                    logger.info(f"等待 {self.retry_delay} 秒后重试...")
                    time.sleep(self.retry_delay)
                    continue
                
                # 最后一次尝试失败
                error_msg = f"请求超时（已重试 {self.max_retries} 次）：{e}"
                logger.error(error_msg)
                raise ZiniaoTimeoutError(error_msg, {"action": action, "error": str(e)})
            
            except requests.ConnectionError as e:
                last_exception = e
                logger.warning(
                    f"连接失败：action={action}, attempt={attempt + 1}/{self.max_retries + 1}, "
                    f"error={e}"
                )
                
                if attempt < self.max_retries:
                    logger.info(f"等待 {self.retry_delay} 秒后重试...")
                    time.sleep(self.retry_delay)
                    continue
                
                # 最后一次尝试失败
                error_msg = (
                    f"无法连接到紫鸟客户端（已重试 {self.max_retries} 次），"
                    f"请确认客户端已启动且端口 {self.port} 可访问"
                )
                logger.error(error_msg)
                raise CommunicationError(error_msg, {"port": self.port, "error": str(e)})
            
            except json.JSONDecodeError as e:
                last_exception = e
                error_msg = f"响应 JSON 解析失败：{e}"
                logger.error(error_msg)
                raise CommunicationError(error_msg, {"error": str(e)})
            
            except Exception as e:
                last_exception = e
                logger.error(f"未知错误：action={action}, error={e}")
                
                if attempt < self.max_retries:
                    logger.info(f"等待 {self.retry_delay} 秒后重试...")
                    time.sleep(self.retry_delay)
                    continue
                
                # 最后一次尝试失败
                error_msg = f"通信失败（已重试 {self.max_retries} 次）：{e}"
                logger.error(error_msg)
                raise CommunicationError(error_msg, {"action": action, "error": str(e)})
        
        # 不应该到达这里，但为了类型检查
        if last_exception:
            raise CommunicationError(
                f"请求失败：{last_exception}",
                {"error": str(last_exception)}
            )
        
        return None
    
    def update_port(self, new_port: int) -> None:
        """更新通信端口
        
        Args:
            new_port: 新的端口号
        """
        self.port = new_port
        self.base_url = self._build_base_url(self.host, new_port)
        logger.info(f"更新通信端口：{new_port}")

    def update_host(self, new_host: str) -> None:
        """更新通信主机。

        Args:
            new_host: 新的主机名或 IP
        """
        self.host = new_host
        self.base_url = self._build_base_url(new_host, self.port)
        logger.info(f"更新通信主机：{new_host}")
    
    def test_connection(self) -> bool:
        """测试连接是否可用
        
        Returns:
            bool: 连接正常返回 True，否则返回 False
        """
        try:
            response = requests.get(
                self.base_url,
                timeout=5
            )
            logger.debug(f"连接测试成功：port={self.port}")
            return True
        except Exception as e:
            logger.debug(f"连接测试失败：port={self.port}, error={e}")
            return False

    def wait_until_ready(
        self,
        user_info: Dict[str, str],
        timeout: float = 30,
        poll_interval: float = 0.5,
    ) -> HttpResponse:
        """等待紫鸟 HTTP JSON API 完全就绪。

        仅监听端口或启动器进程状态不足以表示 API 可用。这里使用幂等的
        getBrowserList 请求，直到收到合法 JSON 和成功状态码。
        """
        if timeout <= 0:
            raise ValueError("timeout 必须大于 0")
        if poll_interval < 0:
            raise ValueError("poll_interval 不能小于 0")

        deadline = time.monotonic() + timeout
        attempts = 0
        last_error = "尚未发送请求"

        while time.monotonic() < deadline:
            attempts += 1
            response = None
            try:
                data = {
                    "action": "getBrowserList",
                    "requestId": str(uuid.uuid4()),
                }
                data.update(user_info)
                remaining = max(0.1, deadline - time.monotonic())
                response = requests.post(
                    self.base_url,
                    data=json.dumps(data).encode("utf-8"),
                    timeout=min(5.0, remaining),
                )
                response.encoding = "utf-8"
                if not response.content:
                    raise ValueError("HTTP 响应体为空")

                result = response.json()
                if not isinstance(result, dict):
                    raise ValueError(f"响应不是 JSON 对象：{type(result).__name__}")

                status_code = result.get("statusCode")
                if status_code == 0:
                    logger.info("紫鸟客户端 HTTP API 已就绪（尝试 %s 次）", attempts)
                    return result  # type: ignore[return-value]
                if status_code == -10003:
                    error_msg = f"认证失败：{json.dumps(result, ensure_ascii=False)}"
                    raise AuthenticationError(error_msg, result)
                last_error = f"statusCode={status_code}, message={result.get('message')}"
            except AuthenticationError:
                raise
            except (requests.RequestException, ValueError) as e:
                last_error = f"{type(e).__name__}: {e}"
                logger.debug("紫鸟 HTTP API 尚未就绪（第 %s 次）：%s", attempts, e)
            finally:
                if response is not None:
                    response.close()

            remaining = deadline - time.monotonic()
            if remaining <= 0:
                break
            time.sleep(min(poll_interval, remaining))

        error_msg = f"紫鸟客户端 HTTP API 在 {timeout} 秒内未就绪"
        logger.warning("%s：%s", error_msg, last_error)
        raise CommunicationError(
            error_msg,
            {
                "host": self.host,
                "port": self.port,
                "attempts": attempts,
                "last_error": last_error,
            },
        )
    
    def __repr__(self) -> str:
        return (
            f"HttpClient(host='{self.host}', port={self.port}, "
            f"timeout={self.timeout}, max_retries={self.max_retries})"
        )
