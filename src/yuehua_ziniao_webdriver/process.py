"""进程管理模块

提供紫鸟客户端进程的启动、关闭和管理功能。
"""

import os
import time
import subprocess
import logging
from typing import List, Optional

from .types import VersionType
from .utils import is_windows, is_mac, is_linux
from .exceptions import BrowserStartError, ProcessError

logger = logging.getLogger(__name__)


class ProcessManager:
    """进程管理器
    
    负责紫鸟客户端进程的启动和关闭。
    """
    
    def __init__(
        self,
        client_path: str,
        socket_port: int,
        version: VersionType = "v6"
    ) -> None:
        """初始化进程管理器
        
        Args:
            client_path: 客户端可执行文件路径
            socket_port: 通信端口
            version: 客户端版本
        """
        self.client_path = client_path
        self.socket_port = socket_port
        self.version = version
        self.process: Optional[subprocess.Popen] = None
        
        logger.debug(
            f"初始化进程管理器：client_path={client_path}, "
            f"socket_port={socket_port}, version={version}"
        )
    
    def kill_existing_process(self) -> bool:
        """关闭已存在的紫鸟客户端进程
        
        Returns:
            bool: 成功关闭返回 True，用户取消返回 False
            
        Raises:
            ProcessError: 进程关闭失败
        """
        
        try:
            if is_windows():
                process_name = self._get_windows_process_name()
                logger.info(f"关闭 Windows 进程：{process_name}")
                result = os.system(f'taskkill /f /t /im {process_name}')
                time.sleep(3)
                
                if result != 0:
                    logger.warning(f"关闭进程返回非零状态码：{result}")
                
            elif is_mac():
                logger.info("关闭 macOS 进程：ziniao")
                os.system('killall ziniao')
                time.sleep(3)
                
            elif is_linux():
                logger.info("关闭 Linux 进程：ziniaobrowser")
                os.system('killall ziniaobrowser')
                time.sleep(3)
            
            else:
                raise ProcessError("不支持的操作系统平台")
            
            logger.info("成功关闭已存在的进程")
            return True
            
        except Exception as e:
            error_msg = f"关闭进程失败：{e}"
            logger.error(error_msg)
            raise ProcessError(error_msg, {"error": str(e)})
    
    def _get_windows_process_name(self) -> str:
        """获取 Windows 平台的进程名称
        
        Returns:
            str: 进程名称
        """
        if self.version == "v5":
            return "SuperBrowser.exe"
        else:
            return "ziniao.exe"
    
    def start_browser(self, wait_time: int = 5) -> None:
        """启动紫鸟客户端
        
        Args:
            wait_time: 启动后等待时间（秒），默认 5 秒
            
        Raises:
            BrowserStartError: 启动失败
        """
        try:
            cmd = self._build_start_command()
            
            logger.info(f"启动客户端：{' '.join(cmd)}")
            
            # 启动进程
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            logger.info(f"客户端进程已启动，PID: {self.process.pid}")
            
            # 等待客户端启动完成
            logger.debug(f"等待 {wait_time} 秒让客户端完成启动...")
            time.sleep(wait_time)
            
            # 检查进程是否仍在运行
            if self.process.poll() is not None:
                # 进程已退出
                stdout, stderr = self.process.communicate()
                error_msg = (
                    f"客户端启动后立即退出，退出码：{self.process.returncode}\n"
                    f"stdout: {stdout.decode('utf-8', errors='ignore')}\n"
                    f"stderr: {stderr.decode('utf-8', errors='ignore')}"
                )
                logger.error(error_msg)
                raise BrowserStartError(error_msg)
            
            logger.info("客户端启动成功")
            
        except BrowserStartError:
            raise
        except Exception as e:
            error_msg = f"启动客户端失败：{e}"
            logger.error(error_msg)
            raise BrowserStartError(error_msg, {"error": str(e)})
    
    def _build_start_command(self) -> List[str]:
        """构建启动命令
        
        Returns:
            List[str]: 命令参数列表
            
        Raises:
            ProcessError: 不支持的平台
        """
        port_str = str(self.socket_port)
        
        if is_windows():
            return [
                self.client_path,
                '--run_type=web_driver',
                '--ipc_type=http',
                f'--port={port_str}'
            ]
        
        elif is_mac():
            return [
                'open',
                '-a',
                self.client_path,
                '--args',
                '--run_type=web_driver',
                '--ipc_type=http',
                f'--port={port_str}'
            ]
        
        elif is_linux():
            return [
                self.client_path,
                '--no-sandbox',
                '--run_type=web_driver',
                '--ipc_type=http',
                f'--port={port_str}'
            ]
        
        else:
            raise ProcessError("不支持的操作系统平台")
    
    def is_running(self) -> bool:
        """检查客户端进程是否正在运行
        
        Returns:
            bool: 运行中返回 True
        """
        if self.process is None:
            return False
        
        return self.process.poll() is None
    
    def get_pid(self) -> Optional[int]:
        """获取进程 PID
        
        Returns:
            Optional[int]: PID，如果进程未启动返回 None
        """
        if self.process is None:
            return None
        return self.process.pid
    
    def terminate(self, wait_timeout: int = 10) -> bool:
        """终止客户端进程
        
        Args:
            wait_timeout: 等待进程终止的超时时间（秒）
            
        Returns:
            bool: 成功终止返回 True
        """
        if self.process is None:
            logger.debug("进程未启动，无需终止")
            return True
        
        if not self.is_running():
            logger.debug("进程已退出，无需终止")
            return True
        
        try:
            logger.info(f"终止进程 PID: {self.process.pid}")
            self.process.terminate()
            
            # 等待进程退出
            try:
                self.process.wait(timeout=wait_timeout)
                logger.info("进程已正常终止")
                return True
            except subprocess.TimeoutExpired:
                # 强制杀死
                logger.warning(f"进程 {wait_timeout} 秒内未退出，强制杀死")
                self.process.kill()
                self.process.wait()
                logger.info("进程已强制杀死")
                return True
                
        except Exception as e:
            logger.error(f"终止进程失败：{e}")
            return False
    
    def __repr__(self) -> str:
        return (
            f"ProcessManager(client_path='{self.client_path}', "
            f"socket_port={self.socket_port}, version='{self.version}', "
            f"running={self.is_running()})"
        )
