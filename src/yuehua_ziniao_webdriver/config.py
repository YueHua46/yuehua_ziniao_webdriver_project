"""配置管理模块

提供配置类和配置加载功能。
"""

import json
import os
import shlex
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional, Dict, Any, List

from .types import VersionType, ConfigDict
from .exceptions import ConfigurationError


@dataclass
class ZiniaoConfig:
    """紫鸟浏览器客户端配置类
    
    使用 dataclass 提供类型提示和默认值。
    
    Attributes:
        client_path: 紫鸟客户端可执行文件路径（必需）
        socket_port: 客户端通信端口，默认 16851
        host: SDK 连接紫鸟 WebDriver HTTP 服务的主机，默认 127.0.0.1
        listen_ip: 紫鸟 WebDriver HTTP 服务监听地址（可选）
        cdp_host: SDK 连接店铺 CDP 调试端口的主机，默认与 host 一致
        cdp_proxy_host: 对外暴露 CDP 调试端口的本机监听地址（可选）
        extra_args: 启动紫鸟客户端时追加的命令行参数
        company: 企业名称（用于登录）
        username: 用户名（用于登录）
        password: 密码（用于登录）
        version: 客户端版本，"v5" 或 "v6"，默认 "v6"
        request_timeout: HTTP 请求超时时间（秒），默认 120
        max_retries: 失败重试次数，默认 3
        retry_delay: 重试延迟时间（秒），默认 2.0
    """
    
    client_path: str = ""
    socket_port: int = 16851
    host: str = "127.0.0.1"
    listen_ip: Optional[str] = None
    cdp_host: Optional[str] = None
    cdp_proxy_host: Optional[str] = None
    extra_args: List[str] = field(default_factory=list)
    company: str = ""
    username: str = ""
    password: str = ""
    version: VersionType = "v6"
    request_timeout: int = 120
    max_retries: int = 3
    retry_delay: float = 2.0
    
    def __post_init__(self) -> None:
        """初始化后的验证"""
        self.validate()
    
    def validate(self) -> None:
        """验证配置有效性
        
        Raises:
            ConfigurationError: 当配置无效时
        """
        # 先验证版本，V6 支持从默认安装位置自动查找启动程序。
        if self.version not in ("v5", "v6"):
            raise ConfigurationError(
                f"version 必须是 'v5' 或 'v6'，当前值：{self.version}",
                {"version": self.version}
            )

        # 验证必需字段
        if not self.client_path and self.version != "v6":
            raise ConfigurationError("client_path 不能为空")

        if self.version == "v6":
            self.client_path = self._resolve_v6_client_path(self.client_path)
        
        # 验证客户端路径是否存在
        if not os.path.exists(self.client_path):
            raise ConfigurationError(
                f"客户端路径不存在：{self.client_path}",
                {"path": self.client_path}
            )
        
        # 验证端口范围
        if not (1024 <= self.socket_port <= 65535):
            raise ConfigurationError(
                f"端口号必须在 1024-65535 之间，当前值：{self.socket_port}",
                {"port": self.socket_port}
            )

        # 验证主机配置
        if not self.host:
            raise ConfigurationError("host 不能为空")

        if self.cdp_host == "":
            raise ConfigurationError("cdp_host 不能是空字符串")

        if self.cdp_proxy_host == "":
            raise ConfigurationError("cdp_proxy_host 不能是空字符串")

        if self.listen_ip == "":
            raise ConfigurationError("listen_ip 不能是空字符串")

        # 验证额外启动参数
        if self.extra_args is None:
            self.extra_args = []
        elif not isinstance(self.extra_args, list) or not all(
            isinstance(arg, str) for arg in self.extra_args
        ):
            raise ConfigurationError(
                "extra_args 必须是字符串列表",
                {"extra_args": self.extra_args}
            )
        
        # 验证超时时间
        if self.request_timeout <= 0:
            raise ConfigurationError(
                f"request_timeout 必须大于 0，当前值：{self.request_timeout}",
                {"timeout": self.request_timeout}
            )
        
        # 验证重试次数
        if self.max_retries < 0:
            raise ConfigurationError(
                f"max_retries 不能为负数，当前值：{self.max_retries}",
                {"retries": self.max_retries}
            )
        
        # 验证重试延迟
        if self.retry_delay < 0:
            raise ConfigurationError(
                f"retry_delay 不能为负数，当前值：{self.retry_delay}",
                {"delay": self.retry_delay}
            )
    
    @classmethod
    def _resolve_v6_client_path(cls, client_path: str) -> str:
        """解析 V6 客户端路径。

        Windows 下允许调用方留空或继续传旧路径；如果旧路径不存在，自动搜索
        V6 常见默认安装位置，如 C:\\Program Files\\ziniao\\ziniao.exe。
        """
        if client_path and os.path.exists(client_path):
            return client_path
        if os.name != "nt":
            return client_path

        candidates = cls._windows_v6_client_path_candidates(client_path)
        for candidate in candidates:
            if os.path.exists(candidate):
                return candidate

        searched = "\n".join(f"- {candidate}" for candidate in candidates)
        raise ConfigurationError(
            "未找到紫鸟 V6 启动程序 ziniao.exe",
            {"searched_paths": searched}
        )

    @staticmethod
    def _windows_v6_client_path_candidates(client_path: str) -> List[str]:
        candidates = [
            client_path,
            os.getenv("ZINIAO_CLIENT_PATH", ""),
        ]
        base_paths = [
            r"C:\Program Files",
            r"C:\Program Files (x86)",
            os.getenv("ProgramW6432", ""),
            os.getenv("ProgramFiles", r"C:\Program Files"),
            os.getenv("ProgramFiles(x86)", r"C:\Program Files (x86)"),
            os.getenv("LOCALAPPDATA", ""),
            os.getenv("APPDATA", ""),
        ]

        for base in base_paths:
            if not base:
                continue
            candidates.extend(
                [
                    str(Path(base) / "ziniao" / "ziniao.exe"),
                    str(Path(base) / "ZiNiao" / "ziniao.exe"),
                    str(Path(base) / "Programs" / "ziniao" / "ziniao.exe"),
                ]
            )

        unique_candidates: List[str] = []
        seen = set()
        for candidate in candidates:
            if not candidate:
                continue
            normalized = os.path.normcase(os.path.normpath(candidate))
            if normalized in seen:
                continue
            seen.add(normalized)
            unique_candidates.append(candidate)
        return unique_candidates

    @classmethod
    def from_dict(cls, config_dict: ConfigDict) -> "ZiniaoConfig":
        """从字典创建配置对象
        
        Args:
            config_dict: 配置字典
            
        Returns:
            ZiniaoConfig: 配置对象
            
        Raises:
            ConfigurationError: 当配置无效时
        """
        try:
            return cls(**config_dict)  # type: ignore
        except TypeError as e:
            raise ConfigurationError(f"配置字典格式错误：{e}", {"dict": config_dict})
    
    @classmethod
    def from_json_file(cls, file_path: str) -> "ZiniaoConfig":
        """从 JSON 文件加载配置
        
        Args:
            file_path: JSON 配置文件路径
            
        Returns:
            ZiniaoConfig: 配置对象
            
        Raises:
            ConfigurationError: 当文件不存在或格式错误时
        """
        path = Path(file_path)
        
        if not path.exists():
            raise ConfigurationError(
                f"配置文件不存在：{file_path}",
                {"path": file_path}
            )
        
        try:
            with open(path, "r", encoding="utf-8") as f:
                config_dict = json.load(f)
            return cls.from_dict(config_dict)
        except json.JSONDecodeError as e:
            raise ConfigurationError(
                f"JSON 文件格式错误：{e}",
                {"path": file_path, "error": str(e)}
            )
        except Exception as e:
            raise ConfigurationError(
                f"加载配置文件失败：{e}",
                {"path": file_path, "error": str(e)}
            )
    
    @classmethod
    def from_env(cls, prefix: str = "ZINIAO_") -> "ZiniaoConfig":
        """从环境变量加载配置
        
        环境变量命名规则：前缀 + 大写字段名
        例如：ZINIAO_CLIENT_PATH, ZINIAO_SOCKET_PORT
        
        Args:
            prefix: 环境变量前缀，默认 "ZINIAO_"
            
        Returns:
            ZiniaoConfig: 配置对象
            
        Raises:
            ConfigurationError: 当必需的环境变量不存在时
        """
        config_dict: Dict[str, Any] = {}
        
        # 字段映射：Python 字段名 -> 环境变量名
        field_mapping = {
            "client_path": f"{prefix}CLIENT_PATH",
            "socket_port": f"{prefix}SOCKET_PORT",
            "host": f"{prefix}HOST",
            "listen_ip": f"{prefix}LISTEN_IP",
            "cdp_host": f"{prefix}CDP_HOST",
            "cdp_proxy_host": f"{prefix}CDP_PROXY_HOST",
            "extra_args": f"{prefix}EXTRA_ARGS",
            "company": f"{prefix}COMPANY",
            "username": f"{prefix}USERNAME",
            "password": f"{prefix}PASSWORD",
            "version": f"{prefix}VERSION",
            "request_timeout": f"{prefix}REQUEST_TIMEOUT",
            "max_retries": f"{prefix}MAX_RETRIES",
            "retry_delay": f"{prefix}RETRY_DELAY",
        }
        
        # 从环境变量读取
        for field_name, env_name in field_mapping.items():
            env_value = os.getenv(env_name)
            if env_value is not None:
                # 类型转换
                if field_name == "socket_port":
                    config_dict[field_name] = int(env_value)
                elif field_name == "request_timeout":
                    config_dict[field_name] = int(env_value)
                elif field_name == "max_retries":
                    config_dict[field_name] = int(env_value)
                elif field_name == "retry_delay":
                    config_dict[field_name] = float(env_value)
                elif field_name == "extra_args":
                    config_dict[field_name] = shlex.split(env_value)
                else:
                    config_dict[field_name] = env_value
        
        # 检查必需字段
        if "client_path" not in config_dict:
            raise ConfigurationError(
                f"环境变量 {prefix}CLIENT_PATH 未设置",
                {"required_env": f"{prefix}CLIENT_PATH"}
            )
        
        return cls.from_dict(config_dict)  # type: ignore
    
    def to_dict(self) -> ConfigDict:
        """将配置转换为字典
        
        Returns:
            ConfigDict: 配置字典
        """
        return asdict(self)  # type: ignore
    
    def to_json_file(self, file_path: str, indent: int = 2) -> None:
        """将配置保存到 JSON 文件
        
        Args:
            file_path: 目标文件路径
            indent: JSON 缩进空格数，默认 2
            
        Raises:
            ConfigurationError: 当保存失败时
        """
        try:
            path = Path(file_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(path, "w", encoding="utf-8") as f:
                json.dump(self.to_dict(), f, ensure_ascii=False, indent=indent)
        except Exception as e:
            raise ConfigurationError(
                f"保存配置文件失败：{e}",
                {"path": file_path, "error": str(e)}
            )
    
    def get_user_info(self) -> Dict[str, str]:
        """获取用户登录信息字典
        
        用于 HTTP 请求。
        
        Returns:
            Dict[str, str]: 包含 company, username, password 的字典
        """
        return {
            "company": self.company,
            "username": self.username,
            "password": self.password
        }
    
    def __repr__(self) -> str:
        """安全的字符串表示（隐藏密码）"""
        return (
            f"ZiniaoConfig("
            f"client_path='{self.client_path}', "
            f"socket_port={self.socket_port}, "
            f"host='{self.host}', "
            f"listen_ip='{self.listen_ip}', "
            f"cdp_host='{self.cdp_host}', "
            f"cdp_proxy_host='{self.cdp_proxy_host}', "
            f"company='{self.company}', "
            f"username='{self.username}', "
            f"password='***', "
            f"version='{self.version}'"
            f")"
        )
