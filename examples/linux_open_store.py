"""Linux 环境打开紫鸟店铺示例。

运行前示例：
    export ZINIAO_CLIENT_PATH=/opt/ziniao/ziniaobrowser
    export ZINIAO_COMPANY='你的企业名'
    export ZINIAO_USERNAME='你的用户名'
    export ZINIAO_PASSWORD='你的密码'
    export ZINIAO_LISTEN_IP=0.0.0.0
    python examples/linux_open_store.py '你的店铺名'

暴露给其他机器连接 CDP：
    export ZINIAO_LISTEN_IP=0.0.0.0
    export ZINIAO_CDP_HOST=127.0.0.1
    export ZINIAO_CDP_PROXY_HOST=192.168.1.20

说明：
    - Linux 版紫鸟需使用 V6，建议 6.25.3.3 或更新版本。
    - 默认假设 Python 脚本和紫鸟客户端在同一台 Linux 机器上运行。
    - 如果是无桌面服务器，需要先准备可用的图形环境或 DISPLAY。
"""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path


# 未安装包时也可直接运行：将项目 src 加入 path。
_here = Path(__file__).resolve().parent
_src = _here.parent / "src"
if _src.exists() and str(_src) not in sys.path:
    sys.path.insert(0, str(_src))

from yuehua_ziniao_webdriver import (  # noqa: E402
    StoreOpenOptions,
    ZiniaoClient,
    ZiniaoConfig,
    setup_logging,
)


def env_required(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"请先设置环境变量：{name}")
    return value


def build_config() -> ZiniaoConfig:
    client_path = os.getenv("ZINIAO_CLIENT_PATH", "/opt/ziniao/ziniaobrowser")
    if not Path(client_path).exists():
        raise RuntimeError(f"紫鸟 Linux 客户端不存在：{client_path}")

    return ZiniaoConfig(
        client_path=client_path,
        host=os.getenv("ZINIAO_HOST", "127.0.0.1"),
        listen_ip=os.getenv("ZINIAO_LISTEN_IP"),
        cdp_host=os.getenv("ZINIAO_CDP_HOST"),
        cdp_proxy_host=os.getenv("ZINIAO_CDP_PROXY_HOST"),
        company=env_required("ZINIAO_COMPANY"),
        username=env_required("ZINIAO_USERNAME"),
        password=env_required("ZINIAO_PASSWORD"),
        version="v6",
        socket_port=int(os.getenv("ZINIAO_SOCKET_PORT", "16851")),
        request_timeout=120,
        max_retries=3,
        retry_delay=2.0,
    )


def main() -> None:
    if len(sys.argv) < 2:
        raise RuntimeError("用法：python examples/linux_open_store.py '店铺名'")

    if sys.platform.startswith("linux") and not os.getenv("DISPLAY"):
        print("警告：当前没有 DISPLAY，紫鸟客户端可能无法启动图形窗口。")

    store_name = sys.argv[1]

    setup_logging(level=logging.INFO, log_file="ziniao-linux.log")
    config = build_config()

    # Linux 上一般先跑有界面模式；如果紫鸟和你的场景确认支持无头，再改 isHeadless=1。
    options: StoreOpenOptions = {
        "isHeadless": 0,
        "isWebDriverReadOnlyMode": 0,
        "isWaitPluginUpdate": 0,
        "isLoadUserPlugin": False,
    }

    client = ZiniaoClient(config)

    try:
        client.start(
            kill_existing=True,
            update_core=True,
            wait_time=8,
        )

        session = client.open_store_by_name(
            store_name,
            exact_match=True,
            options=options,
        )

        print(f"店铺已打开：{session.store_name}")
        print(f"调试端口：{session.port}")
        cdp_host = session.proxy_host or session.host
        print(f"CDP 地址：{cdp_host}:{session.port}")

        tab = session.get_tab()
        print(f"当前页面：{getattr(tab, 'url', '')}")

        # 这里开始写你的业务自动化逻辑。
        # tab.get("https://www.example.com")

        input("按回车关闭店铺并退出...")
        session.close()

    finally:
        client.stop()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n用户中断")
    except Exception as exc:
        print(f"运行失败：{exc}")
        raise
