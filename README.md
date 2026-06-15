# 紫鸟浏览器 Python SDK

[![Python Version](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

一个用于控制紫鸟浏览器的 Python SDK，提供店铺管理、浏览器自动化等功能。

## ✨ 特性

- 🚀 **简单易用**：面向对象的 API 设计，清晰直观
- 🔄 **并发支持**：支持同时打开多个店铺，提高效率
- 🔍 **智能搜索**：通过店铺名称搜索，支持模糊匹配和精确匹配
- 🛡️ **类型安全**：完整的类型提示，IDE 友好
- ⚡ **自动重试**：内置重试机制，处理网络波动
- 📝 **日志系统**：集成 Python logging，方便调试
- 🎯 **错误处理**：清晰的异常体系，易于定位问题
- 🔌 **灵活配置**：支持代码、字典、文件等多种配置方式

## 📦 安装

### 从源码安装（开发中）

```bash
# 克隆仓库
git clone https://github.com/yourusername/yuehua-ziniao-webdriver.git
cd yuehua-ziniao-webdriver

# 安装依赖
pip install -e .

# 安装开发依赖（可选）
pip install -e ".[dev]"
```

### 发布到 PyPI 后安装

```bash
pip install yuehua-ziniao-webdriver
```

## 🚀 快速开始

### 基本使用

```python
from yuehua_ziniao_webdriver import ZiniaoClient, ZiniaoConfig

# 创建配置
config = ZiniaoConfig(
    client_path=r"D:\ziniao\ziniao.exe",  # 紫鸟客户端路径
    company="你的企业名",
    username="你的用户名",
    password="你的密码",
    version="v6"  # v5 或 v6
)

# 使用上下文管理器（推荐）
with ZiniaoClient(config) as client:
    # 获取店铺列表
    stores = client.get_store_list()
    print(f"共有 {len(stores)} 个店铺")
    
    # 通过名称打开店铺
    session = client.open_store_by_name("我的店铺")
    
    # 检测 IP
    if session.check_ip():
        # 获取标签页进行操作
        tab = session.get_tab()
        tab.get("https://example.com")
    
    # 关闭店铺
    session.close()
```

### 并发打开多个店铺

```python
from yuehua_ziniao_webdriver import ZiniaoClient, ZiniaoConfig

config = ZiniaoConfig(
    client_path=r"D:\ziniao\ziniao.exe",
    company="你的企业名",
    username="你的用户名",
    password="你的密码"
)

with ZiniaoClient(config) as client:
    # 要打开的店铺名称列表
    store_names = ["店铺A", "店铺B", "店铺C"]
    
    # 并发打开（最多同时3个）
    sessions = client.open_stores_by_names(
        store_names,
        max_workers=3
    )
    
    # 处理每个店铺
    for store_name, session in sessions.items():
        if session.check_ip():
            tab = session.get_tab()
            # 进行自动化操作
            print(f"✓ {store_name} 已就绪")
    
    # 关闭所有店铺
    for session in sessions.values():
        session.close()
```

## 📚 核心功能

### 1. 客户端管理

```python
from yuehua_ziniao_webdriver import ZiniaoClient, ZiniaoConfig

config = ZiniaoConfig(...)
client = ZiniaoClient(config)

# 启动客户端
client.start(
    kill_existing=True,  # 自动关闭已存在的进程
    update_core=True     # 启动后更新内核
)

# 检查客户端状态
if client.is_started():
    print("客户端已启动")

# 关闭客户端
client.stop()
```

### 2. 店铺搜索

```python
# 模糊搜索
stores = client.find_stores_by_name("亚马逊", exact_match=False)

# 精确搜索
stores = client.find_stores_by_name("我的亚马逊店铺", exact_match=True)

# 打印结果
for store in stores:
    print(f"{store['browserName']} - {store['browserOauth']}")
```

### 3. 打开店铺

```python
# 方式 1：通过 ID/OAuth
session = client.open_store("store_id_or_oauth")

# 方式 2：通过名称（推荐）
session = client.open_store_by_name("店铺名称")

# 方式 3：并发打开多个
sessions = client.open_stores_by_names(
    ["店铺1", "店铺2", "店铺3"],
    max_workers=3
)

# 下载时弹出保存对话框
session = client.open_store_by_name(
    "店铺名称",
    options={"notPromptForDownload": 0}
)

# 不弹窗并指定下载目录
session = client.open_store_by_name(
    "店铺名称",
    options={
        "notPromptForDownload": 1,
        "forceDownloadPath": r"D:\downloads"
    }
)
```

### 4. 浏览器操作

```python
# 打开店铺
session = client.open_store_by_name("我的店铺")

# 检测 IP
if session.check_ip(timeout=60):
    print("IP 检测通过")

# 打开启动页面
session.open_launcher_page()

# 获取标签页
tab = session.get_tab()

# 导航到 URL
session.navigate("https://example.com", wait_time=2)

# 关闭会话
session.close()
```

### 平台模块（Amazon 示例）

```python
from yuehua_ziniao_webdriver import setup_logging
from yuehua_ziniao_webdriver.platforms.amazon import (
    handle_login,
    switch_language_to_cn,
    switch_site,
)

setup_logging()

session = client.open_store_by_name("我的店铺")
tab = session.get_tab()

# 切换语言与站点
switch_language_to_cn(tab)
switch_site(tab, "US")

# 如遇登录页，执行登录流程
handle_login(tab)
```

### 5. 配置管理

```python
from yuehua_ziniao_webdriver import ZiniaoConfig

# 方式 1：代码配置
config = ZiniaoConfig(
    client_path=r"D:\ziniao\ziniao.exe",
    company="企业名",
    username="用户名",
    password="密码"
)

# 方式 2：从字典
config = ZiniaoConfig.from_dict({
    "client_path": r"D:\ziniao\ziniao.exe",
    "company": "企业名",
    "username": "用户名",
    "password": "密码"
})

# 方式 3：从 JSON 文件
config = ZiniaoConfig.from_json_file("config.json")

# 方式 4：从环境变量
config = ZiniaoConfig.from_env(prefix="ZINIAO_")

# 保存配置到文件
config.to_json_file("config.json")
```

### 6. 错误处理

```python
from yuehua_ziniao_webdriver import (
    StoreNotFoundError,
    MultipleStoresFoundError,
    StoreOperationError
)

try:
    session = client.open_store_by_name("店铺名称")
    
except StoreNotFoundError as e:
    print(f"未找到店铺：{e.store_identifier}")
    
except MultipleStoresFoundError as e:
    print(f"找到多个匹配的店铺：{e.store_names}")
    
except StoreOperationError as e:
    print(f"操作失败：{e.message}")
```

### 7. 日志配置

```python
from yuehua_ziniao_webdriver import setup_logging
import logging

# 配置日志
setup_logging(
    level=logging.INFO,
    log_file="ziniao.log"  # 可选：输出到文件
)
```

## 🔧 配置参数

| 参数 | 类型 | 必需 | 默认值 | 说明 |
|------|------|------|--------|------|
| `client_path` | `str` | ❌ | `""` | 紫鸟客户端可执行文件路径；Windows 默认安装的 V5/V6 可留空自动探测 |
| `company` | `str` | ✅ | - | 企业名称（登录用） |
| `username` | `str` | ✅ | - | 用户名（登录用） |
| `password` | `str` | ✅ | - | 密码（登录用） |
| `socket_port` | `int` | ❌ | `16851` | 通信端口 |
| `version` | `"v5" \| "v6"` | ❌ | `"v6"` | 客户端版本 |
| `request_timeout` | `int` | ❌ | `120` | 请求超时时间（秒） |
| `max_retries` | `int` | ❌ | `3` | 最大重试次数 |
| `retry_delay` | `float` | ❌ | `2.0` | 重试延迟（秒） |

## 📖 API 文档

### ZiniaoClient

主客户端类，提供所有核心功能。

#### 方法

- `start(kill_existing=False, update_core=False, wait_time=5)` - 启动客户端
- `stop()` - 关闭客户端
- `update_core(max_wait_time=300)` - 更新浏览器内核
- `get_store_list(use_cache=False)` - 获取店铺列表
- `find_stores_by_name(name, exact_match=False)` - 搜索店铺
- `open_store(store_id, **options)` - 通过 ID 打开店铺
- `open_store_by_name(store_name, exact_match=False, **options)` - 通过名称打开店铺
- `open_stores_by_names(store_names, max_workers=3, exact_match=False, **options)` - 并发打开多个店铺
- `close_store(store_id)` - 关闭店铺

常用 `options`：

- `isHeadless`：无头模式，`0=否`、`1=是`
- `isWebDriverReadOnlyMode`：WebDriver 只读模式，`0=否`、`1=是`
- `notPromptForDownload`：下载是否不弹窗，`1=不弹窗`、`0=弹窗`；不传则跟随紫鸟版本/店铺内核默认行为
- `forceDownloadPath`：强制文件下载路径，需传绝对路径
- `cookieTypeSave`：Cookie 保存类型，`0=默认`、`1=不提交`

### BrowserSession

浏览器会话类，表示一个已打开的店铺。

#### 属性

- `browser` - DrissionPage 的 Chromium 对象
- `store_id` - 店铺 ID
- `store_name` - 店铺名称
- `port` - 调试端口

#### 方法

- `get_tab(index=-1)` - 获取标签页
- `check_ip(ip_check_url=None, timeout=60)` - 检测 IP
- `open_launcher_page(launcher_page=None, wait_time=6)` - 打开启动页面
- `navigate(url, wait_time=0)` - 导航到 URL
- `close()` - 关闭会话

### ZiniaoConfig

配置类。

#### 类方法

- `from_dict(config_dict)` - 从字典创建
- `from_json_file(file_path)` - 从 JSON 文件加载
- `from_env(prefix="ZINIAO_")` - 从环境变量加载

#### 方法

- `to_dict()` - 转换为字典
- `to_json_file(file_path)` - 保存到 JSON 文件
- `get_user_info()` - 获取用户登录信息

## 🔍 常见问题

### 1. 如何获取店铺 ID？

登录紫鸟客户端 → 账号管理 → 选择店铺 → 点击"查看账号" → 账号名称后面的 ID 即为店铺 ID。

不过推荐直接使用 `open_store_by_name()` 方法，通过店铺名称打开。

### 2. 支持哪些操作系统？

- ✅ Windows
- ✅ macOS (Darwin)
- ✅ Linux

### 3. Python 版本要求？

需要 Python 3.8 或更高版本。

### 4. 如何处理多个重名店铺？

使用精确匹配模式：

```python
session = client.open_store_by_name("店铺名称", exact_match=True)
```

或者先搜索，手动选择：

```python
stores = client.find_stores_by_name("店铺")
# 选择第一个
session = client.open_store(stores[0]['browserOauth'])
```

### 5. 客户端启动失败怎么办？

1. 确认客户端路径正确
2. 确认端口未被占用
3. 手动关闭已运行的紫鸟进程
4. 检查登录信息是否正确

### 6. 如何清理缓存？

```python
from yuehua_ziniao_webdriver import delete_cache, get_cache_size, format_bytes

# 查看缓存大小
size = get_cache_size()
print(f"缓存大小：{format_bytes(size)}")

# 删除缓存（仅 Windows）
if delete_cache():
    print("缓存已清理")
```

## 📝 示例代码

完整的示例代码请查看 [`examples/basic_usage.py`](examples/basic_usage.py)。

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 📄 许可证

本项目采用 [MIT 许可证](LICENSE)。

## 📮 联系方式

- 作者：Yuehua
- 邮箱：shengxi_2000@outlook.com

## 🙏 致谢

- [DrissionPage](https://github.com/g1879/DrissionPage) - 提供浏览器控制功能
- [紫鸟浏览器](https://www.ziniao123.com/) - 提供多账号管理能力

---

**注意**：本 SDK 仅用于学习和个人项目，请遵守紫鸟浏览器的使用条款。
